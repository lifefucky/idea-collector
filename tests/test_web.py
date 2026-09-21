from __future__ import annotations

import asyncio
import csv
import io
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendDocument, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import BufferedInputFile, Chat
from aiogram.types import Message as TelegramMessage
from aiohttp.test_utils import TestClient, TestServer

from idea_collector.bot import bot_reply, create_dispatcher
from idea_collector.capture import capture_text
from idea_collector.db import Idea, IdeaStore, SourceStore
from idea_collector.enrich import Enricher
from idea_collector.shelves import OWN_SHELF
from idea_collector.web import COUNT_PLACEHOLDER, create_web_app
from tests.helpers import BOT_TOKEN, OPERATOR_ID, make_init_data

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "webapp" / "index.html"


class ImmediateLlm:
    async def extract(self, raw_text: str):
        return None


class HangingLlm:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def extract(self, raw_text: str):
        self.started.set()
        await asyncio.sleep(3600)
        return None


def _auth_headers(user_id: int = OPERATOR_ID) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(user_id)}"}


REMOTE_HOST = {"Host": "pocket.test"}


def _counter_in_html(body: str, count: int) -> bool:
    return f'id="ideas-counter">{count}</span>' in body


@pytest.fixture
async def enricher(store: IdeaStore) -> Enricher:
    return Enricher(store, ImmediateLlm())  # type: ignore[arg-type]


@pytest.fixture
async def client(config, store: IdeaStore, enricher: Enricher):
    app = create_web_app(config, store, enricher)
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    yield test_client
    await test_client.close()


@pytest.mark.asyncio
async def test_first_paint_field_and_count_without_js_bundle(
    client, store: IdeaStore
) -> None:
    html = INDEX.read_text(encoding="utf-8")
    assert 'id="capture-field"' in html
    assert 'placeholder="Идея"' in html
    assert 'id="ideas-counter"' in html
    assert COUNT_PLACEHOLDER in html
    assert 'id="idea-list"' in html
    assert "onsubmit=\"return false;\"" in html
    assert 'id="capture-submit"' in html
    assert "Захватить" in html
    assert "clip: rect(0, 0, 0, 0)" not in html
    assert "#f5c400" in html
    assert "#0e0e0e" in html
    assert "white-space: nowrap" in html
    assert "font-variant-numeric: tabular-nums" in html
    assert "disabled" not in html
    response = await client.get("/")
    assert response.status == 200
    body = await response.text()
    assert "Захватить" in body
    assert "clip: rect(0, 0, 0, 0)" not in body
    assert 'id="capture-field"' in body
    assert 'placeholder="Идея"' in body
    assert f'id="ideas-counter">{store.count()}</span>' in body or (
        f">{store.count()}<" in body and "ideas-counter" in body
    )
    assert COUNT_PLACEHOLDER not in body
    list_html = body.split('id="idea-list"', 1)[1]
    assert "ProductHunt" not in list_html
    assert OWN_SHELF not in list_html
    assert 'id="capture-field"' in body.split('id="idea-list"', 1)[0]
    body_html = html.split("<body>", 1)[1].split("<script", 1)[0]
    assert "Tabbar" not in body_html
    assert "Sources" not in body_html
    assert "Лента" not in body_html
    assert "BottomNav" not in body_html


def test_built_telegram_html_has_v2_tokens_and_nav_in_bundle() -> None:
    completed = subprocess.run(
        ["npm", "--prefix", str(ROOT / "webapp"), "run", "build"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    dist_index = ROOT / "webapp" / "dist" / "index.html"
    html = dist_index.read_text(encoding="utf-8")
    body_html = html.split("<body>", 1)[1].split("<script", 1)[0]
    assert "#f5c400" in html
    assert "#0e0e0e" in html
    assert "Захватить" in html
    assert "Лента" not in body_html
    assert "BottomNav" not in body_html
    assert "Tabbar" not in body_html
    js = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "webapp" / "dist" / "assets").glob("*.js")
    )
    assert "Лента" in js
    assert "bottom-nav" in js


def test_empty_pocket_is_field_and_zero() -> None:
    html = INDEX.read_text(encoding="utf-8")
    assert f">{COUNT_PLACEHOLDER}<" in html or f">{COUNT_PLACEHOLDER}</span>" in html
    injected = html.replace(COUNT_PLACEHOLDER, "0")
    assert ">0</span>" in injected
    list_html = html.split('id="idea-list"', 1)[1]
    assert "Accordion" not in list_html
    assert "list-skeleton" in list_html


@pytest.mark.asyncio
async def test_bot_dump_operator_ack_queue_and_non_operator(
    store: IdeaStore, enricher: Enricher
) -> None:
    ignored = capture_text(
        store,
        enricher,
        user_id=999,
        operator_id=OPERATOR_ID,
        text="secret",
    )
    assert ignored.ignored
    assert bot_reply(ignored) is None
    assert store.count() == 0

    result = capture_text(
        store,
        enricher,
        user_id=OPERATOR_ID,
        operator_id=OPERATOR_ID,
        text="from chat",
        owner=f"tg:{OPERATOR_ID}",
    )
    assert result.idea is not None
    assert result.count == 1
    assert bot_reply(result) == "1"
    assert enricher.queued == 1
    presented_pending = store.list_all()[0]
    assert presented_pending.raw_text == "from chat"

    again = capture_text(
        store,
        enricher,
        user_id=OPERATOR_ID,
        operator_id=OPERATOR_ID,
        text="from chat",
        owner=f"tg:{OPERATOR_ID}",
    )
    assert again.count == 2
    assert bot_reply(again) == "2"


@pytest.mark.asyncio
async def test_bot_persist_fail_not_stored_short_error(enricher: Enricher) -> None:
    class BoomStore(IdeaStore):
        def insert(self, raw_text: str, owner: str = "global") -> Idea:  # type: ignore[override]
            raise sqlite3.OperationalError("disk")

    boom = BoomStore(":memory:")
    result = capture_text(
        boom,
        enricher,
        user_id=OPERATOR_ID,
        operator_id=OPERATOR_ID,
        text="lost",
    )
    assert result.error == "Не удалось сохранить"
    assert bot_reply(result) == "Не удалось сохранить"
    assert boom.count() == 0
    boom.close()


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.replies: list[str] = []
        self.documents: list[tuple[str, bytes]] = []
        self.fail = False

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        if isinstance(method, SendDocument) and isinstance(
            method.document, BufferedInputFile
        ):
            self.documents.append(
                (method.document.filename or "", method.document.data)
            )
        text = getattr(method, "text", None)
        if isinstance(text, str):
            self.replies.append(text)
        if self.fail:
            raise TelegramAPIError(method=method, message="fail")
        return TelegramMessage(  # type: ignore[return-value]
            message_id=1,
            date=datetime.now(UTC),
            chat=Chat(id=OPERATOR_ID, type="private"),
            text=text or "",
        )

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ):
        if False:
            yield b""


@pytest.mark.asyncio
async def test_bot_on_text_stores_ack_and_skips_slash(
    config, store: IdeaStore, enricher: Enricher
) -> None:
    session = RecordingSession()
    bot = Bot(token=BOT_TOKEN, session=session)
    dispatcher = create_dispatcher(config, store, enricher)
    now = int(time.time())

    async def feed(text: str, update_id: int, user_id: int = OPERATOR_ID) -> None:
        await dispatcher.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "message": {
                    "message_id": update_id,
                    "date": now,
                    "chat": {"id": user_id, "type": "private"},
                    "from": {
                        "id": user_id,
                        "is_bot": False,
                        "first_name": "Op",
                    },
                    "text": text,
                },
            },
        )

    try:
        await feed("/start", 1)
        session.replies.clear()
        session.documents.clear()
        await feed("/csv", 2)
        assert store.count() == 0
        assert session.replies == ["В кармане нет идей"]
        assert session.documents == []

        await feed("/foo", 3)
        assert store.count() == 0
        assert session.replies == ["В кармане нет идей"]
        assert session.documents == []

        await feed("/csv", 4, user_id=999)
        assert store.count() == 0
        assert session.replies == ["В кармане нет идей"]
        assert session.documents == []

        await feed("from chat", 5)
        assert store.count() == 1
        assert store.list_all()[0].raw_text == "from chat"
        assert "1" in session.replies

        quoted, _ = store.insert("quoted raw")
        store.update_enrichment(
            quoted.id,
            source="ProductHunt",
            short_name="Заголовок, с запятой",
            description='Строка1\nСтрока2, и "кавычки"',
        )
        count_before = store.count()
        replies_before = list(session.replies)
        documents_before = list(session.documents)
        await feed("/csv", 6, user_id=999)
        assert store.count() == count_before
        assert session.replies == replies_before
        assert session.documents == documents_before

        session.replies.clear()
        session.documents.clear()
        expected_name = f"ideas-{datetime.now(UTC).date().isoformat()}.csv"
        await feed("/csv", 7)
        assert store.count() == count_before
        assert session.replies == []
        assert len(session.documents) == 1
        filename, payload = session.documents[0]
        assert filename == expected_name
        assert not payload.startswith(b"\xef\xbb\xbf")
        rows = list(csv.reader(io.StringIO(payload.decode("utf-8"))))
        assert rows[0] == ["title", "description"]
        assert rows[1] == ["from chat", "from chat"]
        assert rows[2] == ["Заголовок, с запятой", 'Строка1\nСтрока2, и "кавычки"']
        assert all(len(row) == 2 for row in rows)

        session.fail = True
        session.replies.clear()
        session.documents.clear()
        await feed("/csv", 8)
        assert store.count() == count_before
        assert session.replies == []

        for idea in store.list_all():
            store.delete(idea.id)
        session.replies.clear()
        session.documents.clear()
        await feed("/csv", 9)
        assert store.count() == 0
        assert session.documents == []
    finally:
        await enricher.drain()
        await bot.session.close()


@pytest.mark.asyncio
async def test_webapp_dump_returns_before_llm_and_increments(
    config, store: IdeaStore
) -> None:
    hanging = HangingLlm()
    tasks: list[asyncio.Task[None]] = []

    def schedule(coro):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    enricher = Enricher(store, hanging, schedule=schedule)  # type: ignore[arg-type]
    app = create_web_app(config, store, enricher)
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    try:
        started = time.monotonic()
        response = await test_client.post(
            "/api/ideas",
            json={"text": "web idea"},
            headers=_auth_headers(),
        )
        elapsed = time.monotonic() - started
        assert elapsed < 1
        assert response.status == 200
        body = await response.json()
        assert body["count"] == 1
        assert body["label"] == "web idea"
        assert body["copy"] == "web idea"
        assert body["shelf"] == OWN_SHELF
        assert store.count() == 1
        assert enricher.queued == 1
        await hanging.started.wait()
        second = await test_client.post(
            "/api/ideas",
            json={"text": "web idea"},
            headers=_auth_headers(),
        )
        assert second.status == 200
        assert (await second.json())["count"] == 2
    finally:
        for task in tasks:
            task.cancel()
        await test_client.close()


@pytest.mark.asyncio
async def test_webapp_persist_fail_keeps_count(config, enricher: Enricher) -> None:
    class BoomStore(IdeaStore):
        def insert(self, raw_text: str, owner: str = "global") -> Idea:  # type: ignore[override]
            raise sqlite3.OperationalError("disk")

    boom = BoomStore(":memory:")
    app = create_web_app(config, boom, enricher)
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    try:
        response = await test_client.post(
            "/api/ideas",
            json={"text": "keep in field"},
            headers=_auth_headers(),
        )
        assert response.status == 500
        payload = await response.json()
        assert payload["error"] == "Не удалось сохранить"
        assert boom.count() == 0
        count_resp = await test_client.get("/api/count", headers=_auth_headers())
        assert (await count_resp.json())["count"] == 0
    finally:
        await test_client.close()
        boom.close()


@pytest.mark.asyncio
async def test_api_count_matches_index_owner_and_fallback(
    client, store: IdeaStore
) -> None:
    local_headers = {"Authorization": "tma dev"}
    await client.post(
        "/api/ideas",
        json={"text": "local idea"},
        headers=local_headers,
    )
    await client.post(
        "/api/ideas",
        json={"text": "tg idea"},
        headers=_auth_headers(),
    )
    assert store.count() == 2

    local_html = await client.get("/")
    local_count = await client.get("/api/count")
    assert local_html.status == 200
    assert local_count.status == 200
    assert _counter_in_html(await local_html.text(), 1)
    assert (await local_count.json()) == {"count": 1}

    hmac_on_localhost = await client.get("/api/count", headers=_auth_headers())
    assert hmac_on_localhost.status == 200
    assert (await hmac_on_localhost.json()) == {"count": 1}

    remote_html = await client.get("/", headers=REMOTE_HOST)
    remote_count = await client.get("/api/count", headers=REMOTE_HOST)
    assert remote_html.status == 200
    assert remote_count.status == 200
    assert _counter_in_html(await remote_html.text(), 2)
    assert (await remote_count.json()) == {"count": 2}

    tg_count = await client.get(
        "/api/count",
        headers={**REMOTE_HOST, **_auth_headers()},
    )
    assert tg_count.status == 200
    assert (await tg_count.json()) == {"count": 1}

    ideas_still_auth = await client.get("/api/ideas")
    assert ideas_still_auth.status == 401


@pytest.mark.asyncio
async def test_api_ideas_groups_and_copy_payload(client, store: IdeaStore) -> None:
    store.insert("pending raw")
    second, _ = store.insert("ph raw")
    store.update_enrichment(
        second.id,
        source="ProductHunt",
        short_name="Short PH",
        description="copy this",
    )
    failed, _ = store.insert("fail raw")
    store.update_enrichment(
        failed.id,
        source=OWN_SHELF,
        short_name="fail raw",
        description="fail raw",
    )
    response = await client.get("/api/ideas", headers=_auth_headers())
    assert response.status == 200
    body = await response.json()
    names = [shelf["name"] for shelf in body["shelves"]]
    assert names == [OWN_SHELF, "ProductHunt"]
    own = body["shelves"][0]["ideas"]
    assert own[0]["label"] == "pending raw"
    assert own[0]["copy"] == "pending raw"
    ph = body["shelves"][1]["ideas"][0]
    assert ph["label"] == "Short PH"
    assert ph["copy"] == "copy this"


@pytest.mark.asyncio
async def test_local_and_telegram_ideas_are_separate(client, store: IdeaStore) -> None:
    # Local preview uses dev initData and localhost host.
    local_headers = {"Authorization": "tma dev"}

    local_resp = await client.post(
        "/api/ideas",
        json={"text": "local idea"},
        headers=local_headers,
    )
    assert local_resp.status == 200
    assert (await local_resp.json())["count"] == 1

    tg_resp = await client.post(
        "/api/ideas",
        json={"text": "tg idea"},
        headers=_auth_headers(),
    )
    assert tg_resp.status == 200
    assert (await tg_resp.json())["count"] == 1

    local_list = await client.get("/api/ideas", headers=local_headers)
    tg_list = await client.get("/api/ideas", headers=_auth_headers())
    assert local_list.status == 200
    assert tg_list.status == 200
    local_body = await local_list.json()
    tg_body = await tg_list.json()
    assert local_body["count"] == 1
    assert tg_body["count"] == 1
    assert any(idea["label"] == "local idea" for shelf in local_body["shelves"] for idea in shelf["ideas"])
    assert all(idea["label"] != "tg idea" for shelf in local_body["shelves"] for idea in shelf["ideas"])
    assert any(idea["label"] == "tg idea" for shelf in tg_body["shelves"] for idea in shelf["ideas"])
    assert all(idea["label"] != "local idea" for shelf in tg_body["shelves"] for idea in shelf["ideas"])


@pytest.mark.asyncio
async def test_local_and_telegram_sources_are_separate(client, store: IdeaStore) -> None:
    local_headers = {"Authorization": "tma dev"}

    # Ensure operator pocket exists for both owners.
    await client.post(
        "/api/ideas",
        json={"text": "seed local"},
        headers=local_headers,
    )
    await client.post(
        "/api/ideas",
        json={"text": "seed tg"},
        headers=_auth_headers(),
    )

    local_created = await client.post(
        "/api/sources",
        json={"title": "LocalDoc", "url": "https://local.example"},
        headers=local_headers,
    )
    assert local_created.status == 200

    tg_created = await client.post(
        "/api/sources",
        json={"title": "TgDoc", "url": "https://tg.example"},
        headers=_auth_headers(),
    )
    assert tg_created.status == 200

    local_sources = await client.get("/api/sources", headers=local_headers)
    tg_sources = await client.get("/api/sources", headers=_auth_headers())
    assert local_sources.status == 200
    assert tg_sources.status == 200
    local_body = await local_sources.json()
    tg_body = await tg_sources.json()
    assert [s["title"] for s in local_body["sources"]] == ["LocalDoc"]
    assert [s["title"] for s in tg_body["sources"]] == ["TgDoc"]


@pytest.mark.asyncio
async def test_hmac_rejects_non_operator_and_bad_hash(client) -> None:
    bad = await client.get("/api/ideas")
    assert bad.status == 401
    other = await client.post(
        "/api/ideas",
        json={"text": "nope"},
        headers=_auth_headers(user_id=7),
    )
    assert other.status == 403
    forged = await client.post(
        "/api/ideas",
        json={"text": "nope"},
        headers={"Authorization": "tma user=%7B%22id%22%3A42%7D&hash=dead"},
    )
    assert forged.status == 401


def test_copy_repeat_offline_client_contract() -> None:
    probe = ROOT / "tests" / "capture_probe.mjs"
    completed = subprocess.run(
        ["node", str(probe)],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert completed.returncode == 0, completed.stderr
    index = INDEX.read_text(encoding="utf-8")
    capture = (ROOT / "webapp" / "src" / "capture.js").read_text(encoding="utf-8")
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    assert "onContextMenu={() => undefined}" in list_app
    assert "preventDefault" not in list_app
    assert "onCopy(idea.copy)" not in list_app
    assert "Скопировано" in capture
    assert "disabled" not in index.split("capture-field")[1].split("textarea")[0]


def test_idea_list_click_runner() -> None:
    completed = subprocess.run(
        ["npm", "--prefix", str(ROOT / "webapp"), "test"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout


def test_idea_card_open_does_not_copy() -> None:
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    main = (ROOT / "webapp" / "src" / "main.tsx").read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    body_html = index.split("<body>", 1)[1].split("<script", 1)[0]
    row = list_app.split('className="idea-row"', 1)[1].split("</button>", 1)[0]
    assert "selectedIdea" in list_app
    assert "onClick={() => onOpen(idea)}" in row
    assert "onOpen={openCard}" in list_app
    assert "onCopy" not in row
    assert "idea-card-header" in list_app
    assert "selectedIdea.label" in list_app
    assert "selectedIdea.copy" in list_app
    assert "capture-strip" in main
    assert "setCaptureStripHidden" in main
    chrome = (ROOT / "webapp" / "src" / "cardChrome.js").read_text(encoding="utf-8")
    assert "strip.hidden = open" in chrome
    assert "#capture-strip[hidden]" in index
    assert 'id="capture-field"' in body_html
    assert "idea-card-header" not in body_html
    assert "44pt" in index
    assert "text-overflow: ellipsis" in index
    assert "white-space: pre-wrap" in index


def test_idea_card_body_copy_contract() -> None:
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    main = (ROOT / "webapp" / "src" / "main.tsx").read_text(encoding="utf-8")
    capture = (ROOT / "webapp" / "src" / "capture.js").read_text(encoding="utf-8")
    body = list_app.split('className="idea-card-body"', 1)[1].split("</button>", 1)[0]
    assert "onCopy(selectedIdea.copy)" in body
    assert "ignoreBodyCopy" in body
    assert "bindCopy" in main
    assert "navigator.clipboard" in capture
    assert "Скопировано" in capture
    assert "Не удалось скопировать" in capture
    assert "Удалить" not in capture
    assert "Удалить" not in body
    assert "Удалить" in list_app
    assert "copy button" not in list_app.lower()


@pytest.mark.asyncio
async def test_delete_idea_operator_count_and_errors(client, store: IdeaStore) -> None:
    first, _ = store.insert("keep")
    gone, _ = store.insert("gone")
    store.update_enrichment(
        gone.id,
        source="ProductHunt",
        short_name="Gone",
        description="copy",
    )
    unauth = await client.delete(f"/api/ideas/{gone.id}")
    assert unauth.status == 401
    assert store.get(gone.id) is not None
    forbidden = await client.delete(
        f"/api/ideas/{gone.id}",
        headers=_auth_headers(user_id=7),
    )
    assert forbidden.status == 403
    assert store.get(gone.id) is not None
    forged = await client.delete(
        f"/api/ideas/{gone.id}",
        headers={"Authorization": "tma user=%7B%22id%22%3A42%7D&hash=dead"},
    )
    assert forged.status == 401
    missing = await client.delete("/api/ideas/999999", headers=_auth_headers())
    assert missing.status == 404
    assert "error" in await missing.json()
    assert store.count() == 2
    bad_id = await client.delete("/api/ideas/not-an-id", headers=_auth_headers())
    assert bad_id.status == 400
    ok = await client.delete(f"/api/ideas/{gone.id}", headers=_auth_headers())
    assert ok.status == 200
    assert await ok.json() == {"count": 1}
    listed = await client.get("/api/ideas", headers=_auth_headers())
    body = await listed.json()
    assert body["count"] == 1
    assert [shelf["name"] for shelf in body["shelves"]] == [OWN_SHELF]
    last = await client.delete(f"/api/ideas/{first.id}", headers=_auth_headers())
    assert last.status == 200
    assert await last.json() == {"count": 0}
    empty = await client.get("/api/ideas", headers=_auth_headers())
    empty_body = await empty.json()
    assert empty_body["count"] == 0
    assert empty_body["shelves"] == []


@pytest.mark.asyncio
async def test_delete_returns_404_when_remove_fails(config, enricher: Enricher) -> None:
    class MissStore(IdeaStore):
        def delete_for_owner(self, idea_id: int, owner: str) -> tuple[bool, int]:
            # Simulate a low-level delete failure even when the idea exists.
            return False, super().count_for_owner(owner)

    store = MissStore(":memory:")
    idea, _ = store.insert("still there")
    app = create_web_app(config, store, enricher)
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    try:
        response = await test_client.delete(
            f"/api/ideas/{idea.id}",
            headers=_auth_headers(),
        )
        assert response.status == 404
        assert "error" in await response.json()
        assert store.get(idea.id) is not None
    finally:
        await test_client.close()
        store.close()


def test_idea_card_delete_contract() -> None:
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    main = (ROOT / "webapp" / "src" / "main.tsx").read_text(encoding="utf-8")
    capture = (ROOT / "webapp" / "src" / "capture.js").read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    body_html = index.split("<body>", 1)[1].split("<script", 1)[0]
    body = list_app.split('className="idea-card-body"', 1)[1].split("</button>", 1)[0]
    after_body = list_app.split('className="idea-card-body"', 1)[1].split("</button>", 1)[1].split(") : (", 1)[0]
    row = list_app.split('className="idea-row"', 1)[1].split("</button>", 1)[0]
    delete_css = index.split("button.idea-card-delete", 1)[1].split("}", 1)[0]
    handler = list_app.split("const deleteSelected = useCallback", 1)[1].split(
        "}, [getInitData, load, onCount, onDeleteClear,"
        " onDeleteError, selectedIdea]);",
        1,
    )[0]
    assert "Удалить" not in body
    assert "Удалить" not in capture
    assert "Удалить" not in row
    assert "Удалить" not in body_html
    assert "Удалить" in after_body
    assert 'className="idea-card-delete"' in after_body
    assert "<button" in after_body
    assert "idea-related" in list_app
    assert "44pt" in delete_css
    assert "button.idea-card-delete" in index
    assert 'method: "DELETE"' in handler
    assert "deleteFetchOutcome(response)" in handler
    assert "deleteFetchOutcome(null)" in handler
    assert "onCount(body.count)" in handler
    assert "onDeleteClear()" in handler
    assert "setSelectedIdea((current) => (current?.id === deletedId ? null : current))" in handler
    assert "closeCard()" not in handler
    assert "await load()" in handler
    assert "onDeleteError()" in handler
    assert "if (deleteInFlight.current || selectedIdea === null)" in handler
    assert "deleteInFlight.current = true" in handler
    assert "onCount" in main
    assert "onDeleteClear" in main
    assert "onDeleteError" in main
    assert "deleteStatus(true)" in main
    assert "deleteStatus(false)" in main
    assert "setIdeasCounter" in main
    assert "replaceCountPlaceholder" in main
    assert "replaceCountPlaceholder(counter)" in main
    assert "DELETE_ERROR" in capture
    assert "setIdeasCounter" in capture
    assert "export function replaceCountPlaceholder" in capture
    assert "export function deleteFetchOutcome" in capture
    assert "history.back" not in handler
    assert "confirm" not in handler.lower()
    assert "undo" not in handler.lower()


def test_idea_card_back_contract() -> None:
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    main = (ROOT / "webapp" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "closeCard" in list_app
    assert "onClick={closeCard}" in list_app
    assert "backButton.mount" in main
    assert "backButton.mount.isAvailable()" in main
    chrome = (ROOT / "webapp" / "src" / "cardChrome.js").read_text(encoding="utf-8")
    assert "api.show.isAvailable()" in chrome
    assert "api.hide.isAvailable()" in chrome
    assert "api.onClick.isAvailable()" in chrome
    assert "getClose()()" in chrome
    assert "closeIdeaCard" in main
    assert "history.back" not in list_app
    assert "history.back" not in main
    assert "pushState" not in list_app
    assert "pushState" not in main


def test_idea_card_enrich_while_open_contract() -> None:
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    after_load = list_app.split("const load = useCallback", 1)[1]
    load = after_load.split("}, [getInitData]);", 1)[0]
    assert '"ideas:changed"' in list_app
    assert "if (!response.ok)" in load
    assert "return;" in load.split("if (!response.ok)", 1)[1].split("}", 1)[0]
    assert "selectedAfterLoad" in load
    assert "keep current shelves (null = skeleton) and the open card" in load
    idea_card = (ROOT / "webapp" / "src" / "ideaCard.js").read_text(encoding="utf-8")
    assert "export function selectedAfterFetch" in idea_card
    assert "return ideaById(shelves, selected.id) ?? null" in idea_card


@pytest.mark.asyncio
async def test_api_sources_operator_crud_and_errors(client, store: IdeaStore) -> None:
    sources = SourceStore(store)
    store.insert("an idea")
    unauth = await client.get("/api/sources")
    assert unauth.status == 401
    assert sources.list_all() == []
    empty = await client.get("/api/sources", headers=_auth_headers())
    assert empty.status == 200
    assert await empty.json() == {"sources": []}
    stranger_get = await client.get("/api/sources", headers=_auth_headers(user_id=7))
    assert stranger_get.status == 403
    forbidden = await client.post(
        "/api/sources",
        json={"title": "Nope", "url": "https://nope.example"},
        headers=_auth_headers(user_id=7),
    )
    assert forbidden.status == 403
    assert sources.list_all() == []
    forged = await client.post(
        "/api/sources",
        json={"title": "Nope", "url": "https://nope.example"},
        headers={"Authorization": "tma user=%7B%22id%22%3A42%7D&hash=dead"},
    )
    assert forged.status == 401
    assert sources.list_all() == []
    not_json = await client.post(
        "/api/sources",
        data="not-json",
        headers={**_auth_headers(), "Content-Type": "text/plain"},
    )
    assert not_json.status == 400
    assert (await not_json.json())["error"] == "Не удалось сохранить"
    assert sources.list_all() == []
    blank = await client.post(
        "/api/sources",
        json={"title": "  ", "url": "https://ok.example"},
        headers=_auth_headers(),
    )
    assert blank.status == 400
    assert (await blank.json())["error"] == "Не удалось сохранить"
    missing_url = await client.post(
        "/api/sources",
        json={"title": "Doc", "url": ""},
        headers=_auth_headers(),
    )
    assert missing_url.status == 400
    assert sources.list_all() == []
    created = await client.post(
        "/api/sources",
        json={"title": "  Doc  ", "url": "  https://doc.example  "},
        headers=_auth_headers(),
    )
    assert created.status == 200
    first = await created.json()
    assert first == {"id": first["id"], "title": "Doc", "url": "https://doc.example"}
    second = await client.post(
        "/api/sources",
        json={"title": "Repo", "url": "https://repo.example"},
        headers=_auth_headers(),
    )
    assert second.status == 200
    listed = await client.get("/api/sources", headers=_auth_headers())
    assert listed.status == 200
    body = await listed.json()
    assert list(body.keys()) == ["sources"]
    assert [item["title"] for item in body["sources"]] == ["Doc", "Repo"]
    assert all(set(item.keys()) == {"id", "title", "url"} for item in body["sources"])
    assert store.count() == 1
    bad_id = await client.delete("/api/sources/not-an-id", headers=_auth_headers())
    assert bad_id.status == 400
    assert (await bad_id.json())["error"] == "invalid id"
    missing = await client.delete("/api/sources/999999", headers=_auth_headers())
    assert missing.status == 404
    assert (await missing.json())["error"] == "not found"
    forbidden_del = await client.delete(
        f"/api/sources/{first['id']}",
        headers=_auth_headers(user_id=7),
    )
    assert forbidden_del.status == 403
    assert sources.get(first["id"]) is not None
    gone = await client.delete(
        f"/api/sources/{first['id']}",
        headers=_auth_headers(),
    )
    assert gone.status == 200
    assert await gone.json() == {"ok": True}
    after = await client.get("/api/sources", headers=_auth_headers())
    assert [item["title"] for item in (await after.json())["sources"]] == ["Repo"]
    ideas = await client.get("/api/ideas", headers=_auth_headers())
    assert ideas.status == 200
    assert (await ideas.json())["count"] == 1


def test_sources_tabbar_overlay_open_delete_contracts() -> None:
    pocket = (ROOT / "webapp" / "src" / "pocketApp.tsx").read_text(encoding="utf-8")
    sources = (ROOT / "webapp" / "src" / "sourcesPane.tsx").read_text(encoding="utf-8")
    main = (ROOT / "webapp" / "src" / "main.tsx").read_text(encoding="utf-8")
    list_app = (ROOT / "webapp" / "src" / "listApp.tsx").read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    body_html = index.split("<body>", 1)[1].split("<script", 1)[0]
    ideas_pane = pocket.split('className="pocket-ideas"', 1)[1].split(
        'className="pocket-sources"',
        1,
    )[0]
    delete_btn = sources.split('className="source-row-delete"', 1)[1].split(
        "</button>",
        1,
    )[0]
    cancel_btn = sources.split('className="sources-overlay-cancel"', 1)[1].split(
        "</button>",
        1,
    )[0]
    save_btn = sources.split('className="sources-overlay-save"', 1)[1].split(
        "</button>",
        1,
    )[0]
    save_fn = sources.split("const saveSource = useCallback", 1)[1].split(
        "}, [getInitData, load, onOverlayOpenChange, onSaveError, title, url]);",
        1,
    )[0]
    load_fn = sources.split("const load = useCallback", 1)[1].split(
        "}, [getInitData]);",
        1,
    )[0]
    source_link = (ROOT / "webapp" / "src" / "sourceLink.js").read_text(
        encoding="utf-8",
    )
    delete_css = index.split("button.source-row-delete", 1)[1].split("}", 1)[0]
    assert "Tabbar" not in body_html
    assert "Sources" not in body_html
    assert "Идеи" in pocket
    assert "Sources" in pocket
    assert "BottomNav" in pocket
    assert "Лента" in pocket
    assert 'data-stub="no-backend"' in pocket
    assert "Tabbar" not in pocket
    assert "Tabbar.Item" not in pocket
    assert "<IdeaList" in ideas_pane
    assert 'hidden={tab !== "ideas"}' in pocket
    assert "&& <IdeaList" not in pocket
    assert 'tab === "ideas" ?' not in pocket
    assert "?" not in ideas_pane.split("<IdeaList", 1)[0]
    assert "&&" not in ideas_pane.split("<IdeaList", 1)[0]
    assert "selectedIdea" in list_app
    assert "<PocketApp" in main
    assert "<IdeaList" not in main
    assert "onSaveError" in main
    assert "saveStatus(false)" in main
    assert "onOpenError" in main
    assert "OPEN_ERROR" in main
    assert "cancelOverlay" in pocket
    assert "onCardOpenChange(true, cancelOverlay)" in pocket
    assert (
        'setCaptureStripHidden(document.getElementById("capture-strip"), true)'
        in pocket
    )
    assert 'placeholder="Название"' in sources
    assert 'placeholder="Ссылка"' in sources
    assert "Сохранить" in save_btn
    assert "Отмена" in cancel_btn
    assert "fetch" not in cancel_btn
    assert 'onClick={() => onOverlayOpenChange(false)}' in cancel_btn
    assert "if (saveInFlight.current)" in save_fn
    assert "if (!nextTitle || !nextUrl)" in save_fn
    assert "return;" in save_fn.split("if (!nextTitle || !nextUrl)", 1)[1].split(
        "}",
        1,
    )[0]
    assert 'method: "POST"' in save_fn
    assert "setSources((current) => [...current, created])" in save_fn
    assert "onOverlayOpenChange(false)" in save_fn
    assert "await load()" in save_fn
    assert "onSaveError()" in save_fn
    assert '"/api/sources"' in load_fn
    assert "setSources(body.sources ?? [])" in load_fn
    assert 'className="sources-add"' in sources
    assert "+" in sources.split('className="sources-add"', 1)[1].split(
        "</button>",
        1,
    )[0]
    assert 'data-stub="no-backend"' in sources
    assert "source-suggest-chip" in sources
    assert "{source.title}" in sources
    assert "subtitle=" not in sources
    assert "description=" not in sources
    assert "openLink.isAvailable()" in source_link
    assert 'window.open(url, "_blank", "noopener")' in source_link
    assert "openSourceUrl" in sources
    assert "stopPropagation" in delete_btn
    assert "Удалить" in delete_btn
    assert "openLink" not in delete_btn
    assert "openSourceUrl" not in delete_btn
    assert "confirm" not in sources.lower()
    assert "undo" not in sources.lower()
    assert "44pt" in delete_css
    assert "OPEN_ERROR" in sources
    assert "Не удалось открыть" in sources
    assert "onOpenError()" in sources
    assert "if (deleteInFlight.current)" in sources
    assert 'method: "DELETE"' in sources
    assert "sourceDeleteOutcome(response)" in sources
    assert "sourceDeleteOutcome(null)" in sources
    assert "blur" not in save_fn.lower()

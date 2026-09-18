from __future__ import annotations

import asyncio
import sqlite3
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat
from aiogram.types import Message as TelegramMessage
from aiohttp.test_utils import TestClient, TestServer

from idea_collector.bot import bot_reply, create_dispatcher
from idea_collector.capture import capture_text
from idea_collector.db import Idea, IdeaStore
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
    assert "clip: rect(0, 0, 0, 0)" in html
    assert "disabled" not in html
    response = await client.get("/")
    assert response.status == 200
    body = await response.text()
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
    )
    assert again.count == 2
    assert bot_reply(again) == "2"


@pytest.mark.asyncio
async def test_bot_persist_fail_not_stored_short_error(enricher: Enricher) -> None:
    class BoomStore(IdeaStore):
        def insert(self, raw_text: str) -> Idea:
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

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        text = getattr(method, "text", None)
        if isinstance(text, str):
            self.replies.append(text)
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

    async def feed(text: str, update_id: int) -> None:
        await dispatcher.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "message": {
                    "message_id": update_id,
                    "date": now,
                    "chat": {"id": OPERATOR_ID, "type": "private"},
                    "from": {
                        "id": OPERATOR_ID,
                        "is_bot": False,
                        "first_name": "Op",
                    },
                    "text": text,
                },
            },
        )

    try:
        await feed("/start", 1)
        await feed("/csv", 2)
        assert store.count() == 0
        await feed("from chat", 3)
        assert store.count() == 1
        assert store.list_all()[0].raw_text == "from chat"
        assert "1" in session.replies
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
        def insert(self, raw_text: str) -> Idea:
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
    assert "Скопировано" in capture
    assert "disabled" not in index.split("capture-field")[1].split("textarea")[0]

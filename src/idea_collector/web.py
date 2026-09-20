from __future__ import annotations

import json
from pathlib import Path

from aiohttp import ContentTypeError, web

from idea_collector.auth import AuthError, init_data_from_headers, require_operator
from idea_collector.capture import capture_payload, capture_text
from idea_collector.config import Config
from idea_collector.db import IdeaStore, Source, SourceStore
from idea_collector.enrich import Enricher
from idea_collector.shelves import group_by_shelf

COUNT_PLACEHOLDER = "__IDEAS_COUNT__"
ROOT = Path(__file__).resolve().parents[2]
CONFIG_KEY = web.AppKey("config", Config)
STORE_KEY = web.AppKey("store", IdeaStore)
ENRICHER_KEY = web.AppKey("enricher", Enricher)


def _webapp_dir() -> Path:
    for candidate in (Path.cwd() / "webapp", ROOT / "webapp"):
        if (candidate / "dist" / "index.html").is_file() or (
            candidate / "index.html"
        ).is_file():
            return candidate
    return ROOT / "webapp"


def webapp_index_path() -> Path:
    webapp_dir = _webapp_dir()
    dist = webapp_dir / "dist" / "index.html"
    if dist.is_file():
        return dist
    return webapp_dir / "index.html"


def webapp_assets_dir() -> Path | None:
    assets = _webapp_dir() / "dist" / "assets"
    if assets.is_dir():
        return assets
    return None


def inject_count(html: str, count: int) -> str:
    return html.replace(COUNT_PLACEHOLDER, str(count))


def create_web_app(
    config: Config,
    store: IdeaStore,
    enricher: Enricher,
) -> web.Application:
    app = web.Application()
    app[CONFIG_KEY] = config
    app[STORE_KEY] = store
    app[ENRICHER_KEY] = enricher
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/count", handle_count)
    app.router.add_get("/api/ideas", handle_list_ideas)
    app.router.add_post("/api/ideas", handle_create_idea)
    app.router.add_delete("/api/ideas/{id}", handle_delete_idea)
    app.router.add_get("/api/sources", handle_list_sources)
    app.router.add_post("/api/sources", handle_create_source)
    app.router.add_delete("/api/sources/{id}", handle_delete_source)
    assets = webapp_assets_dir()
    if assets is not None:
        app.router.add_static("/assets", assets)
    return app


def _is_local_request(request: web.Request) -> bool:
    host = request.host.split(":", 1)[0]
    return host in {"127.0.0.1", "localhost"}


def _operator_from_request(request: web.Request) -> None:
    # Backwards-compatible shim: keep behavior for call sites that only
    # need to enforce operator auth without caring about the owner key.
    _owner_from_request(request)


def _owner_from_request(request: web.Request) -> str:
    """Return the owner key for this request, enforcing operator auth."""

    config = request.app[CONFIG_KEY]
    init_data = init_data_from_headers(dict(request.headers))
    if init_data == "dev" and _is_local_request(request):
        # Local preview: treat as a separate local owner pocket.
        return f"local:{config.operator_telegram_id}"
    user = require_operator(init_data, config)
    return f"tg:{user.id}"


def _json_error(status: int, message: str) -> web.Response:
    return web.json_response({"error": message}, status=status)


async def handle_index(request: web.Request) -> web.StreamResponse:
    store = request.app[STORE_KEY]
    config = request.app[CONFIG_KEY]
    path = webapp_index_path()
    if not path.is_file():
        raise web.HTTPNotFound(text="webapp index is missing; build webapp/dist")
    html = path.read_text(encoding="utf-8")
    # For local preview, show the count for the local owner pocket so the
    # counter matches what the operator sees in the app. For Telegram and
    # other environments, try to scope by owner when auth is available, but
    # fall back to the global count so the Mini App still renders even when
    # initData is missing or invalid.
    if _is_local_request(request):
        owner = f"local:{config.operator_telegram_id}"
        count = store.count_for_owner(owner)
    else:
        try:
            owner = _owner_from_request(request)
        except AuthError:
            count = store.count()
        else:
            count = store.count_for_owner(owner)
    body = inject_count(html, count)
    return web.Response(text=body, content_type="text/html")


async def handle_count(request: web.Request) -> web.StreamResponse:
    try:
        owner = _owner_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    store = request.app[STORE_KEY]
    return web.json_response({"count": store.count_for_owner(owner)})


async def handle_list_ideas(request: web.Request) -> web.StreamResponse:
    try:
        owner = _owner_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    store = request.app[STORE_KEY]
    ideas = store.list_for_owner(owner)
    return web.json_response(
        {
            "count": len(ideas),
            "shelves": group_by_shelf(ideas),
        }
    )


async def _read_idea_text(request: web.Request) -> str:
    content_type = request.content_type
    if content_type.startswith("application/json"):
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise web.HTTPBadRequest(text="invalid json") from exc
        if isinstance(payload, dict):
            value = payload.get("text", "")
            return value if isinstance(value, str) else ""
        return ""
    post = await request.post()
    return str(post.get("text", ""))


async def handle_create_idea(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG_KEY]
    store = request.app[STORE_KEY]
    enricher = request.app[ENRICHER_KEY]
    try:
        owner = _owner_from_request(request)
        text = await _read_idea_text(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    if not text.strip():
        return _json_error(400, "Не удалось сохранить")
    result = capture_text(
        store,
        enricher,
        user_id=config.operator_telegram_id,
        operator_id=config.operator_telegram_id,
        text=text,
        owner=owner,
    )
    if result.error or result.idea is None:
        return _json_error(500, result.error or "Не удалось сохранить")
    return web.json_response(capture_payload(result))


async def handle_delete_idea(request: web.Request) -> web.StreamResponse:
    try:
        owner = _owner_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    try:
        idea_id = int(request.match_info["id"])
    except (TypeError, ValueError):
        return _json_error(400, "invalid id")
    store = request.app[STORE_KEY]
    removed, count = store.delete_for_owner(idea_id, owner)
    if not removed:
        return _json_error(404, "not found")
    return web.json_response({"count": count})


def _source_payload(source: Source) -> dict[str, int | str]:
    return {"id": source.id, "title": source.title, "url": source.url}


async def handle_list_sources(request: web.Request) -> web.StreamResponse:
    try:
        owner = _owner_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    store = request.app[STORE_KEY]
    sources = SourceStore(store).list_for_owner(owner)
    return web.json_response({"sources": [_source_payload(item) for item in sources]})


async def _read_source_fields(request: web.Request) -> tuple[str, str]:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ContentTypeError, ValueError, UnicodeDecodeError):
        return "", ""
    if not isinstance(payload, dict):
        return "", ""
    title = payload.get("title", "")
    url = payload.get("url", "")
    title_text = title.strip() if isinstance(title, str) else ""
    url_text = url.strip() if isinstance(url, str) else ""
    return title_text, url_text


async def handle_create_source(request: web.Request) -> web.StreamResponse:
    store = request.app[STORE_KEY]
    try:
        owner = _owner_from_request(request)
        title, url = await _read_source_fields(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    if not title or not url:
        return _json_error(400, "Не удалось сохранить")
    source = SourceStore(store).insert(title, url, owner=owner)
    return web.json_response(_source_payload(source))


async def handle_delete_source(request: web.Request) -> web.StreamResponse:
    try:
        owner = _owner_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    try:
        source_id = int(request.match_info["id"])
    except (TypeError, ValueError):
        return _json_error(400, "invalid id")
    store = request.app[STORE_KEY]
    removed = SourceStore(store).delete_for_owner(source_id, owner)
    if not removed:
        return _json_error(404, "not found")
    return web.json_response({"ok": True})

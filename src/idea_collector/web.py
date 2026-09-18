from __future__ import annotations

import json
from pathlib import Path

from aiohttp import web

from idea_collector.auth import AuthError, init_data_from_headers, require_operator
from idea_collector.capture import capture_payload, capture_text
from idea_collector.config import Config
from idea_collector.db import IdeaStore
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
    assets = webapp_assets_dir()
    if assets is not None:
        app.router.add_static("/assets", assets)
    return app


def _operator_from_request(request: web.Request) -> None:
    config = request.app[CONFIG_KEY]
    init_data = init_data_from_headers(dict(request.headers))
    require_operator(init_data, config)


def _json_error(status: int, message: str) -> web.Response:
    return web.json_response({"error": message}, status=status)


async def handle_index(request: web.Request) -> web.StreamResponse:
    store = request.app[STORE_KEY]
    path = webapp_index_path()
    if not path.is_file():
        raise web.HTTPNotFound(text="webapp index is missing; build webapp/dist")
    html = path.read_text(encoding="utf-8")
    body = inject_count(html, store.count())
    return web.Response(text=body, content_type="text/html")


async def handle_count(request: web.Request) -> web.StreamResponse:
    try:
        _operator_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    store = request.app[STORE_KEY]
    return web.json_response({"count": store.count()})


async def handle_list_ideas(request: web.Request) -> web.StreamResponse:
    try:
        _operator_from_request(request)
    except AuthError as exc:
        return _json_error(exc.status, exc.message)
    store = request.app[STORE_KEY]
    ideas = store.list_all()
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
        _operator_from_request(request)
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
    )
    if result.error or result.idea is None:
        return _json_error(500, result.error or "Не удалось сохранить")
    return web.json_response(capture_payload(result))

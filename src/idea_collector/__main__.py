from __future__ import annotations

import asyncio
import sys

from aiogram import Bot
from aiohttp import web

from idea_collector.bot import configure_menu_button, create_dispatcher
from idea_collector.config import ConfigError, load_config
from idea_collector.db import IdeaStore
from idea_collector.enrich import Enricher
from idea_collector.llm import LlmExtractor
from idea_collector.web import create_web_app


async def run() -> None:
    config = load_config()
    store = IdeaStore(config.sqlite_path)
    llm = LlmExtractor(config)
    enricher = Enricher(store, llm)
    app = create_web_app(config, store, enricher)
    runner = web.AppRunner(app)
    bot: Bot | None = None
    try:
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", config.port)
        await site.start()
        bot = Bot(token=config.bot_token)
        dispatcher = create_dispatcher(config, store, enricher)
        await configure_menu_button(bot, config)
        await dispatcher.start_polling(bot)
    finally:
        await runner.cleanup()
        if bot is not None:
            await bot.session.close()
        await enricher.drain()
        store.close()


def main() -> None:
    try:
        asyncio.run(run())
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

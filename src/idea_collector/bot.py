from __future__ import annotations

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from idea_collector.capture import CaptureResult, capture_text
from idea_collector.config import Config
from idea_collector.db import IdeaStore
from idea_collector.enrich import Enricher

router = Router()


def create_dispatcher(
    config: Config,
    store: IdeaStore,
    enricher: Enricher,
) -> Dispatcher:
    dp = Dispatcher()
    dp["config"] = config
    dp["store"] = store
    dp["enricher"] = enricher
    dp.include_router(router)
    return dp


async def configure_menu_button(bot: Bot, config: Config) -> None:
    if not config.public_base_url:
        return
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Карман",
            web_app=WebAppInfo(url=config.public_base_url),
        )
    )


def bot_reply(result: CaptureResult) -> str | None:
    if result.ignored:
        return None
    if result.error:
        return result.error
    return str(result.count)


def _web_app_keyboard(config: Config) -> InlineKeyboardMarkup | None:
    if not config.public_base_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть",
                    web_app=WebAppInfo(url=config.public_base_url),
                )
            ]
        ]
    )


@router.message(CommandStart())
async def on_start(message: Message, config: Config) -> None:
    user = message.from_user
    if user is None or user.id != config.operator_telegram_id:
        return
    keyboard = _web_app_keyboard(config)
    await message.answer("Карман", reply_markup=keyboard)


@router.message(F.text)
async def on_text(
    message: Message,
    config: Config,
    store: IdeaStore,
    enricher: Enricher,
) -> None:
    user = message.from_user
    if user is None:
        return
    text = message.text or ""
    if text.startswith("/"):
        return
    result = capture_text(
        store,
        enricher,
        user_id=user.id,
        operator_id=config.operator_telegram_id,
        text=text,
    )
    reply = bot_reply(result)
    if reply is None:
        return
    try:
        await message.answer(reply)
    except TelegramAPIError:
        return

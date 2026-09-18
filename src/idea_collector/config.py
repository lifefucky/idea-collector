from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED = (
    "BOT_TOKEN",
    "OPERATOR_TELEGRAM_ID",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
)


class ConfigError(Exception):
    """Raised when required environment is missing or invalid."""


@dataclass(frozen=True)
class Config:
    bot_token: str
    operator_telegram_id: int
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    public_base_url: str
    sqlite_path: str
    port: int


def load_config(env: Mapping[str, str] | None = None) -> Config:
    source = env if env is not None else os.environ
    missing = [name for name in REQUIRED if not str(source.get(name, "")).strip()]
    if missing:
        raise ConfigError(
            "Missing required environment: " + ", ".join(missing)
        )

    raw_operator = str(source["OPERATOR_TELEGRAM_ID"]).strip()
    try:
        operator_id = int(raw_operator)
    except ValueError as exc:
        raise ConfigError("OPERATOR_TELEGRAM_ID must be an integer") from exc

    raw_port = str(source.get("PORT", "8080")).strip() or "8080"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ConfigError("PORT must be an integer") from exc

    sqlite_path = str(source.get("SQLITE_PATH", "ideas.db")).strip() or "ideas.db"
    public_base_url = str(source.get("PUBLIC_BASE_URL", "")).strip()

    return Config(
        bot_token=str(source["BOT_TOKEN"]).strip(),
        operator_telegram_id=operator_id,
        openai_base_url=str(source["OPENAI_BASE_URL"]).strip(),
        openai_api_key=str(source["OPENAI_API_KEY"]).strip(),
        openai_model=str(source["OPENAI_MODEL"]).strip(),
        public_base_url=public_base_url.rstrip("/"),
        sqlite_path=sqlite_path,
        port=port,
    )

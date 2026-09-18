from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from idea_collector.config import Config


class AuthError(Exception):
    """initData is missing, invalid, or not the operator."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class TelegramUser:
    id: int


def parse_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise AuthError(401, "invalid initData")
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs.items())
    )
    secret = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    computed = hmac.new(
        secret, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    try:
        if not hmac.compare_digest(computed, received_hash):
            raise AuthError(401, "invalid initData")
    except (TypeError, ValueError) as exc:
        raise AuthError(401, "invalid initData") from exc
    _require_fresh_auth_date(pairs)
    return pairs


def _require_fresh_auth_date(fields: dict[str, str]) -> None:
    try:
        auth_date = int(fields.get("auth_date", ""))
    except (TypeError, ValueError) as exc:
        raise AuthError(401, "invalid initData") from exc
    if int(time.time()) - auth_date > 86400:
        raise AuthError(401, "invalid initData")


def user_from_init_data(fields: dict[str, str]) -> TelegramUser:
    raw_user = fields.get("user", "")
    try:
        payload = json.loads(raw_user)
        user_id = int(payload["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AuthError(401, "invalid initData") from exc
    return TelegramUser(id=user_id)


def require_operator(init_data: str | None, config: Config) -> TelegramUser:
    if not init_data:
        raise AuthError(401, "invalid initData")
    fields = parse_init_data(init_data, config.bot_token)
    user = user_from_init_data(fields)
    if user.id != config.operator_telegram_id:
        raise AuthError(403, "forbidden")
    return user


def init_data_from_headers(headers: dict[str, str]) -> str | None:
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    if authorization.lower().startswith("tma "):
        return authorization[4:]
    return (
        headers.get("X-Telegram-Init-Data")
        or headers.get("x-telegram-init-data")
    )

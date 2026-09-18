from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from idea_collector.config import load_config

BOT_TOKEN = "123456:TESTTOKEN"
OPERATOR_ID = 42


def sample_config(**overrides: str):
    env = {
        "BOT_TOKEN": BOT_TOKEN,
        "OPERATOR_TELEGRAM_ID": str(OPERATOR_ID),
        "OPENAI_BASE_URL": "https://llm.test/v1",
        "OPENAI_API_KEY": "sk-test",
        "OPENAI_MODEL": "test-model",
        "PUBLIC_BASE_URL": "https://pocket.test",
        "SQLITE_PATH": ":memory:",
        **overrides,
    }
    return load_config(env)


def make_init_data(user_id: int, bot_token: str = BOT_TOKEN) -> str:
    user = json.dumps(
        {"id": user_id, "first_name": "Op"},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "abc",
        "user": user,
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    digest = hmac.new(
        secret, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return urlencode({**fields, "hash": digest})

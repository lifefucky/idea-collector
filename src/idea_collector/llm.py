from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from idea_collector.config import Config
from idea_collector.shelves import SHELVES_MD

SYSTEM_PROMPT = """You extract three fields from an idea dump.
Reply with a JSON object only.
Keys allowed: source, short_name, description. No other keys.
No evaluative fields.

source: the shelf name per the rules below.
Use an empty string when the source is not specified.
short_name: a short label for the idea.
description: the idea text to copy later.

Shelf rules:
""" + SHELVES_MD


@dataclass(frozen=True)
class Extraction:
    source: str
    short_name: str
    description: str


def completions_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


class LlmExtractor:
    def __init__(
        self,
        config: Config,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None
        self.calls = 0

    async def extract(self, raw_text: str) -> Extraction | None:
        self.calls += 1
        payload = {
            "model": self._config.openai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
        }
        try:
            client = self._client or httpx.AsyncClient(timeout=30.0)
            try:
                response = await client.post(
                    completions_url(self._config.openai_base_url),
                    headers={
                        "Authorization": f"Bearer {self._config.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            finally:
                if self._owns_client:
                    await client.aclose()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, KeyError):
            return None
        return parse_extraction(body)


def parse_extraction(body: Any) -> Extraction | None:
    try:
        content = body["choices"][0]["message"]["content"]
        data = json.loads(content) if isinstance(content, str) else content
    except (KeyError, TypeError, IndexError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    source = data.get("source")
    short_name = data.get("short_name")
    description = data.get("description")
    if source is None and short_name is None and description is None:
        return None
    return Extraction(
        source="" if source is None else str(source),
        short_name="" if short_name is None else str(short_name),
        description="" if description is None else str(description),
    )

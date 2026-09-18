from __future__ import annotations

import json

import httpx
import pytest

from idea_collector.enrich import Enricher, apply_extraction
from idea_collector.llm import SYSTEM_PROMPT, Extraction, LlmExtractor, parse_extraction
from idea_collector.shelves import OWN_SHELF, SHELVES_MD


def test_prompt_includes_shelves_md() -> None:
    assert "source" in SYSTEM_PROMPT
    assert "short_name" in SYSTEM_PROMPT
    assert "description" in SYSTEM_PROMPT
    assert SHELVES_MD in SYSTEM_PROMPT
    assert "No evaluative fields" in SYSTEM_PROMPT


def test_parse_extraction_ok_and_strips_extra_fields() -> None:
    body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "source": "ProductHunt",
                            "short_name": "Short",
                            "description": "Desc",
                            "market_size": "should be ignored",
                        }
                    )
                }
            }
        ]
    }
    extracted = parse_extraction(body)
    assert extracted is not None
    assert extracted.source == "ProductHunt"
    assert extracted.short_name == "Short"
    assert extracted.description == "Desc"
    assert not hasattr(extracted, "market_size")


def test_empty_source_maps_to_own_shelf() -> None:
    extracted = parse_extraction(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "source": "",
                                "short_name": "Name",
                                "description": "Body",
                            }
                        )
                    }
                }
            ]
        }
    )
    source, short_name, description = apply_extraction("raw", extracted)
    assert source == OWN_SHELF
    assert short_name == "Name"
    assert description == "Body"


def test_unknown_aggregator_kept() -> None:
    extracted = parse_extraction(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "source": "BetaList",
                                "short_name": "X",
                                "description": "Y",
                            }
                        )
                    }
                }
            ]
        }
    )
    source, _, _ = apply_extraction("raw", extracted)
    assert source == "BetaList"


def test_llm_fail_keeps_raw() -> None:
    source, short_name, description = apply_extraction("raw dump", None)
    assert source == OWN_SHELF
    assert short_name == "raw dump"
    assert description == "raw dump"


@pytest.mark.asyncio
async def test_llm_http_fail_does_not_retry(config) -> None:
    calls = {"n": 0}

    def on_request(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, text="nope")

    client = httpx.AsyncClient(transport=httpx.MockTransport(on_request))
    llm = LlmExtractor(config, client=client)
    result = await llm.extract("an idea")
    await client.aclose()
    assert result is None
    assert calls["n"] == 1
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_llm_http_ok(config) -> None:
    def on_request(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["messages"][0]["content"] == SYSTEM_PROMPT
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "source": "Product Radar",
                                    "short_name": "Radar",
                                    "description": "from radar",
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(on_request))
    llm = LlmExtractor(config, client=client)
    result = await llm.extract("idea from product radar")
    await client.aclose()
    assert result is not None
    assert result.source == "Product Radar"


@pytest.mark.asyncio
async def test_enricher_fail_writes_own_raw(store, config) -> None:
    class FailLlm:
        async def extract(self, raw_text: str):
            return None

    idea, _ = store.insert("keep me")
    enricher = Enricher(store, FailLlm())  # type: ignore[arg-type]
    await enricher._run(idea.id, "keep me")
    updated = store.get(idea.id)
    assert updated is not None
    assert updated.source == OWN_SHELF
    assert updated.short_name == "keep me"
    assert updated.description == "keep me"


@pytest.mark.asyncio
async def test_enricher_success_writes_extraction(store, config) -> None:
    class OkLlm:
        async def extract(self, raw_text: str):
            return Extraction(
                source="ProductHunt",
                short_name="Short",
                description="Copy me",
            )

    idea, _ = store.insert("raw dump")
    enricher = Enricher(store, OkLlm())  # type: ignore[arg-type]
    await enricher._run(idea.id, "raw dump")
    updated = store.get(idea.id)
    assert updated is not None
    assert updated.source == "ProductHunt"
    assert updated.short_name == "Short"
    assert updated.description == "Copy me"

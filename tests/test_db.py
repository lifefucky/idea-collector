from __future__ import annotations

import sqlite3

import pytest

from idea_collector.config import ConfigError, load_config
from idea_collector.db import IdeaStore
from idea_collector.shelves import OWN_SHELF, present_idea
from tests.helpers import OPERATOR_ID


def test_insert_count_list_and_enrichment(store: IdeaStore) -> None:
    first, count = store.insert("alpha")
    assert count == 1
    assert store.count() == 1
    _, count = store.insert("alpha")
    assert count == 2
    ideas = store.list_all()
    assert [idea.raw_text for idea in ideas] == ["alpha", "alpha"]
    assert ideas[0].source is None
    assert ideas[0].short_name is None
    store.update_enrichment(
        first.id,
        source="ProductHunt",
        short_name="Short",
        description="Copy me",
    )
    updated = store.get(first.id)
    assert updated is not None
    assert updated.source == "ProductHunt"
    assert updated.short_name == "Short"
    assert updated.description == "Copy me"


def test_pending_row_uses_raw_text(store: IdeaStore) -> None:
    idea, _ = store.insert("raw dump")
    presented = present_idea(idea)
    assert presented["label"] == "raw dump"
    assert presented["copy"] == "raw dump"
    assert presented["shelf"] == OWN_SHELF


def test_persist_fail_does_not_store() -> None:
    class BoomStore(IdeaStore):
        def insert(self, raw_text: str):  # type: ignore[override]
            raise sqlite3.OperationalError("disk")

    boom = BoomStore(":memory:")
    with pytest.raises(sqlite3.OperationalError):
        boom.insert("nope")
    assert boom.count() == 0
    boom.close()


def test_config_boot_fail_without_required_env() -> None:
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(
            {
                "OPERATOR_TELEGRAM_ID": str(OPERATOR_ID),
                "OPENAI_BASE_URL": "https://llm.test/v1",
                "OPENAI_API_KEY": "sk-test",
                "OPENAI_MODEL": "test-model",
            }
        )
    with pytest.raises(ConfigError, match="OPERATOR_TELEGRAM_ID"):
        load_config(
            {
                "BOT_TOKEN": "x",
                "OPENAI_BASE_URL": "https://llm.test/v1",
                "OPENAI_API_KEY": "sk-test",
                "OPENAI_MODEL": "test-model",
            }
        )
    with pytest.raises(ConfigError, match="OPENAI"):
        load_config(
            {
                "BOT_TOKEN": "x",
                "OPERATOR_TELEGRAM_ID": "1",
            }
        )

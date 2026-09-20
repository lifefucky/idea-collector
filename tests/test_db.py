from __future__ import annotations

import sqlite3

import pytest

from idea_collector.config import ConfigError, load_config
from idea_collector.db import IdeaStore, SourceStore
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


def test_delete_returns_removed_and_remaining_count(store: IdeaStore) -> None:
    first, _ = store.insert("keep")
    second, _ = store.insert("gone")
    removed, count = store.delete(second.id)
    assert removed is True
    assert count == 1
    assert store.count() == 1
    assert store.get(second.id) is None
    assert store.get(first.id) is not None
    missing, remaining = store.delete(second.id)
    assert missing is False
    assert remaining == 1
    assert store.list_all()[0].id == first.id
    last_removed, empty = store.delete(first.id)
    assert last_removed is True
    assert empty == 0
    assert store.count() == 0


def test_source_store_insert_list_delete_missing_same_db(store: IdeaStore) -> None:
    sources = SourceStore(store)
    idea, _ = store.insert("keep idea")
    first = sources.insert("One", "https://one.example")
    second = sources.insert("Two", "https://two.example")
    listed = sources.list_all()
    assert [item.title for item in listed] == ["One", "Two"]
    assert [item.url for item in listed] == [
        "https://one.example",
        "https://two.example",
    ]
    assert listed[0].id == first.id
    assert listed[1].id == second.id
    assert store.get(idea.id) is not None
    assert store.count() == 1
    assert sources.delete(second.id) is True
    assert [item.title for item in sources.list_all()] == ["One"]
    assert sources.get(second.id) is None
    assert sources.delete(second.id) is False
    assert sources.delete(999_999) is False
    remaining = store.list_all()
    assert len(remaining) == 1
    assert remaining[0].raw_text == "keep idea"
    assert remaining[0].source is None


def test_source_store_memory_connections_are_separate(store: IdeaStore) -> None:
    sources = SourceStore(store)
    sources.insert("Doc", "https://doc.example")
    other = IdeaStore(":memory:")
    other_sources = SourceStore(other)
    try:
        assert other_sources.list_all() == []
        assert store.count() == 0
        assert len(sources.list_all()) == 1
        other.insert("other idea")
        assert store.count() == 0
        assert other.count() == 1
    finally:
        other.close()


def test_persist_fail_does_not_store() -> None:
    class BoomStore(IdeaStore):
        def insert(self, raw_text: str, owner: str = "global"):  # type: ignore[override]
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


def test_delete_for_owner_does_not_remove_other_owner(store: IdeaStore) -> None:
    """Attempting to delete another owner's idea should be a no-op."""

    first_owner = "tg:1"
    second_owner = "tg:2"
    keep, _ = store.insert("keep", owner=first_owner)
    other, _ = store.insert("other", owner=second_owner)

    removed, remaining = store.delete_for_owner(other.id, first_owner)
    assert removed is False
    # First owner still sees only their own idea.
    assert remaining == 1
    assert store.get(keep.id) is not None
    assert store.get(other.id) is not None


def test_delete_for_local_owner_does_not_delete_global(store: IdeaStore) -> None:
    """Local owner pockets must not be able to delete legacy global ideas."""

    # Insert as legacy global owner.
    idea, _ = store.insert("legacy global")
    assert idea.owner == "global"

    removed, remaining = store.delete_for_owner(idea.id, "local:42")
    assert removed is False
    # Local pocket has no ideas visible, so count_for_owner is zero.
    assert remaining == 0
    # The global row must still be present in the database.
    assert store.get(idea.id) is not None

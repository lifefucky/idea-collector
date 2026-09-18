from __future__ import annotations

from idea_collector.db import Idea
from idea_collector.shelves import (
    FOREIGN_APPS_SHELF,
    OWN_SHELF,
    group_by_shelf,
    map_source,
    present_idea,
)


def _idea(
    idea_id: int,
    raw: str,
    *,
    source: str | None = None,
    short_name: str | None = None,
    description: str | None = None,
) -> Idea:
    return Idea(
        id=idea_id,
        raw_text=raw,
        source=source,
        short_name=short_name,
        description=description,
        created_at="2026-01-01T00:00:00+00:00",
    )


def test_empty_source_maps_to_own() -> None:
    assert map_source(None) == OWN_SHELF
    assert map_source("") == OWN_SHELF
    assert map_source("   ") == OWN_SHELF


def test_unknown_aggregator_name_used_as_shelf() -> None:
    assert map_source("BetaList") == "BetaList"


def test_known_shelves_and_foreign_apps() -> None:
    assert map_source("ProductHunt") == "ProductHunt"
    assert map_source("чужие приложения") == FOREIGN_APPS_SHELF
    assert map_source("идея собственная") == OWN_SHELF


def test_group_first_seen_skips_empty_and_mixes_unshelved() -> None:
    ideas = [
        _idea(1, "raw pending"),
        _idea(
            2,
            "ph raw",
            source="ProductHunt",
            short_name="PH idea",
            description="ph copy",
        ),
        _idea(3, "own raw", source="", short_name="Own", description="own copy"),
        _idea(
            4,
            "failed",
            source=OWN_SHELF,
            short_name="failed",
            description="failed",
        ),
        _idea(
            5,
            "radar",
            source="Product Radar",
            short_name="Radar",
            description="radar copy",
        ),
    ]
    shelves = group_by_shelf(ideas)
    names = [shelf["name"] for shelf in shelves]
    assert names == [OWN_SHELF, "ProductHunt", "Product Radar"]
    own_ideas = shelves[0]["ideas"]
    assert [item["id"] for item in own_ideas] == [1, 3, 4]
    assert own_ideas[0]["label"] == "raw pending"
    assert own_ideas[0]["copy"] == "raw pending"
    ph = shelves[1]["ideas"][0]
    assert ph["label"] == "PH idea"
    assert ph["copy"] == "ph copy"


def test_llm_success_row_label_and_copy() -> None:
    presented = present_idea(
        _idea(
            9,
            "long raw",
            source="ProductHunt",
            short_name="Short",
            description="full description",
        )
    )
    assert presented["shelf"] == "ProductHunt"
    assert presented["label"] == "Short"
    assert presented["copy"] == "full description"

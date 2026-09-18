from __future__ import annotations

from pathlib import Path

from idea_collector.db import Idea

OWN_SHELF = "идея собственная"
FOREIGN_APPS_SHELF = "чужие приложения"

SHELVES_MD = (Path(__file__).with_name("shelves.md")).read_text(encoding="utf-8")

_SOURCE_ALIASES = {
    "идея собственная": OWN_SHELF,
    "чужие приложения": FOREIGN_APPS_SHELF,
    "producthunt": "ProductHunt",
    "product hunt": "ProductHunt",
    "product radar": "Product Radar",
    "productradar": "Product Radar",
    "yc": "YC / Y Combinator",
    "y combinator": "YC / Y Combinator",
    "ycombinator": "YC / Y Combinator",
    "yc / y combinator": "YC / Y Combinator",
}


def map_source(source: str | None) -> str:
    if source is None:
        return OWN_SHELF
    cleaned = " ".join(str(source).split())
    if not cleaned:
        return OWN_SHELF
    alias = _SOURCE_ALIASES.get(cleaned.casefold())
    if alias is not None:
        return alias
    return cleaned


def present_idea(idea: Idea) -> dict[str, object]:
    label = idea.short_name if idea.short_name else idea.raw_text
    copy_text = idea.description if idea.description else idea.raw_text
    return {
        "id": idea.id,
        "label": label,
        "copy": copy_text,
        "shelf": map_source(idea.source),
    }


def group_by_shelf(ideas: list[Idea]) -> list[dict[str, object]]:
    order: list[str] = []
    buckets: dict[str, list[dict[str, object]]] = {}
    for idea in ideas:
        presented = present_idea(idea)
        shelf = str(presented["shelf"])
        if shelf not in buckets:
            buckets[shelf] = []
            order.append(shelf)
        buckets[shelf].append(presented)
    return [
        {"name": name, "ideas": buckets[name]}
        for name in order
        if buckets[name]
    ]

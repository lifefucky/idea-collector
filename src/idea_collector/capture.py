from __future__ import annotations

from dataclasses import dataclass

from idea_collector.db import Idea, IdeaStore
from idea_collector.enrich import Enricher
from idea_collector.shelves import present_idea


@dataclass(frozen=True)
class CaptureResult:
    ignored: bool = False
    error: str | None = None
    idea: Idea | None = None
    count: int | None = None


PERSIST_ERROR = "Не удалось сохранить"


def capture_text(
    store: IdeaStore,
    enricher: Enricher,
    *,
    user_id: int,
    operator_id: int,
    text: str,
) -> CaptureResult:
    if user_id != operator_id:
        return CaptureResult(ignored=True)
    stripped = text.strip()
    if not stripped:
        return CaptureResult(error=PERSIST_ERROR)
    try:
        idea, count = store.insert(stripped)
    except Exception:
        return CaptureResult(error=PERSIST_ERROR)
    try:
        enricher.queue(idea.id, stripped)
    except Exception:
        pass
    return CaptureResult(idea=idea, count=count)


def capture_payload(result: CaptureResult) -> dict[str, object]:
    assert result.idea is not None
    presented = present_idea(result.idea)
    return {
        "id": presented["id"],
        "label": presented["label"],
        "copy": presented["copy"],
        "shelf": presented["shelf"],
        "count": result.count,
    }

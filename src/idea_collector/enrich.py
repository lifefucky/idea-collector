from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from idea_collector.db import IdeaStore
from idea_collector.llm import Extraction, LlmExtractor
from idea_collector.shelves import OWN_SHELF, map_source

Schedule = Callable[[Awaitable[None]], asyncio.Task[None]]


class Enricher:
    def __init__(
        self,
        store: IdeaStore,
        llm: LlmExtractor,
        schedule: Schedule | None = None,
    ) -> None:
        self._store = store
        self._llm = llm
        self._schedule = schedule or asyncio.create_task
        self._tasks: set[asyncio.Task[None]] = set()
        self.queued = 0

    def queue(self, idea_id: int, raw_text: str) -> asyncio.Task[None]:
        self.queued += 1
        task = self._schedule(self._run(idea_id, raw_text))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(self, idea_id: int, raw_text: str) -> None:
        try:
            extracted = await self._llm.extract(raw_text)
        except Exception:
            extracted = None
        if extracted is None:
            self._store.update_enrichment(
                idea_id,
                source=OWN_SHELF,
                short_name=raw_text,
                description=raw_text,
            )
            return
        source = map_source(extracted.source)
        short_name = extracted.short_name.strip() or raw_text
        description = extracted.description.strip() or raw_text
        self._store.update_enrichment(
            idea_id,
            source=source,
            short_name=short_name,
            description=description,
        )


def apply_extraction(
    raw_text: str, extracted: Extraction | None
) -> tuple[str, str, str]:
    if extracted is None:
        return OWN_SHELF, raw_text, raw_text
    source = map_source(extracted.source)
    short_name = extracted.short_name.strip() or raw_text
    description = extracted.description.strip() or raw_text
    return source, short_name, description

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from idea_collector.db import Idea
from idea_collector.shelves import present_idea


def csv_filename(when: datetime) -> str:
    moment = when.astimezone(UTC) if when.tzinfo is not None else when
    return f"ideas-{moment.date().isoformat()}.csv"


def csv_bytes(ideas: list[Idea]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["title", "description"])
    for idea in ideas:
        presented = present_idea(idea)
        writer.writerow([presented["label"], presented["copy"]])
    return buffer.getvalue().encode("utf-8")

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from idea_collector.csv_export import csv_bytes, csv_filename
from idea_collector.db import Idea


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


def _rows(payload: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(payload.decode("utf-8"))))


def test_csv_bytes_unenriched_quotes_comma_newline_cyrillic() -> None:
    raw = 'Идея, "цитата"\nвторая строка'
    payload = csv_bytes([_idea(1, raw)])
    assert not payload.startswith(b"\xef\xbb\xbf")
    rows = _rows(payload)
    assert rows[0] == ["title", "description"]
    assert rows[1] == [raw, raw]


def test_csv_bytes_empty_is_header_only() -> None:
    payload = csv_bytes([])
    assert _rows(payload) == [["title", "description"]]


def test_csv_filename_uses_utc_date() -> None:
    when = datetime(2026, 9, 20, 22, 15, tzinfo=UTC)
    assert csv_filename(when) == "ideas-2026-09-20.csv"

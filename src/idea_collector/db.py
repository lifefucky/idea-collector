from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Idea:
    id: int
    raw_text: str
    source: str | None
    short_name: str | None
    description: str | None
    created_at: str


@dataclass(frozen=True)
class Source:
    id: int
    title: str
    url: str
    created_at: str


def _now() -> str:
    return datetime.now(UTC).isoformat()


class IdeaStore:
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_text TEXT NOT NULL,
                    source TEXT,
                    short_name TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def insert(self, raw_text: str) -> tuple[Idea, int]:
        created_at = _now()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO ideas (
                    raw_text, source, short_name, description, created_at
                )
                VALUES (?, NULL, NULL, NULL, ?)
                """,
                (raw_text, created_at),
            )
            self._conn.commit()
            idea_id = int(cursor.lastrowid)
            row = self._conn.execute("SELECT COUNT(*) AS n FROM ideas").fetchone()
            count = int(row["n"])
        return (
            Idea(
                id=idea_id,
                raw_text=raw_text,
                source=None,
                short_name=None,
                description=None,
                created_at=created_at,
            ),
            count,
        )

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM ideas").fetchone()
        return int(row["n"])

    def list_all(self) -> list[Idea]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, raw_text, source, short_name, description, created_at
                FROM ideas
                ORDER BY id ASC
                """
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, idea_id: int) -> Idea | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, raw_text, source, short_name, description, created_at
                FROM ideas
                WHERE id = ?
                """,
                (idea_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def update_enrichment(
        self,
        idea_id: int,
        *,
        source: str | None,
        short_name: str | None,
        description: str | None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE ideas
                SET source = ?, short_name = ?, description = ?
                WHERE id = ?
                """,
                (source, short_name, description, idea_id),
            )
            self._conn.commit()

    def delete(self, idea_id: int) -> tuple[bool, int]:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM ideas WHERE id = ?",
                (idea_id,),
            )
            self._conn.commit()
            removed = cursor.rowcount > 0
            row = self._conn.execute("SELECT COUNT(*) AS n FROM ideas").fetchone()
            count = int(row["n"])
        return removed, count

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Idea:
        return Idea(
            id=int(row["id"]),
            raw_text=str(row["raw_text"]),
            source=row["source"],
            short_name=row["short_name"],
            description=row["description"],
            created_at=str(row["created_at"]),
        )


class SourceStore:
    def __init__(self, idea_store: IdeaStore) -> None:
        self._lock = idea_store._lock
        self._conn = idea_store._conn
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def insert(self, title: str, url: str) -> Source:
        created_at = _now()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO sources (title, url, created_at)
                VALUES (?, ?, ?)
                """,
                (title, url, created_at),
            )
            self._conn.commit()
            source_id = int(cursor.lastrowid)
        return Source(id=source_id, title=title, url=url, created_at=created_at)

    def list_all(self) -> list[Source]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, title, url, created_at
                FROM sources
                ORDER BY id ASC
                """
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, source_id: int) -> Source | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, title, url, created_at
                FROM sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def delete(self, source_id: int) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM sources WHERE id = ?",
                (source_id,),
            )
            self._conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Source:
        return Source(
            id=int(row["id"]),
            title=str(row["title"]),
            url=str(row["url"]),
            created_at=str(row["created_at"]),
        )

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Idea(BaseModel):
    """Domain model for a stored idea.

    Pydantic adds runtime validation and keeps the data immutable, similar to the
    previous frozen dataclass, while being friendlier to API and schema tooling.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    raw_text: str
    source: str | None = None
    short_name: str | None = None
    description: str | None = None
    created_at: str
    owner: str = "global"


class Source(BaseModel):
    """Domain model for a source document / link."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    title: str
    url: str
    created_at: str
    owner: str = "global"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _has_column(conn: sqlite3.Connection, table: str, name: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    rows = cursor.fetchall()
    for row in rows:
        if row[1] == name or row["name"] == name:
            return True
    return False


class _Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""


class _IdeaRecord(_Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    short_name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="global")


class _SourceRecord(_Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="global")


def _owner_filter(owner: str, column) -> object:
    """Return a SQLAlchemy filter expression for owner-aware queries.

    Legacy rows with owner == 'global' are treated as Telegram-owned when the
    requested owner starts with "tg:" so existing data remains visible there.
    Local owners only see their own rows.
    """

    from sqlalchemy import or_

    if owner.startswith("tg:"):
        return or_(column == owner, column == "global")
    return column == owner


def _init_disk_schema(path: str) -> None:
    """Run lightweight migrations on an existing on-disk SQLite file.

    This keeps backward compatibility for older databases that may not yet have
    the owner column while the application code uses SQLAlchemy for normal I/O.
    """

    if path == ":memory:":
        # In-memory databases are always created fresh by SQLAlchemy.
        return

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                source TEXT,
                short_name TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'global'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'global'
            )
            """
        )
        if not _has_column(conn, "ideas", "owner"):
            conn.execute(
                "ALTER TABLE ideas ADD COLUMN owner TEXT NOT NULL DEFAULT 'global'"
            )
        if not _has_column(conn, "sources", "owner"):
            conn.execute(
                "ALTER TABLE sources ADD COLUMN owner TEXT NOT NULL DEFAULT 'global'"
            )
        conn.commit()
    finally:
        conn.close()


class IdeaStore:
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()

        # Keep SQLite-compatible behaviour: path may be a file path or ':memory:'.
        if path != ":memory:":
            _init_disk_schema(path)
            url = f"sqlite+pysqlite:///{path}"
        else:
            url = "sqlite+pysqlite:///:memory:"

        # Single engine per store; sessions are short-lived and created per op.
        self._engine = create_engine(
            url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            class_=Session,
        )

        # Ensure tables exist for this engine (no-op if already migrated).
        _Base.metadata.create_all(self._engine)

    def _session(self) -> Session:
        return self._SessionLocal()

    def insert(self, raw_text: str, owner: str = "global") -> tuple[Idea, int]:
        created_at = _now()
        with self._lock, self._session() as session:
            row = _IdeaRecord(
                raw_text=raw_text,
                source=None,
                short_name=None,
                description=None,
                created_at=created_at,
                owner=owner,
            )
            session.add(row)
            session.flush()  # populate PK

            # Count ideas for this owner including legacy 'global' rows where applicable.
            count_stmt = select(func.count()).select_from(_IdeaRecord).where(
                _owner_filter(owner, _IdeaRecord.owner)
            )
            count_val = session.scalar(count_stmt) or 0

            session.commit()

        idea = Idea.model_validate(row)
        return idea, int(count_val)

    def count(self) -> int:
        """Return total ideas across all owners (legacy behavior)."""

        with self._lock, self._session() as session:
            stmt = select(func.count()).select_from(_IdeaRecord)
            value = session.scalar(stmt) or 0
        return int(value)

    def count_for_owner(self, owner: str) -> int:
        with self._lock, self._session() as session:
            stmt = (
                select(func.count())
                .select_from(_IdeaRecord)
                .where(_owner_filter(owner, _IdeaRecord.owner))
            )
            value = session.scalar(stmt) or 0
        return int(value)

    def list_all(self) -> list[Idea]:
        with self._lock, self._session() as session:
            stmt = select(_IdeaRecord).order_by(_IdeaRecord.id.asc())
            rows = session.scalars(stmt).all()
        return [Idea.model_validate(row) for row in rows]

    def list_for_owner(self, owner: str) -> list[Idea]:
        with self._lock, self._session() as session:
            stmt = (
                select(_IdeaRecord)
                .where(_owner_filter(owner, _IdeaRecord.owner))
                .order_by(_IdeaRecord.id.asc())
            )
            rows = session.scalars(stmt).all()
        return [Idea.model_validate(row) for row in rows]

    def get(self, idea_id: int) -> Idea | None:
        with self._lock, self._session() as session:
            row = session.get(_IdeaRecord, idea_id)
        if row is None:
            return None
        return Idea.model_validate(row)

    def update_enrichment(
        self,
        idea_id: int,
        *,
        source: str | None,
        short_name: str | None,
        description: str | None,
    ) -> None:
        with self._lock, self._session() as session:
            row = session.get(_IdeaRecord, idea_id)
            if row is None:
                return
            row.source = source
            row.short_name = short_name
            row.description = description
            session.commit()

    def delete(self, idea_id: int) -> tuple[bool, int]:
        """Delete by id without scoping to an owner (legacy behavior)."""

        with self._lock, self._session() as session:
            row = session.get(_IdeaRecord, idea_id)
            removed = row is not None
            if row is not None:
                session.delete(row)
                session.flush()

            # Count remaining ideas across all owners.
            stmt = select(func.count()).select_from(_IdeaRecord)
            remaining = session.scalar(stmt) or 0
            session.commit()

        return removed, int(remaining)

    def delete_for_owner(self, idea_id: int, owner: str) -> tuple[bool, int]:
        with self._lock, self._session() as session:
            # Strict match on id + owner filter.
            stmt = select(_IdeaRecord).where(
                _IdeaRecord.id == idea_id,
                _owner_filter(owner, _IdeaRecord.owner),
            )
            rows = session.scalars(stmt).all()
            removed = bool(rows)
            for row in rows:
                session.delete(row)
            if removed:
                session.flush()

            # Count remaining rows visible to this owner.
            count_stmt = (
                select(func.count())
                .select_from(_IdeaRecord)
                .where(_owner_filter(owner, _IdeaRecord.owner))
            )
            remaining = session.scalar(count_stmt) or 0
            session.commit()

        return removed, int(remaining)

    def close(self) -> None:
        with self._lock:
            self._engine.dispose()


class SourceStore:
    def __init__(self, idea_store: IdeaStore) -> None:
        # Share engine and lock with the associated IdeaStore so both operate
        # on the same underlying database and serialization primitive.
        self._lock = idea_store._lock
        self._engine = idea_store._engine
        self._SessionLocal = idea_store._SessionLocal

        with self._lock, self._SessionLocal() as session:
            _Base.metadata.create_all(self._engine)
            session.commit()

    def _session(self) -> Session:
        return self._SessionLocal()

    def insert(self, title: str, url: str, owner: str = "global") -> Source:
        created_at = _now()
        with self._lock, self._session() as session:
            row = _SourceRecord(
                title=title,
                url=url,
                created_at=created_at,
                owner=owner,
            )
            session.add(row)
            session.commit()
        return Source.model_validate(row)

    def list_all(self) -> list[Source]:
        with self._lock, self._session() as session:
            stmt = select(_SourceRecord).order_by(_SourceRecord.id.asc())
            rows = session.scalars(stmt).all()
        return [Source.model_validate(row) for row in rows]

    def list_for_owner(self, owner: str) -> list[Source]:
        with self._lock, self._session() as session:
            stmt = (
                select(_SourceRecord)
                .where(_owner_filter(owner, _SourceRecord.owner))
                .order_by(_SourceRecord.id.asc())
            )
            rows = session.scalars(stmt).all()
        return [Source.model_validate(row) for row in rows]

    def get(self, source_id: int) -> Source | None:
        with self._lock, self._session() as session:
            row = session.get(_SourceRecord, source_id)
        if row is None:
            return None
        return Source.model_validate(row)

    def delete(self, source_id: int) -> bool:
        with self._lock, self._session() as session:
            row = session.get(_SourceRecord, source_id)
            removed = row is not None
            if row is not None:
                session.delete(row)
                session.commit()
        return removed

    def delete_for_owner(self, source_id: int, owner: str) -> bool:
        with self._lock, self._session() as session:
            stmt = select(_SourceRecord).where(
                _SourceRecord.id == source_id,
                _owner_filter(owner, _SourceRecord.owner),
            )
            rows = session.scalars(stmt).all()
            removed = bool(rows)
            for row in rows:
                session.delete(row)
            if removed:
                session.commit()
        return removed

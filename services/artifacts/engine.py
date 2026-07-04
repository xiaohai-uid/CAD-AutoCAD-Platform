"""ArtifactManager — manage CAD output artifacts with SQLite storage."""

from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ArtifactRecord:
    """A single artifact record stored by the ArtifactManager."""

    job_id: str
    files: dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


class ArtifactManager:
    """Persistent artifact manager backed by SQLite.

    By default uses an in-memory database. Pass a *db_path* to use
    a persistent file-based database.
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    # -- connection management -----------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db_path) if self._db_path else ":memory:",
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row
            self._init_db()
        return self._conn

    def _init_db(self) -> None:
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS artifacts (
                job_id       TEXT PRIMARY KEY,
                files_json   TEXT NOT NULL DEFAULT '{}',
                created_at   TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )"""
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- CRUD -----------------------------------------------------------------

    def store(self, job_id: str, files: dict[str, str], metadata: dict | None = None) -> ArtifactRecord:
        """Store an artifact record (INSERT OR REPLACE)."""
        now = datetime.now(timezone.utc).isoformat()
        record = ArtifactRecord(
            job_id=job_id,
            files=files,
            created_at=now,
            metadata=metadata or {},
        )
        self.conn.execute(
            """INSERT OR REPLACE INTO artifacts (job_id, files_json, created_at, metadata_json)
               VALUES (?, ?, ?, ?)""",
            (job_id, json.dumps(files), now, json.dumps(metadata or {})),
        )
        self.conn.commit()
        return record

    def get(self, job_id: str) -> Optional[ArtifactRecord]:
        """Retrieve a record by *job_id*, or *None* if not found."""
        row = self.conn.execute(
            "SELECT job_id, files_json, created_at, metadata_json FROM artifacts WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return ArtifactRecord(
            job_id=row["job_id"],
            files=json.loads(row["files_json"]),
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )

    def get_all(self) -> list[ArtifactRecord]:
        """Return all records ordered by created_at descending."""
        rows = self.conn.execute(
            "SELECT job_id, files_json, created_at, metadata_json FROM artifacts ORDER BY created_at DESC"
        ).fetchall()
        return [
            ArtifactRecord(
                job_id=r["job_id"],
                files=json.loads(r["files_json"]),
                created_at=r["created_at"],
                metadata=json.loads(r["metadata_json"]),
            )
            for r in rows
        ]

    def delete(self, job_id: str) -> bool:
        """Delete a record by *job_id*. Returns *True* if a row was removed."""
        cur = self.conn.execute(
            "DELETE FROM artifacts WHERE job_id = ?", (job_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def count(self) -> int:
        """Return the total number of stored artifacts."""
        row = self.conn.execute("SELECT COUNT(*) AS cnt FROM artifacts").fetchone()
        return row["cnt"] if row else 0

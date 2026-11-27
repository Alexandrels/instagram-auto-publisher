from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path


@dataclass(frozen=True)
class PublishJob:
    job_id: str
    media_type: str
    media_urls: tuple[str, ...]
    caption: str
    cover_url: str | None
    scheduled_for: datetime


class PublishQueue:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS publish_jobs (
                    job_id TEXT PRIMARY KEY,
                    media_type TEXT NOT NULL,
                    media_urls TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    cover_url TEXT,
                    scheduled_for TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'scheduled',
                    container_id TEXT,
                    media_id TEXT,
                    error TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def enqueue(self, job: PublishJob) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO publish_jobs (
                    job_id, media_type, media_urls, caption, cover_url,
                    scheduled_for, state, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?)
                """,
                (
                    job.job_id,
                    job.media_type,
                    json.dumps(job.media_urls),
                    job.caption,
                    job.cover_url,
                    job.scheduled_for.isoformat(),
                    updated_at,
                ),
            )

    def claim(self, job_id: str) -> bool:
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE publish_jobs
                SET state = 'claiming', updated_at = ?, attempt_count = attempt_count + 1
                WHERE job_id = ? AND state IN ('scheduled', 'retrying')
                """,
                (updated_at, job_id),
            )
        return cursor.rowcount == 1

    def mark_completed(
        self,
        job_id: str,
        container_id: str,
        media_id: str,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE publish_jobs
                SET state = 'completed', container_id = ?, media_id = ?,
                    error = NULL, updated_at = ?
                WHERE job_id = ? AND state != 'completed'
                """,
                (container_id, media_id, updated_at, job_id),
            )

    def mark_failed(
        self,
        job_id: str,
        error: str,
        retry: bool,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        state = "retrying" if retry else "failed"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE publish_jobs
                SET state = ?, error = ?, updated_at = ?
                WHERE job_id = ? AND state != 'completed'
                """,
                (state, error, updated_at, job_id),
            )

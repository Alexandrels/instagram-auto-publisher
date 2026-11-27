from datetime import datetime, timedelta, timezone
import sqlite3
from pathlib import Path


class PublishLedger:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._connect().close()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS published_media (
                    media_id TEXT PRIMARY KEY,
                    published_at TEXT NOT NULL
                )
                """
            )

    def record(self, media_id: str) -> None:
        published_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO published_media
                (media_id, published_at)
                VALUES (?, ?)
                """,
                (media_id, published_at),
            )

    def count_last_24_hours(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT published_at FROM published_media"
            ).fetchall()

        return sum(
            1
            for (published_at,) in rows
            if datetime.fromisoformat(published_at) >= cutoff
        )

    def can_publish(self, conservative_limit: int = 25) -> bool:
        return self.count_last_24_hours() < conservative_limit

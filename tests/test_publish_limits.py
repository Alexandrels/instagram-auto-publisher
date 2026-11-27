from datetime import datetime, timedelta, timezone
from pathlib import Path

from instagram_publisher.publish_limits import PublishLedger


def test_publish_ledger_counts_only_last_24_hours(tmp_path: Path) -> None:
    database = tmp_path / "publish.db"
    ledger = PublishLedger(database)
    ledger.record("media-1")

    assert ledger.count_last_24_hours() == 1
    assert ledger.can_publish(conservative_limit=2)

    with ledger._connect() as connection:
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        connection.execute(
            "INSERT INTO published_media (media_id, published_at) VALUES (?, ?)",
            ("media-old", old),
        )

    assert ledger.count_last_24_hours() == 1

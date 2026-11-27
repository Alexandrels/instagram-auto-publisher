from datetime import datetime, timezone
from pathlib import Path

from instagram_publisher.scheduler import PublishJob, PublishQueue


def test_queue_claim_is_idempotent(tmp_path: Path) -> None:
    queue = PublishQueue(tmp_path / "queue.db")
    job = PublishJob(
        job_id="job-1",
        media_type="IMAGE",
        media_urls=("https://example.com/image.jpg",),
        caption="Teste",
        cover_url=None,
        scheduled_for=datetime.now(timezone.utc),
    )
    queue.enqueue(job)

    assert queue.claim("job-1")
    assert not queue.claim("job-1")


def test_queue_marks_completed(tmp_path: Path) -> None:
    queue = PublishQueue(tmp_path / "queue.db")
    job = PublishJob(
        job_id="job-2",
        media_type="REELS",
        media_urls=("https://example.com/reel.mp4",),
        caption="Reel",
        cover_url="https://example.com/cover.jpg",
        scheduled_for=datetime.now(timezone.utc),
    )
    queue.enqueue(job)
    assert queue.claim("job-2")

    queue.mark_completed("job-2", "container-1", "media-1")
    queue.mark_failed("job-2", "erro depois do sucesso", retry=True)

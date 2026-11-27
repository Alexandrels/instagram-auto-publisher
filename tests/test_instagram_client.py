from unittest.mock import Mock

import pytest
import requests

from instagram_publisher.config import Settings
from instagram_publisher.exceptions import (
    ContainerProcessingError,
    ContainerTimeoutError,
    MetaApiError,
)
from instagram_publisher.instagram_client import InstagramClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ig_user_id="17841400000000000",
        access_token="test-token",
        graph_api_version="v26.0",
    )


def mock_response(
    payload: dict,
    status_code: int = 200,
) -> Mock:
    response = Mock(spec=requests.Response)
    response.ok = 200 <= status_code < 300
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_create_image_container(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.return_value = mock_response({"id": "container-123"})
    client = InstagramClient(settings, session=session)

    container_id = client.create_image_container(
        "https://example.com/image.jpg",
        "Legenda de teste",
    )

    assert container_id == "container-123"
    assert session.post.call_args.kwargs["data"] == {
        "media_type": "IMAGE",
        "image_url": "https://example.com/image.jpg",
        "caption": "Legenda de teste",
        "access_token": "test-token",
    }


def test_create_container_rejects_relative_url(settings: Settings) -> None:
    client = InstagramClient(settings, session=Mock(spec=requests.Session))

    with pytest.raises(ValueError, match="URL publica"):
        client.create_image_container("/image.jpg", "Legenda")


def test_wait_for_finished_container(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.get.side_effect = [
        mock_response({"status": "IN_PROGRESS", "status_code": "IN_PROGRESS"}),
        mock_response({"status": "FINISHED", "status_code": "FINISHED"}),
    ]
    client = InstagramClient(settings, session=session)

    client.wait_for_container(
        "container-123",
        timeout_seconds=30,
        interval_seconds=0,
    )

    assert session.get.call_count == 2


@pytest.mark.parametrize(
    ("status", "status_code"),
    [
        ("ERROR", "MEDIA_ERROR"),
        ("EXPIRED", "EXPIRED"),
    ],
)
def test_wait_rejects_terminal_container_states(
    settings: Settings,
    status: str,
    status_code: str,
) -> None:
    session = Mock(spec=requests.Session)
    session.get.return_value = mock_response(
        {"status": status, "status_code": status_code}
    )
    client = InstagramClient(settings, session=session)

    with pytest.raises(ContainerProcessingError):
        client.wait_for_container("container-123")


def test_wait_times_out(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.get.return_value = mock_response(
        {"status": "IN_PROGRESS", "status_code": "IN_PROGRESS"}
    )
    client = InstagramClient(settings, session=session)
    timestamps = iter((0.0, 2.0))

    with pytest.raises(ContainerTimeoutError):
        client.wait_for_container(
            "container-123",
            timeout_seconds=1,
            interval_seconds=0,
            monotonic=lambda: next(timestamps),
        )


def test_publish_container(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.return_value = mock_response({"id": "media-456"})
    client = InstagramClient(settings, session=session)

    media_id = client.publish_container("container-123")

    assert media_id == "media-456"
    assert session.post.call_args.kwargs["data"]["creation_id"] == "container-123"


def test_publish_image_runs_full_lifecycle(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.side_effect = [
        mock_response({"id": "container-123"}),
        mock_response({"id": "media-456"}),
    ]
    session.get.return_value = mock_response(
        {"status": "FINISHED", "status_code": "FINISHED"}
    )
    client = InstagramClient(settings, session=session)

    media_id = client.publish_image(
        "https://example.com/image.jpg",
        "Legenda",
    )

    assert media_id == "media-456"
    assert session.post.call_count == 2
    assert session.get.call_count == 1


def test_api_error_is_sanitized(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.return_value = mock_response(
        {
            "error": {
                "message": "Too Many Requests",
                "code": 32,
                "error_subcode": 2207051,
                "is_transient": True,
            }
        },
        status_code=429,
    )
    client = InstagramClient(settings, session=session)

    with pytest.raises(MetaApiError) as caught:
        client.create_image_container(
            "https://example.com/image.jpg",
            "Teste",
        )

    error = caught.value
    assert error.code == 32
    assert error.error_subcode == 2207051
    assert error.http_status == 429
    assert error.is_transient
    assert "test-token" not in str(error)


def test_create_carousel_item(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.return_value = mock_response({"id": "item-1"})
    client = InstagramClient(settings, session=session)

    item_id = client.create_carousel_item(
        "https://example.com/image.jpg",
        media_type="IMAGE",
    )

    assert item_id == "item-1"
    data = session.post.call_args.kwargs["data"]
    assert data["is_carousel_item"] == "true"
    assert data["image_url"] == "https://example.com/image.jpg"


def test_publish_reel_creates_reel_container(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.side_effect = [
        mock_response({"id": "reel-container"}),
        mock_response({"id": "reel-media"}),
    ]
    session.get.return_value = mock_response(
        {"status": "FINISHED", "status_code": "FINISHED"}
    )
    client = InstagramClient(settings, session=session)

    media_id = client.publish_reel(
        "https://example.com/reel.mp4",
        "Reel de teste",
        "https://example.com/cover.jpg",
    )

    assert media_id == "reel-media"
    reel_data = session.post.call_args_list[0].kwargs["data"]
    assert reel_data["media_type"] == "REELS"
    assert reel_data["video_url"] == "https://example.com/reel.mp4"
    assert reel_data["cover_url"] == "https://example.com/cover.jpg"


def test_rate_limit_with_backoff_retries(settings: Settings) -> None:
    session = Mock(spec=requests.Session)
    session.post.side_effect = [
        mock_response(
            {
                "error": {
                    "message": "Limit reached",
                    "code": 32,
                    "error_subcode": 2207051,
                    "is_transient": True,
                }
            },
            status_code=429,
        ),
        mock_response({"id": "container-123"}),
    ]
    delays: list[float] = []
    client = InstagramClient(
        settings,
        session=session,
        max_attempts=2,
        sleep=delays.append,
        random_value=lambda start, end: 0.0,
    )

    container_id = client.create_image_container(
        "https://example.com/image.jpg",
        "Teste",
    )

    assert container_id == "container-123"
    assert delays == [1.0]

from collections.abc import Callable
from typing import Any
import random
import time

import requests

from .config import Settings
from .exceptions import (
    ContainerProcessingError,
    ContainerTimeoutError,
    MetaApiError,
)


class InstagramClient:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
        random_value: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.max_attempts = max_attempts
        self.sleep = sleep
        self.random_value = random_value
        self.base_url = (
            f"https://graph.facebook.com/{settings.graph_api_version}"
        )

    @staticmethod
    def _is_retryable(error: MetaApiError) -> bool:
        if error.http_status == 429:
            return True
        if error.code == 32:
            return error.error_subcode == 2207051 or error.is_transient
        return error.is_transient

    @staticmethod
    def _retry_delay(
        attempt: int,
        random_value: Callable[[float, float], float],
    ) -> float:
        base = min(60.0, 1.0 * (2 ** attempt))
        return base + random_value(0.0, base * 0.25)

    @staticmethod
    def _retry_after(response: requests.Response) -> float | None:
        headers = getattr(response, "headers", {}) or {}
        value = headers.get("Retry-After") if hasattr(headers, "get") else None
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        payload = {**data, "access_token": self.settings.access_token}
        last_network_error: requests.RequestException | None = None

        for attempt in range(self.max_attempts):
            try:
                response = self.session.post(
                    f"{self.base_url}/{path}",
                    data=payload,
                    timeout=(10, 60),
                )
            except requests.RequestException as exc:
                last_network_error = exc
                if attempt + 1 >= self.max_attempts:
                    raise RuntimeError(
                        "Falha de rede ao chamar a Graph API"
                    ) from exc
                self.sleep(self._retry_delay(attempt, self.random_value))
                continue

            try:
                body = response.json()
            except requests.exceptions.JSONDecodeError as exc:
                raise RuntimeError("Resposta JSON invalida da Graph API") from exc

            if response.ok:
                return body

            error = body.get("error", {})
            api_error = MetaApiError(
                message=error.get("message", "Erro desconhecido"),
                code=int(error.get("code", response.status_code)),
                error_subcode=error.get("error_subcode"),
                http_status=response.status_code,
                is_transient=bool(error.get("is_transient", False)),
                response=body,
            )
            if (
                not self._is_retryable(api_error)
                or attempt + 1 >= self.max_attempts
            ):
                raise api_error

            retry_after = self._retry_after(response)
            self.sleep(
                retry_after
                if retry_after is not None
                else self._retry_delay(attempt, self.random_value)
            )

        if last_network_error is not None:
            raise RuntimeError("Falha de rede ao chamar a Graph API")
        raise RuntimeError("Tentativas de requisicao agotadas")

    def create_image_container(
        self,
        image_url: str,
        caption: str,
    ) -> str:
        if not image_url.startswith(("http://", "https://")):
            raise ValueError("image_url deve ser uma URL publica")

        body = self._post(
            f"{self.settings.ig_user_id}/media",
            {
                "media_type": "IMAGE",
                "image_url": image_url,
                "caption": caption,
            },
        )
        return str(body["id"])

    def create_carousel_item(
        self,
        media_url: str,
        media_type: str = "IMAGE",
    ) -> str:
        if not media_url.startswith(("http://", "https://")):
            raise ValueError("media_url deve ser uma URL publica")

        data: dict[str, str] = {
            "is_carousel_item": "true",
        }
        if media_type == "REELS":
            data.update({
                "media_type": "REELS",
                "video_url": media_url,
            })
        else:
            data.update({
                "media_type": "IMAGE",
                "image_url": media_url,
            })

        body = self._post(
            f"{self.settings.ig_user_id}/media",
            data,
        )
        return str(body["id"])

    def create_carousel(
        self,
        item_urls: list[str],
        caption: str,
    ) -> str:
        if not 2 <= len(item_urls) <= 10:
            raise ValueError("Um carrossel deve ter entre 2 e 10 itens")

        item_ids: list[str] = []
        for item_url in item_urls:
            item_ids.append(self.create_carousel_item(item_url))
            self.wait_for_container(item_ids[-1])

        body = self._post(
            f"{self.settings.ig_user_id}/media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": caption,
            },
        )
        return str(body["id"])

    def publish_carousel(
        self,
        item_urls: list[str],
        caption: str,
    ) -> str:
        container_id = self.create_carousel(item_urls, caption)
        self.wait_for_container(container_id, timeout_seconds=600)
        return self.publish_container(container_id)

    def create_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: str | None = None,
    ) -> str:
        if not video_url.startswith(("http://", "https://")):
            raise ValueError("video_url deve ser uma URL publica")

        data: dict[str, str] = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
        }
        if cover_url is not None:
            data["cover_url"] = cover_url

        body = self._post(
            f"{self.settings.ig_user_id}/media",
            data,
        )
        return str(body["id"])

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: str | None = None,
    ) -> str:
        container_id = self.create_reel(video_url, caption, cover_url)
        self.wait_for_container(container_id, timeout_seconds=900)
        return self.publish_container(container_id)

    def get_container_status(self, container_id: str) -> dict[str, str]:
        try:
            response = self.session.get(
                f"{self.base_url}/{container_id}",
                params={
                    "access_token": self.settings.access_token,
                    "fields": "status,status_code",
                },
                timeout=(10, 60),
            )
            body = response.json()
        except requests.RequestException as exc:
            raise RuntimeError("Falha de rede consultando o contêiner") from exc
        except requests.exceptions.JSONDecodeError as exc:
            raise RuntimeError("Resposta JSON invalida da Graph API") from exc

        if not response.ok:
            error = body.get("error", {})
            raise MetaApiError(
                message=error.get("message", "Erro desconhecido"),
                code=int(error.get("code", response.status_code)),
                error_subcode=error.get("error_subcode"),
                http_status=response.status_code,
                is_transient=bool(error.get("is_transient", False)),
                response=body,
            )

        return {
            "status": str(body.get("status", "")),
            "status_code": str(body.get("status_code", "")),
        }

    def wait_for_container(
        self,
        container_id: str,
        timeout_seconds: int = 300,
        interval_seconds: float = 5,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        deadline = monotonic() + timeout_seconds

        while monotonic() < deadline:
            result = self.get_container_status(container_id)
            status = result["status"]
            status_code = result["status_code"]

            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ContainerProcessingError(
                    f"Erro no contêiner {container_id}: {status_code}"
                )
            if status == "EXPIRED":
                raise ContainerProcessingError(
                    f"Contêiner expirado: {container_id}"
                )
            if status not in {"IN_PROGRESS", ""}:
                raise ContainerProcessingError(
                    f"Estado inesperado '{status}' no contêiner {container_id}"
                )

            sleep(interval_seconds)

        raise ContainerTimeoutError(
            f"Timeout aguardando o contêiner {container_id}"
        )

    def publish_container(self, container_id: str) -> str:
        body = self._post(
            f"{self.settings.ig_user_id}/media_publish",
            {"creation_id": container_id},
        )
        return str(body["id"])

    def publish_image(self, image_url: str, caption: str) -> str:
        container_id = self.create_image_container(image_url, caption)
        self.wait_for_container(container_id)
        return self.publish_container(container_id)

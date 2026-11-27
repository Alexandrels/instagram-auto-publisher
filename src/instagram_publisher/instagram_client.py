from collections.abc import Callable
from typing import Any
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
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.base_url = (
            f"https://graph.facebook.com/{settings.graph_api_version}"
        )

    def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        payload = {**data, "access_token": self.settings.access_token}
        try:
            response = self.session.post(
                f"{self.base_url}/{path}",
                data=payload,
                timeout=(10, 60),
            )
        except requests.RequestException as exc:
            raise RuntimeError("Falha de rede ao chamar a Graph API") from exc

        try:
            body = response.json()
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

        return body

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

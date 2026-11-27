from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MetaApiError(RuntimeError):
    message: str
    code: int
    error_subcode: int | None = None
    http_status: int | None = None
    is_transient: bool = False
    response: dict[str, Any] | None = None

    def __str__(self) -> str:
        subcode = f", subcode={self.error_subcode}" if self.error_subcode else ""
        return f"Meta API error {self.code}{subcode}: {self.message}"


class ContainerProcessingError(RuntimeError):
    """Raised when a media container cannot be published."""


class ContainerTimeoutError(RuntimeError):
    """Raised when a media container does not finish before the deadline."""

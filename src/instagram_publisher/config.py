import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    ig_user_id: str
    access_token: str
    graph_api_version: str

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        ig_user_id = os.getenv("IG_USER_ID", "").strip()
        access_token = os.getenv("IG_ACCESS_TOKEN", "").strip()
        graph_api_version = os.getenv(
            "GRAPH_API_VERSION",
            "v26.0",
        ).strip()

        if not ig_user_id:
            raise ConfigurationError("IG_USER_ID nao foi configurado")
        if not ig_user_id.isdigit():
            raise ConfigurationError("IG_USER_ID deve conter apenas numeros")
        if not access_token:
            raise ConfigurationError("IG_ACCESS_TOKEN nao foi configurado")
        if not graph_api_version.startswith("v"):
            raise ConfigurationError(
                "GRAPH_API_VERSION deve comecar com 'v', por exemplo 'v26.0'"
            )

        return cls(
            ig_user_id=ig_user_id,
            access_token=access_token,
            graph_api_version=graph_api_version,
        )

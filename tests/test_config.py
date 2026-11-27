import pytest

from instagram_publisher.config import ConfigurationError, Settings


def configure_valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IG_USER_ID", "17841400000000000")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("GRAPH_API_VERSION", "v26.0")


def test_loads_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_valid_environment(monkeypatch)

    settings = Settings.load()

    assert settings.ig_user_id == "17841400000000000"
    assert settings.access_token == "test-token"
    assert settings.graph_api_version == "v26.0"


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("IG_USER_ID", "", "IG_USER_ID nao foi configurado"),
        ("IG_USER_ID", "abc", "IG_USER_ID deve conter apenas numeros"),
        ("IG_ACCESS_TOKEN", "", "IG_ACCESS_TOKEN nao foi configurado"),
        (
            "GRAPH_API_VERSION",
            "26.0",
            "GRAPH_API_VERSION deve comecar",
        ),
    ],
)
def test_rejects_invalid_settings(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
    message: str,
) -> None:
    configure_valid_environment(monkeypatch)
    monkeypatch.setenv(variable, value)

    with pytest.raises(ConfigurationError, match=message):
        Settings.load()

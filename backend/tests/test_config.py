from pathlib import Path

import pytest
from pydantic import SecretStr

from app.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def test_loads_without_any_keys() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None
    assert settings.elevenlabs_api_key is None
    assert settings.guardian_api_key is None
    assert settings.openai_write_model == "gpt-6-sol"


def test_missing_env_file_is_ignored(tmp_path: Path) -> None:
    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.openai_api_key is None


def test_empty_values_count_as_missing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=\nELEVENLABS_API_KEY=\n")

    settings = Settings(_env_file=env_file)

    assert settings.openai_api_key is None
    assert settings.elevenlabs_api_key is None


def test_keys_are_masked_when_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-test-not-a-real-key"
    assert "sk-test-not-a-real-key" not in repr(settings)


def test_env_example_matches_settings() -> None:
    documented = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            name, _, value = line.partition("=")
            documented[name.strip()] = value.strip()

    fields = {name.upper(): field for name, field in Settings.model_fields.items()}

    assert documented.keys() == fields.keys()
    for name, value in documented.items():
        if value:
            default = fields[name].default
            if isinstance(default, SecretStr):
                default = default.get_secret_value()
            assert value == default, name

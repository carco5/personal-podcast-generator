from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-level .env. In Docker it does not exist: Compose injects the variables, and
# pydantic-settings ignores a missing env file.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Runtime configuration from environment variables and the optional repo-level .env."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_ignore_empty=True, extra="ignore")

    # Keys are optional: without them the app still runs but cannot generate episodes.
    openai_api_key: SecretStr | None = None
    elevenlabs_api_key: SecretStr | None = None
    guardian_api_key: SecretStr | None = None

    # OpenAI model per pipeline stage.
    openai_write_model: str = "gpt-6-sol"
    openai_select_model: str = "gpt-6-luna"
    openai_judge_model: str = "gpt-6-luna"

    # Audio files (episodes and the voice cache), outside git.
    data_dir: Path = ENV_FILE.parent / "data"

    # ElevenLabs default voices: George (host) and Sarah (analyst).
    elevenlabs_host_voice_id: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_analyst_voice_id: str = "EXAVITQu4vr4xnSDxMaL"

    # Development default (compose.dev.yaml); Compose overrides it inside the containers.
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://podcast:podcast@127.0.0.1:5433/podcast"
    )


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process."""
    return Settings()

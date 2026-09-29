from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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

    # Worker: the free tone voice unless real voice is enabled, a daily spending cap, and how often
    # it polls the queue.
    worker_voice: Literal["tone", "elevenlabs"] = "tone"
    worker_daily_budget_usd: Decimal = Field(default=Decimal("1.00"), ge=0)
    worker_poll_seconds: float = Field(default=10, gt=0)

    # Development default (compose.dev.yaml); Compose overrides it inside the containers.
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://podcast:podcast@127.0.0.1:5433/podcast"
    )

    def missing_generation_keys(self) -> list[str]:
        """Names of the environment variables that episode generation needs and are not set."""
        keys = {"OPENAI_API_KEY": self.openai_api_key}
        if self.worker_voice == "elevenlabs":
            keys["ELEVENLABS_API_KEY"] = self.elevenlabs_api_key
        return [name for name, key in keys.items() if key is None]


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once per process."""
    return Settings()

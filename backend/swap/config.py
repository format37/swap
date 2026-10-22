"""Configuration, read from the environment (compose passes `.env` through)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Each field comes from the environment variable of the same name, upper-cased.

    A blank variable counts as unset, so `.env.example` can list every name.
    """

    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    database_url: str
    telegram_bot_token: SecretStr
    # The VPS's own Bot API server (ADR-0008). No default, deliberately: unset means
    # nothing talks to Telegram, so a laptop or CI can never log the bot back in to
    # the cloud API and starve the relay.
    telegram_api_base: str | None = None
    webapp_url: str = "https://swap.latentstate.dev"
    # The bot's links (invites and deep links) are t.me/<this>.
    telegram_bot_username: str = "peertopeerswapbot"
    init_data_max_age_s: int = 3600
    session_ttl_s: int = 24 * 3600
    invite_ttl_s: int = 72 * 3600
    # What orders may give and want (FR-2.2): ISO 4217 codes and two stablecoins
    # (ADR-0010). More are a config change, as JSON: ASSETS='["RUB","GEL",…]'.
    assets: list[str] = ["RUB", "GEL", "USD", "EUR", "TRY", "KZT", "AMD", "USDT", "USDC"]
    # The built frontend; the api serves it when this is set (ADR-0001).
    static_dir: str | None = None
    log_format: Literal["json", "console"] = "json"
    log_level: str = "INFO"

    def secrets(self) -> tuple[str, ...]:
        """What the log redactor must never print: the token and its secret half."""
        token = self.telegram_bot_token.get_secret_value()
        return (token, token.partition(":")[2])


@lru_cache
def get_settings() -> Settings:
    return Settings()

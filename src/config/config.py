from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== Application ====================
    app_name: str = Field(default="FX Payment Processor", env="APP_NAME")
    version: str = Field(default="0.1.0", env="VERSION")

    # ==================== Database ====================
    database_url: str = Field(..., env="DATABASE_URL")

    # ==================== FX Rates ====================
    # Initial/default FX rates
    fx_rate_usd_to_mxn: float = Field(default=18.70, env="FX_RATE_USD_TO_MXN")
    fx_rate_mxn_to_usd: float = Field(default=0.053, env="FX_RATE_MXN_TO_USD")

    # Dynamic FX Rates Configuration
    fx_rate_mode: Literal["static", "random", "api"] = Field(
        default="static", env="FX_RATE_MODE"
    )
    fx_rate_update_interval: int = Field(
        default=300, env="FX_RATE_UPDATE_INTERVAL"
    )  # seconds (5 minutes default)

    # Random mode: list of possible values for USD to MXN
    fx_rate_random_values: str = Field(
        default="18.50,18.60,18.70,18.80,18.90,19.00", env="FX_RATE_RANDOM_VALUES"
    )

    # API mode: exchangerate-api configuration
    exchangerate_api_key: str = Field(env="EXCHANGERATE_API_KEY")
    exchangerate_api_url: str = Field(env="EXCHANGERATE_API_URL")
    exchangerate_api_timeout: int = Field(
        default=10, env="EXCHANGERATE_API_TIMEOUT"
    )  # seconds

    # ==================== Business Logic ====================
    # Wallet settings
    max_balance_per_currency: float = Field(
        default=1_000_000.00, env="MAX_BALANCE_PER_CURRENCY"
    )  # Maximum balance allowed
    min_transaction_amount: float = Field(
        default=0.01, env="MIN_TRANSACTION_AMOUNT"
    )  # Minimum transaction amount

    def get_random_fx_values(self) -> list[float]:
        return [float(val.strip()) for val in self.fx_rate_random_values.split(",")]

    def get_allowed_origins_list(self) -> list[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()

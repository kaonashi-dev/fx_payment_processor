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
    app_name: str = "FX Payment Processor"
    version: str = "0.1.0"

    # ==================== Database ====================
    database_url: str = "postgresql://postgres:postgres@localhost:5432/fx_payment_processor"

    # Connection pool settings
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600

    # Rate Limiting
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # ==================== FX Rates ====================
    # Initial/default FX rates
    fx_rate_usd_to_mxn: float = 18.70
    fx_rate_mxn_to_usd: float = 0.053

    # Dynamic FX Rates Configuration
    fx_rate_mode: Literal["static", "random", "api"] = "static"
    fx_rate_update_interval: int = 300  # seconds (5 minutes default)

    # Random mode: list of possible values for USD to MXN
    fx_rate_random_values: str = "18.50,18.60,18.70,18.80,18.90,19.00"

    # API mode: exchangerate-api configuration
    exchangerate_api_key: str = ""
    exchangerate_api_url: str = "https://api.exchangerate-api.com/v4/latest/USD"
    exchangerate_api_timeout: int = 10  # seconds

    # ==================== Business Logic ====================
    # Wallet settings
    max_balance_per_currency: float = 1_000_000.00  # Maximum balance allowed
    min_transaction_amount: float = 0.01  # Minimum transaction amount

    # Health check
    health_check_enabled: bool = True

    def get_random_fx_values(self) -> list[float]:
        return [float(val.strip()) for val in self.fx_rate_random_values.split(",")]

    def get_allowed_origins_list(self) -> list[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

settings = Settings()


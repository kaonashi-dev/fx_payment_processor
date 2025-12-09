import random
import logging
from decimal import Decimal
from typing import Optional
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.config.config import settings

logger = logging.getLogger(__name__)


class FXRateService:
    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self._usd_to_mxn: float = settings.fx_rate_usd_to_mxn
        self._mxn_to_usd: float = settings.fx_rate_mxn_to_usd
        self._random_values: list[float] = []

        if settings.fx_rate_mode == "random":
            try:
                self._random_values = settings.get_random_fx_values()
                if not self._random_values:
                    raise ValueError("No random values provided")
                logger.info(
                    f"Random FX mode initialized with {len(self._random_values)} values"
                )
            except Exception as e:
                logger.error(f"Error parsing random FX values: {e}")
                logger.info("Falling back to static mode")
                settings.fx_rate_mode = "static"

    def start_scheduler(self):
        if settings.fx_rate_mode == "static":
            logger.info("FX rates mode is static, scheduler not started")
            return

        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler is already running")
            return

        self.scheduler = BackgroundScheduler()

        trigger = IntervalTrigger(seconds=settings.fx_rate_update_interval)
        self.scheduler.add_job(
            self.update_rates,
            trigger=trigger,
            id="update_fx_rates",
            name="Update FX Rates",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            f"FX rate scheduler started in '{settings.fx_rate_mode}' mode, "
            f"updating every {settings.fx_rate_update_interval} seconds"
        )

        self.update_rates()

    def stop_scheduler(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("FX rate scheduler stopped")

    def update_rates(self):
        try:
            if settings.fx_rate_mode == "random":
                self._update_random_rates()
            elif settings.fx_rate_mode == "api":
                self._update_api_rates()
            else:
                logger.debug("FX rates mode is static, no update needed")
        except Exception as e:
            logger.error(f"Error updating FX rates: {e}", exc_info=True)

    def _update_random_rates(self):
        if not self._random_values:
            logger.warning("No random values available, keeping current rates")
            return

        new_rate = random.choice(self._random_values)
        old_rate = self._usd_to_mxn

        self._usd_to_mxn = new_rate
        self._mxn_to_usd = round(1 / new_rate, 4)

        logger.info(
            f"FX rates updated (random mode): "
            f"USD->MXN: {old_rate} -> {self._usd_to_mxn}, "
            f"MXN->USD: {self._mxn_to_usd}"
        )

    def _update_api_rates(self):
        try:
            url = settings.exchangerate_api_url
            params = {}

            if settings.exchangerate_api_key:
                params["access_key"] = settings.exchangerate_api_key

            response = requests.get(
                url, params=params, timeout=settings.exchangerate_api_timeout
            )
            response.raise_for_status()
            data = response.json()

            if "rates" in data and "MXN" in data["rates"]:
                new_rate = float(data["rates"]["MXN"])
                old_rate = self._usd_to_mxn

                self._usd_to_mxn = new_rate
                self._mxn_to_usd = round(1 / new_rate, 4)

                logger.info(
                    f"FX rates updated (API mode): "
                    f"USD->MXN: {old_rate} -> {self._usd_to_mxn}, "
                    f"MXN->USD: {self._mxn_to_usd}"
                )
            else:
                logger.warning("MXN rate not found in API response")
        except requests.RequestException as e:
            logger.error(f"Error fetching rates from API: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing API response: {e}")

    @property
    def usd_to_mxn(self) -> Decimal:
        return Decimal(str(self._usd_to_mxn))

    @property
    def mxn_to_usd(self) -> Decimal:
        return Decimal(str(self._mxn_to_usd))

    def get_rates(self) -> dict[str, float]:
        return {
            "usd_to_mxn": float(self._usd_to_mxn),
            "mxn_to_usd": float(self._mxn_to_usd),
            "mode": settings.fx_rate_mode,
        }


fx_rate_service = FXRateService()

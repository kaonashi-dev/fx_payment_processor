from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.routes import wallet_router
from src.config.logging_config import setup_logging, get_logger
from src.services.fx_rates import fx_rate_service
from src.config.config import settings

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="0.1.0")

    logger.info("starting_fx_rate_scheduler", mode=settings.fx_rate_mode)
    fx_rate_service.start_scheduler()
    logger.info("fx_rate_scheduler_started")

    yield

    logger.info("application_shutdown")
    fx_rate_service.stop_scheduler()
    logger.info("fx_rate_scheduler_stopped")


app = FastAPI(
    title="FX Payment Processor",
    description="Multi-currency wallet system API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(wallet_router)

@app.get("/fx-rates", tags=["Demo"])
async def get_fx_rates():
    return fx_rate_service.get_rates()
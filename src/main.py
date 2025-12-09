from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.routes import wallet_router
from src.config.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", version="0.1.0")

    yield

    logger.info("application_shutdown")


app = FastAPI(
    title="FX Payment Processor",
    description="Multi-currency wallet system API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(wallet_router)

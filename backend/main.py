from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager
import uvicorn
from controllers import (
    document_upload_controller,
    upload_controller,
    website_capture_controller,
    websocket_controller,
    ai_controller,
    auth_controller,
    directory_controller,
)
from background.subscribers.redis_subscriber import RedisSubscriber
from config.redis import redis_pool, RedisType
from config.mongo import mongo_manager
from services.websocket_manager import get_websocket_manager
import asyncio

# From huey's documentation, this is recommended, even though it's not directly used in this file
# https://huey.readthedocs.io/en/latest/imports.html#suggested-organization-of-code
# from huey import huey  # type: ignore
from background.huey_jobs.capture_website_job import huey, capture_website  # type: ignore
from background.huey_jobs.process_document_job import process_document  # type: ignore
from background.huey_jobs.summarize_document_job import summarize_document  # type: ignore
from background.huey_jobs.process_document_v2_job import process_document_with_docling  # type: ignore

from config.logger import setup_logging
from db.indices.ensure_indices import ensure_indices_with_manager

# Determine environment
ENV = os.getenv("ENV", "development")
APP_BASE_URL = os.getenv(
    "APP_BASE_URL", "localhost:5173"
)  # This is the URL of the frontend app

LOG_LEVEL = os.getenv("LOG_LEVEL")
if ENV == "production":
    effective_log_level = LOG_LEVEL or "INFO"
    logger = setup_logging(
        log_level=effective_log_level, log_to_file=True, log_file="app.log"
    )
else:
    effective_log_level = LOG_LEVEL or "DEBUG"
    logger = setup_logging(log_level=effective_log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.redis_pool = redis_pool
    redis_client: RedisType = await app.state.redis_pool.get_client()
    websocket_manager = get_websocket_manager()
    app.state.websocket_manager = websocket_manager
    await FastAPILimiter.init(redis_client)

    await mongo_manager.connect()
    redis_subscriber = RedisSubscriber(redis_client, websocket_manager)
    app.state.redis_subscriber = redis_subscriber
    redis_subscriber.task = asyncio.create_task(redis_subscriber.start())
    asyncio.create_task(ensure_indices_with_manager())

    logger.info("Application startup complete")

    yield
    logger.info("Application shutdown initiated")

    await app.state.redis_pool.close()
    await app.state.websocket_manager.shutdown()
    await redis_subscriber.stop()
    await FastAPILimiter.close()

    await mongo_manager.close()
    logger.info("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router, prefix="/auth", tags=["authentication"])
app.include_router(websocket_controller.router, tags=["websocket"])
app.include_router(website_capture_controller.router, tags=["website_capture"])
app.include_router(upload_controller.router, tags=["upload"])
app.include_router(document_upload_controller.router, tags=["document_upload"])
app.include_router(ai_controller.router, tags=["AI"])
app.include_router(directory_controller.router, tags=["directory"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

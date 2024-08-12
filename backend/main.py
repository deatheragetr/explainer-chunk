from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from controllers import (
    document_upload_controller,
    upload_controller,
    website_capture_controller,
    websocket_controller
)
from services.websocket_manager import WebSocketManager
from background.subscribers.redis_subscriber import redis_subscriber
from config.redis import redis_pool
from config.mongo import mongo_manager
from services.websocket_manager import get_websocket_manager
import asyncio

# From huey's documentation, this is recommended, even though it's not directly used in this file
# https://huey.readthedocs.io/en/latest/imports.html#suggested-organization-of-code
# from huey import huey  # type: ignore
from background.huey_jobs.capture_website_job import huey, capture_website  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_pool = redis_pool
    app.state.websocket_manager = get_websocket_manager()
    await mongo_manager.connect()
    asyncio.create_task(redis_subscriber(app))
    yield
    await app.state.redis_pool.close()
    await app.state.websocket_manager.shutdown()
    await mongo_manager.close()



app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update this with your Vue.js app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_controller.router)
app.include_router(website_capture_controller.router)
app.include_router(upload_controller.router)
app.include_router(document_upload_controller.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

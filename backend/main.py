from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from controllers import (
    document_upload_controller,
    upload_controller,
    website_capture_controller,
)
from background import websockets
from background.websockets import redis_subscriber
from config.redis import redis_client
import asyncio

# From huey's documentation, this is recommended, even though it's not directly used in this file
# https://huey.readthedocs.io/en/latest/imports.html#suggested-organization-of-code
from config.huey import huey  # type: ignore
from background.jobs.capture_website_job import capture_website  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(redis_subscriber())
    yield
    await redis_client.close()


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update this with your Vue.js app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(websockets.router)
app.include_router(website_capture_controller.router)
app.include_router(upload_controller.router)
app.include_router(document_upload_controller.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

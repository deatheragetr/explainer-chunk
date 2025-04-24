# config.py
import os
from huey import RedisHuey

huey = RedisHuey(
    "explainer-chunk",
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", 6379),
    db=os.getenv("REDIS_DB", 0),
)
# Optional configurations
huey.immediate = False  # Set to True for development/debug to run tasks immediately
huey.always_eager = False  # Set to True for testing to run tasks synchronously

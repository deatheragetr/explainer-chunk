# config.py
from huey import RedisHuey

huey = RedisHuey("explainer-chunk", host="localhost", port=6379, db=0)
# Optional configurations
huey.immediate = False  # Set to True for development/debug to run tasks immediately
huey.always_eager = False  # Set to True for testing to run tasks synchronously

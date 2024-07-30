from redis.asyncio import Redis as RedisAsync
from redis import Redis as RedisSync
from typing import cast

# Get a runtime error on start up:
# raise TypeError(f"{cls} is not a generic class")
# TypeError: <class 'redis.asyncio.client.Redis'> is not a generic class
# If I don't use case and directly set redis_client to Redis[bytes]
redis_client = cast("Redis[bytes]", RedisAsync(host="localhost", port=6379, db=0))
redis_client_sync = cast("Redis[bytes]", RedisSync(host="localhost", port=6379, db=0))

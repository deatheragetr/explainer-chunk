from redis.asyncio import Redis
from typing import TYPE_CHECKING

# Get a runtime error on start up:
# raise TypeError(f"{cls} is not a generic class")
# TypeError: <class 'redis.asyncio.client.Redis'> is not a generic class
# If I don't use case and directly set redis_client to Redis[bytes]
host = "localhost"
port = 6379
db = 0

# Redis Types are a little screwy: https://github.com/python/typeshed/issues/8242
# Maybe fixed in the future :shrug:
if TYPE_CHECKING:
    RedisType = Redis[bytes]
else:
    RedisType = Redis

redis_client = Redis(host=host, port=port, db=db)




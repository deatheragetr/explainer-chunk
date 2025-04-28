import os
from redis.asyncio import Redis, ConnectionPool
from typing import TYPE_CHECKING
from config.logger import get_logger

logger = get_logger()

host = os.getenv("REDIS_HOST", "localhost")
port = int(os.getenv("REDIS_PORT", 6379))
db = int(os.getenv("REDIS_DB", 0))


# Redis Types are a little screwy: https://github.com/python/typeshed/issues/8242
# Maybe fixed in the future :shrug:
if TYPE_CHECKING:
    RedisType = Redis[bytes]
else:
    RedisType = Redis


class RedisPool:
    def __init__(self):
        self.pool = ConnectionPool(host=host, port=port, db=db)
        self.client = Redis(connection_pool=self.pool)

    async def get_client(self) -> RedisType:
        return self.client

    async def close(self):
        await self.client.close()
        await self.pool.disconnect()
        logger.info("Closed Redis connection")


redis_pool = RedisPool()

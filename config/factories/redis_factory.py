import asyncio

import redis.asyncio as aioredis
from redis.asyncio import ConnectionError

from config import main_config
from config.logger import get_logger

logger = get_logger(__name__)


async def get_redis_conn_async() -> aioredis.Redis:
    while True:
        try:
            return await aioredis.from_url(main_config.REDIS_URL, decode_responses=True)
        except ConnectionError:
            logger.warning("Redis connection error. Retrying in 5 seconds...")
            await asyncio.sleep(5)
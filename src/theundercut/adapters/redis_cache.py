"""
Central Redis client—import this anywhere you need Redis.
"""

import redis

from theundercut.config import get_settings

settings = get_settings()
# decode_responses=True → returns str instead of bytes
redis_client: redis.Redis = redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

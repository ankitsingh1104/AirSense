import json
import logging
import os
from typing import Optional, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class Cache:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._memory_cache = {}

    async def connect(self):
        """Initializes the Redis connection."""
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis at %s", REDIS_URL)
        except Exception as e:
            logger.warning("Redis connection failed. Using in-memory fallback: %s", str(e))
            self.redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Gets a value from cache."""
        if self.redis:
            try:
                val = await self.redis.get(key)
                return json.loads(val) if val else None
            except Exception as e:
                logger.error("Redis get failed for %s: %s", key, str(e))
        return self._memory_cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 900):
        """Sets a value in cache with TTL (default 15 min)."""
        if self.redis:
            try:
                await self.redis.set(key, json.dumps(value, default=str), ex=ttl)
                return
            except Exception as e:
                logger.error("Redis set failed for %s: %s", key, str(e))
        
        self._memory_cache[key] = value

    async def delete(self, key: str):
        """Deletes a single cache key."""
        if self.redis:
            try:
                await self.redis.delete(key)
                return
            except Exception as e:
                logger.error("Redis delete failed for %s: %s", key, str(e))
        self._memory_cache.pop(key, None)

    async def delete_pattern(self, pattern: str):
        """Deletes all keys matching a glob pattern."""
        if self.redis:
            try:
                keys = []
                async for key in self.redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self.redis.delete(*keys)
                return len(keys)
            except Exception as e:
                logger.error("Redis delete_pattern failed for %s: %s", pattern, str(e))

        to_delete = [k for k in self._memory_cache if _match_pattern(k, pattern)]
        for key in to_delete:
            self._memory_cache.pop(key, None)
        return len(to_delete)

    async def disconnect(self):
        """Closes the connection."""
        if self.redis:
            await self.redis.close()

# Global cache instance
cache = Cache()


def _match_pattern(value: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return value == pattern

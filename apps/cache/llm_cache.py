"""LLM response caching using Redis."""

import logging
import hashlib
import json
from typing import Optional, Any

from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


class LLMCache:
    """LLM response cache using Redis."""

    def __init__(self, redis_manager: RedisManager, ttl: int = 3600):
        """
        Initialize LLM cache.

        Args:
            redis_manager: Redis manager instance
            ttl: Cache TTL in seconds (default 1 hour)
        """
        self.redis = redis_manager
        self.ttl = ttl
        self.prefix = "llm:cache:"
        self.stats_prefix = "llm:stats:"

    def _make_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generate cache key from prompt and parameters.

        Args:
            prompt: LLM prompt
            model: Model name
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Cache key
        """
        # Create deterministic hash from prompt and parameters
        cache_input = {
            "prompt": prompt,
            "model": model,
            **kwargs,
        }

        # Sort keys for consistent hashing
        cache_str = json.dumps(cache_input, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        return f"{self.prefix}{cache_hash}"

    async def get(
        self, prompt: str, model: str, **kwargs
    ) -> Optional[dict[str, Any]]:
        """
        Get cached LLM response.

        Args:
            prompt: LLM prompt
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Cached response or None
        """
        key = self._make_cache_key(prompt, model, **kwargs)
        cached = await self.redis.get_json(key)

        if cached:
            logger.debug(f"LLM cache HIT for key: {key[:32]}...")
            await self._increment_stat("hits")
            return cached

        logger.debug(f"LLM cache MISS for key: {key[:32]}...")
        await self._increment_stat("misses")
        return None

    async def set(
        self,
        prompt: str,
        model: str,
        response: dict[str, Any],
        ttl: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt: LLM prompt
            model: Model name
            response: LLM response to cache
            ttl: Optional custom TTL
            **kwargs: Additional parameters

        Returns:
            True if cached successfully
        """
        key = self._make_cache_key(prompt, model, **kwargs)
        cache_ttl = ttl if ttl is not None else self.ttl

        success = await self.redis.set_json(key, response, expire=cache_ttl)

        if success:
            logger.debug(f"Cached LLM response for key: {key[:32]}...")
            await self._increment_stat("writes")

        return success

    async def invalidate(self, prompt: str, model: str, **kwargs) -> bool:
        """
        Invalidate cached response.

        Args:
            prompt: LLM prompt
            model: Model name
            **kwargs: Additional parameters

        Returns:
            True if invalidated
        """
        key = self._make_cache_key(prompt, model, **kwargs)
        deleted = await self.redis.delete(key)

        if deleted:
            logger.debug(f"Invalidated cache for key: {key[:32]}...")
            await self._increment_stat("invalidations")

        return deleted > 0

    async def clear_all(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of keys deleted
        """
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.prefix}*", count=100
            )

            for key in keys:
                await self.redis.delete(key)
                deleted += 1

            if cursor == 0:
                break

        logger.info(f"Cleared {deleted} cached LLM responses")
        await self._increment_stat("clears")
        return deleted

    async def get_cache_size(self) -> int:
        """
        Get number of cached responses.

        Returns:
            Cache size
        """
        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.prefix}*", count=100
            )
            count += len(keys)

            if cursor == 0:
                break

        return count

    async def _increment_stat(self, stat_name: str) -> int:
        """
        Increment cache statistic.

        Args:
            stat_name: Statistic name (hits, misses, writes, etc.)

        Returns:
            New count
        """
        key = f"{self.stats_prefix}{stat_name}"
        return await self.redis.incr(key)

    async def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Cache statistics
        """
        stats = {}
        stat_names = ["hits", "misses", "writes", "invalidations", "clears"]

        for stat_name in stat_names:
            key = f"{self.stats_prefix}{stat_name}"
            value = await self.redis.get(key)
            stats[stat_name] = int(value) if value else 0

        # Calculate hit rate
        total_requests = stats["hits"] + stats["misses"]
        stats["hit_rate"] = (
            stats["hits"] / total_requests if total_requests > 0 else 0.0
        )
        stats["cache_size"] = await self.get_cache_size()

        return stats

    async def reset_stats(self):
        """Reset cache statistics."""
        stat_names = ["hits", "misses", "writes", "invalidations", "clears"]
        for stat_name in stat_names:
            key = f"{self.stats_prefix}{stat_name}"
            await self.redis.delete(key)

        logger.info("Reset LLM cache statistics")

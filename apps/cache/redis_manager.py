"""Redis connection and management."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any, Dict, Optional, Tuple, List, Set
from urllib.parse import urlparse

from redis.asyncio import ConnectionPool, Redis

logger = logging.getLogger(__name__)


@dataclass
class _SortedMember:
    member: str
    score: float


class _InMemoryRedis:
    """Minimal async in-memory Redis replacement for local development."""

    def __init__(self) -> None:
        self._strings: Dict[str, str] = {}
        self._hashes: Dict[str, Dict[str, str]] = {}
        self._lists: Dict[str, List[str]] = {}
        self._sets: Dict[str, Set[str]] = {}
        self._zsets: Dict[str, Dict[str, float]] = {}
        self._expirations: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        # No resources to free
        return None

    async def close(self) -> None:
        return None

    def _is_expired(self, key: str) -> bool:
        exp = self._expirations.get(key)
        if exp is None:
            return False
        if exp < time.time():
            self._delete_without_lock(key)
            return True
        return False

    def _delete_without_lock(self, key: str) -> None:
        self._strings.pop(key, None)
        self._hashes.pop(key, None)
        self._lists.pop(key, None)
        self._sets.pop(key, None)
        self._zsets.pop(key, None)
        self._expirations.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if self._is_expired(key):
                return None
            return self._strings.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        async with self._lock:
            self._strings[key] = value
            if ex is not None:
                self._expirations[key] = time.time() + ex
            else:
                self._expirations.pop(key, None)
            return True

    async def delete(self, key: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                return 0
            existed = int(key in self._strings or key in self._hashes or key in self._lists or key in self._sets or key in self._zsets)
            self._delete_without_lock(key)
            return existed

    async def exists(self, key: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                return 0
            return int(key in self._strings or key in self._hashes or key in self._lists or key in self._sets or key in self._zsets)

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if await self.exists(key) == 0:
                return False
            self._expirations[key] = time.time() + seconds
            return True

    async def ttl(self, key: str) -> int:
        async with self._lock:
            if await self.exists(key) == 0:
                return -2
            exp = self._expirations.get(key)
            if exp is None:
                return -1
            ttl = int(exp - time.time())
            return ttl if ttl >= 0 else -2

    async def hset(self, name: str, key: str, value: str) -> int:
        async with self._lock:
            if self._is_expired(name):
                self._hashes.pop(name, None)
            mapping = self._hashes.setdefault(name, {})
            is_new = int(key not in mapping)
            mapping[key] = value
            return is_new

    async def hget(self, name: str, key: str) -> Optional[str]:
        async with self._lock:
            if self._is_expired(name):
                return None
            return self._hashes.get(name, {}).get(key)

    async def hgetall(self, name: str) -> Dict[str, str]:
        async with self._lock:
            if self._is_expired(name):
                return {}
            return dict(self._hashes.get(name, {}))

    async def hdel(self, name: str, *keys: str) -> int:
        async with self._lock:
            if self._is_expired(name):
                return 0
            mapping = self._hashes.get(name, {})
            count = 0
            for key in keys:
                if key in mapping:
                    del mapping[key]
                    count += 1
            if not mapping:
                self._hashes.pop(name, None)
            return count

    async def hexists(self, name: str, key: str) -> bool:
        async with self._lock:
            if self._is_expired(name):
                return False
            return key in self._hashes.get(name, {})

    async def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        return await self.set(key, json.dumps(value), ex=expire)

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON for key %s", key)
            return None

    async def lpush(self, key: str, *values: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._lists.pop(key, None)
            lst = self._lists.setdefault(key, [])
            for value in values:
                lst.insert(0, value)
            return len(lst)

    async def rpush(self, key: str, *values: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._lists.pop(key, None)
            lst = self._lists.setdefault(key, [])
            lst.extend(values)
            return len(lst)

    async def lpop(self, key: str) -> Optional[str]:
        async with self._lock:
            if self._is_expired(key):
                return None
            lst = self._lists.get(key)
            if not lst:
                return None
            value = lst.pop(0)
            if not lst:
                self._lists.pop(key, None)
            return value

    async def rpop(self, key: str) -> Optional[str]:
        async with self._lock:
            if self._is_expired(key):
                return None
            lst = self._lists.get(key)
            if not lst:
                return None
            value = lst.pop()
            if not lst:
                self._lists.pop(key, None)
            return value

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        async with self._lock:
            if self._is_expired(key):
                return []
            lst = self._lists.get(key, [])
            if end == -1:
                end = len(lst)
            return lst[start:end + 1]

    async def llen(self, key: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                return 0
            return len(self._lists.get(key, []))

    async def sadd(self, key: str, *members: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._sets.pop(key, None)
            st = self._sets.setdefault(key, set())
            before = len(st)
            st.update(members)
            return len(st) - before

    async def srem(self, key: str, *members: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                return 0
            st = self._sets.get(key)
            if not st:
                return 0
            count = 0
            for member in members:
                if member in st:
                    st.remove(member)
                    count += 1
            if not st:
                self._sets.pop(key, None)
            return count

    async def smembers(self, key: str) -> Set[str]:
        async with self._lock:
            if self._is_expired(key):
                return set()
            return set(self._sets.get(key, set()))

    async def sismember(self, key: str, member: str) -> bool:
        async with self._lock:
            if self._is_expired(key):
                return False
            return member in self._sets.get(key, set())

    async def zadd(self, key: str, mapping: Dict[str, float], nx: bool = False) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._zsets.pop(key, None)
            zset = self._zsets.setdefault(key, {})
            added = 0
            for member, score in mapping.items():
                if nx and member in zset:
                    continue
                if member not in zset:
                    added += 1
                zset[member] = float(score)
            return added

    async def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        async with self._lock:
            if self._is_expired(key):
                return []
            zset = self._zsets.get(key, {})
            ordered = sorted([_SortedMember(m, s) for m, s in zset.items()], key=lambda item: (item.score, item.member))
            if end == -1:
                end = len(ordered) - 1
            sliced = ordered[start:end + 1]
            if withscores:
                return [(item.member, item.score) for item in sliced]
            return [item.member for item in sliced]

    async def zrem(self, key: str, *members: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                return 0
            zset = self._zsets.get(key)
            if not zset:
                return 0
            removed = 0
            for member in members:
                if member in zset:
                    del zset[member]
                    removed += 1
            if not zset:
                self._zsets.pop(key, None)
            return removed

    async def zscore(self, key: str, member: str) -> Optional[float]:
        async with self._lock:
            if self._is_expired(key):
                return None
            zset = self._zsets.get(key, {})
            return zset.get(member)

    async def incr(self, key: str, amount: int = 1) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._strings.pop(key, None)
            current = int(self._strings.get(key, '0'))
            current += amount
            self._strings[key] = str(current)
            return current

    async def decr(self, key: str, amount: int = 1) -> int:
        return await self.incr(key, -amount)

    async def keys(self, pattern: str) -> List[str]:
        async with self._lock:
            all_keys = set(self._strings) | set(self._hashes) | set(self._lists) | set(self._sets) | set(self._zsets)
            result = []
            for key in all_keys:
                if self._is_expired(key):
                    continue
                if fnmatch(key, pattern):
                    result.append(key)
            return sorted(result)

    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10) -> Tuple[int, List[str]]:
        keys = await self.keys(match or '*')
        return 0, keys


class RedisManager:
    """Redis connection manager with in-memory fallback."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize Redis connection or fallback to in-memory implementation."""
        try:
            parsed = urlparse(self.redis_url)
            if parsed.scheme == 'memory':
                self.client = _InMemoryRedis()
                logger.info("Using in-memory Redis implementation (memory://)")
                return

            self.pool = ConnectionPool.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                max_connections=10,
            )
            self.client = Redis(connection_pool=self.pool)
            await self.client.ping()
            logger.info("Redis initialized successfully")
        except Exception as exc:
            logger.error(f"Failed to initialize Redis: {exc}")
            raise

    async def close(self) -> None:
        """Close Redis connections."""
        if self.client:
            close = getattr(self.client, 'aclose', None) or getattr(self.client, 'close', None)
            if close:
                await close()
            self.client = None
            logger.info("Redis connection closed")
        if self.pool:
            await self.pool.disconnect()
            self.pool = None

    async def health_check(self) -> bool:
        """Check Redis health."""
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except Exception as exc:
            logger.error(f"Redis health check failed: {exc}")
            return False

    # The remaining methods proxy directly to the underlying client
    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return bool(await self.client.exists(key))

    async def expire(self, key: str, seconds: int) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return bool(await self.client.expire(key, seconds))

    async def ttl(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.ttl(key)

    async def get_json(self, key: str) -> Optional[Any]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        if hasattr(self.client, 'get_json'):
            return await self.client.get_json(key)  # type: ignore[attr-defined]
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to decode JSON for key {key}: {exc}")
            return None

    async def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        if hasattr(self.client, 'set_json'):
            return await self.client.set_json(key, value, expire)  # type: ignore[attr-defined]
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError) as exc:
            logger.error(f"Failed to encode JSON for key {key}: {exc}")
            return False
        return await self.set(key, payload, expire)

    async def hget(self, name: str, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> Dict[str, str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.hdel(name, *keys)

    async def hexists(self, name: str, key: str) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return bool(await self.client.hexists(name, key))

    async def lpush(self, key: str, *values: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.rpush(key, *values)

    async def lpop(self, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.lpop(key)

    async def rpop(self, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.rpop(key)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.lrange(key, start, end)

    async def llen(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.llen(key)

    async def sadd(self, key: str, *members: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.sadd(key, *members)

    async def srem(self, key: str, *members: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.srem(key, *members)

    async def smembers(self, key: str) -> Set[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        result = await self.client.smembers(key)
        return set(result) if not isinstance(result, set) else result

    async def sismember(self, key: str, member: str) -> bool:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return bool(await self.client.sismember(key, member))

    async def zadd(self, key: str, mapping: Dict[str, float], nx: bool = False) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.zadd(key, mapping, nx=nx)

    async def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.zrange(key, start, end, withscores=withscores)

    async def zrem(self, key: str, *members: str) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.zrem(key, *members)

    async def zscore(self, key: str, member: str) -> Optional[float]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.zscore(key, member)

    async def incr(self, key: str, amount: int = 1) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.decr(key, amount)

    async def keys(self, pattern: str) -> List[str]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.keys(pattern)

    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10) -> Tuple[int, List[str]]:
        if not self.client:
            raise RuntimeError("Redis not initialized")
        return await self.client.scan(cursor, match=match, count=count)


redis_manager: Optional[RedisManager] = None


async def get_redis_manager() -> RedisManager:
    if redis_manager is None:
        raise RuntimeError("Redis manager not initialized")
    return redis_manager


async def initialize_redis(redis_url: str) -> RedisManager:
    global redis_manager
    redis_manager = RedisManager(redis_url)
    await redis_manager.initialize()
    return redis_manager

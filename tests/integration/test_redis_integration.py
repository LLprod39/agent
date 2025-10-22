"""Integration tests for Redis components."""

import asyncio
import unittest
from datetime import datetime

from apps.cache import RedisManager, SessionManager, LLMCache, RateLimiter


class RedisManagerTests(unittest.TestCase):
    """Tests for RedisManager."""

    def setUp(self):
        """Set up test environment."""
        self.redis_url = "redis://localhost:6379/15"  # Use DB 15 for tests
        self.redis = RedisManager(self.redis_url)

    def tearDown(self):
        """Clean up after tests."""
        asyncio.run(self._cleanup())

    async def _cleanup(self):
        """Async cleanup."""
        if self.redis.client:
            # Clean test keys
            keys = await self.redis.keys("test:*")
            if keys:
                for key in keys:
                    await self.redis.delete(key)
            await self.redis.close()

    def test_redis_initialization(self):
        """Test Redis initialization."""

        async def run_test():
            await self.redis.initialize()
            self.assertIsNotNone(self.redis.client)
            self.assertIsNotNone(self.redis.pool)

            # Test health check
            healthy = await self.redis.health_check()
            self.assertTrue(healthy)

        asyncio.run(run_test())

    def test_key_value_operations(self):
        """Test basic key-value operations."""

        async def run_test():
            await self.redis.initialize()

            # Set and get
            success = await self.redis.set("test:key1", "value1")
            self.assertTrue(success)

            value = await self.redis.get("test:key1")
            self.assertEqual(value, "value1")

            # Exists
            exists = await self.redis.exists("test:key1")
            self.assertTrue(exists)

            # Delete
            deleted = await self.redis.delete("test:key1")
            self.assertEqual(deleted, 1)

            # Get deleted key
            value = await self.redis.get("test:key1")
            self.assertIsNone(value)

        asyncio.run(run_test())

    def test_json_operations(self):
        """Test JSON operations."""

        async def run_test():
            await self.redis.initialize()

            data = {"name": "test", "value": 123, "items": [1, 2, 3]}

            # Set JSON
            success = await self.redis.set_json("test:json1", data)
            self.assertTrue(success)

            # Get JSON
            retrieved = await self.redis.get_json("test:json1")
            self.assertEqual(retrieved, data)

        asyncio.run(run_test())

    def test_expiration(self):
        """Test key expiration."""

        async def run_test():
            await self.redis.initialize()

            # Set with expiration
            await self.redis.set("test:expire1", "value", expire=1)

            # Check TTL
            ttl = await self.redis.ttl("test:expire1")
            self.assertGreater(ttl, 0)
            self.assertLessEqual(ttl, 1)

            # Wait for expiration
            await asyncio.sleep(1.1)

            # Key should be gone
            value = await self.redis.get("test:expire1")
            self.assertIsNone(value)

        asyncio.run(run_test())

    def test_increment_decrement(self):
        """Test increment and decrement operations."""

        async def run_test():
            await self.redis.initialize()

            # Increment
            count = await self.redis.incr("test:counter1")
            self.assertEqual(count, 1)

            count = await self.redis.incr("test:counter1", 5)
            self.assertEqual(count, 6)

            # Decrement
            count = await self.redis.decr("test:counter1", 2)
            self.assertEqual(count, 4)

        asyncio.run(run_test())


class SessionManagerTests(unittest.TestCase):
    """Tests for SessionManager."""

    def setUp(self):
        """Set up test environment."""
        self.redis_url = "redis://localhost:6379/15"
        self.redis = RedisManager(self.redis_url)
        self.session_mgr = SessionManager(self.redis, ttl=60)

    def tearDown(self):
        """Clean up after tests."""
        asyncio.run(self._cleanup())

    async def _cleanup(self):
        """Async cleanup."""
        if self.redis.client:
            keys = await self.redis.keys("session:*")
            if keys:
                for key in keys:
                    await self.redis.delete(key)
            await self.redis.close()

    def test_create_session(self):
        """Test session creation."""

        async def run_test():
            await self.redis.initialize()

            session_id = await self.session_mgr.create_session(
                user_id="user123", metadata={"ip": "127.0.0.1"}
            )

            self.assertIsNotNone(session_id)
            self.assertTrue(len(session_id) > 0)

        asyncio.run(run_test())

    def test_get_session(self):
        """Test getting session data."""

        async def run_test():
            await self.redis.initialize()

            # Create session
            session_id = await self.session_mgr.create_session(
                user_id="user456", metadata={"device": "mobile"}
            )

            # Get session
            session = await self.session_mgr.get_session(session_id)
            self.assertIsNotNone(session)
            self.assertEqual(session["user_id"], "user456")
            self.assertEqual(session["metadata"]["device"], "mobile")

        asyncio.run(run_test())

    def test_update_session(self):
        """Test updating session."""

        async def run_test():
            await self.redis.initialize()

            # Create session
            session_id = await self.session_mgr.create_session(user_id="user789")

            # Update session
            success = await self.session_mgr.update_session(
                session_id, {"metadata": {"updated": True}}
            )
            self.assertTrue(success)

            # Verify update
            session = await self.session_mgr.get_session(session_id)
            self.assertTrue(session["metadata"]["updated"])

        asyncio.run(run_test())

    def test_delete_session(self):
        """Test deleting session."""

        async def run_test():
            await self.redis.initialize()

            # Create and delete session
            session_id = await self.session_mgr.create_session(user_id="user999")
            deleted = await self.session_mgr.delete_session(session_id)
            self.assertTrue(deleted)

            # Verify deletion
            session = await self.session_mgr.get_session(session_id)
            self.assertIsNone(session)

        asyncio.run(run_test())


class LLMCacheTests(unittest.TestCase):
    """Tests for LLMCache."""

    def setUp(self):
        """Set up test environment."""
        self.redis_url = "redis://localhost:6379/15"
        self.redis = RedisManager(self.redis_url)
        self.cache = LLMCache(self.redis, ttl=60)

    def tearDown(self):
        """Clean up after tests."""
        asyncio.run(self._cleanup())

    async def _cleanup(self):
        """Async cleanup."""
        if self.redis.client:
            await self.cache.clear_all()
            await self.cache.reset_stats()
            await self.redis.close()

    def test_cache_miss(self):
        """Test cache miss."""

        async def run_test():
            await self.redis.initialize()

            result = await self.cache.get(
                prompt="test prompt", model="test-model"
            )
            self.assertIsNone(result)

        asyncio.run(run_test())

    def test_cache_hit(self):
        """Test cache hit."""

        async def run_test():
            await self.redis.initialize()

            prompt = "What is the capital of France?"
            model = "gpt-4"
            response = {"content": "Paris", "tokens": 10}

            # Cache response
            await self.cache.set(prompt, model, response)

            # Get cached response
            cached = await self.cache.get(prompt, model)
            self.assertIsNotNone(cached)
            self.assertEqual(cached["content"], "Paris")

        asyncio.run(run_test())

    def test_cache_with_parameters(self):
        """Test cache with different parameters."""

        async def run_test():
            await self.redis.initialize()

            prompt = "Hello"
            model = "gpt-4"
            response1 = {"content": "Response 1"}
            response2 = {"content": "Response 2"}

            # Cache with different temperatures
            await self.cache.set(
                prompt, model, response1, temperature=0.5
            )
            await self.cache.set(
                prompt, model, response2, temperature=0.9
            )

            # Get with correct parameters
            cached1 = await self.cache.get(prompt, model, temperature=0.5)
            cached2 = await self.cache.get(prompt, model, temperature=0.9)

            self.assertEqual(cached1["content"], "Response 1")
            self.assertEqual(cached2["content"], "Response 2")

        asyncio.run(run_test())

    def test_cache_stats(self):
        """Test cache statistics."""

        async def run_test():
            await self.redis.initialize()

            # Reset stats
            await self.cache.reset_stats()

            # Generate some cache activity
            await self.cache.set("prompt1", "model1", {"content": "test"})
            await self.cache.get("prompt1", "model1")  # Hit
            await self.cache.get("prompt2", "model2")  # Miss

            # Check stats
            stats = await self.cache.get_stats()
            self.assertEqual(stats["hits"], 1)
            self.assertEqual(stats["misses"], 1)
            self.assertEqual(stats["writes"], 1)

        asyncio.run(run_test())


class RateLimiterTests(unittest.TestCase):
    """Tests for RateLimiter."""

    def setUp(self):
        """Set up test environment."""
        self.redis_url = "redis://localhost:6379/15"
        self.redis = RedisManager(self.redis_url)
        self.limiter = RateLimiter(
            self.redis, requests_per_minute=5, requests_per_hour=10
        )

    def tearDown(self):
        """Clean up after tests."""
        asyncio.run(self._cleanup())

    async def _cleanup(self):
        """Async cleanup."""
        if self.redis.client:
            keys = await self.redis.keys("ratelimit:*")
            if keys:
                for key in keys:
                    await self.redis.delete(key)
            await self.redis.close()

    def test_rate_limit_allowed(self):
        """Test rate limit when within limits."""

        async def run_test():
            await self.redis.initialize()

            identifier = "test:user1"

            # First request should be allowed
            allowed, info = await self.limiter.is_allowed(identifier)
            self.assertTrue(allowed)
            self.assertEqual(info["minute"]["count"], 1)

        asyncio.run(run_test())

    def test_rate_limit_exceeded(self):
        """Test rate limit when exceeded."""

        async def run_test():
            await self.redis.initialize()

            identifier = "test:user2"

            # Make 5 requests (limit is 5 per minute)
            for i in range(5):
                allowed, info = await self.limiter.is_allowed(identifier)
                self.assertTrue(allowed)

            # 6th request should be blocked
            allowed, info = await self.limiter.is_allowed(identifier)
            self.assertFalse(allowed)
            self.assertEqual(info["minute"]["remaining"], 0)

        asyncio.run(run_test())

    def test_rate_limit_reset(self):
        """Test rate limit reset."""

        async def run_test():
            await self.redis.initialize()

            identifier = "test:user3"

            # Make some requests
            await self.limiter.is_allowed(identifier)
            await self.limiter.is_allowed(identifier)

            # Reset
            await self.limiter.reset_limit(identifier)

            # Check limit is reset
            allowed, info = await self.limiter.is_allowed(identifier)
            self.assertTrue(allowed)
            self.assertEqual(info["minute"]["count"], 1)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()

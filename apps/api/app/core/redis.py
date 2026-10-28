"""
Redis client and connection management.
"""

import json
from typing import Optional, Any, List, Dict, Union
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_settings

settings = get_settings()

_redis_client = None


async def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis.max_connections,
        )
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()


# High-level Redis operations
class RedisCache:
    """High-level Redis cache operations."""
    
    def __init__(self, redis_client):
        self.redis = redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set value in cache."""
        data = json.dumps(value, default=str)
        return await self.redis.set(key, json.dumps(value, default=str), ex=expire, nx=nx, xx=xx)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        return await self.redis.delete(*keys)
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return await self.redis.exists(*keys)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        return await self.redis.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get TTL of key."""
        return await self.redis.ttl(key)
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment value."""
        return await self.redis.incrby(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement value."""
        return await self.redis.decrby(key, amount)
    
    # Hash operations
    async def hset(self, name: str, mapping: dict = None, **kwargs) -> int:
        """Set hash fields."""
        return await self.redis.hset(name, mapping=mapping, **kwargs)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        return await self.redis.hget(name, key)
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields."""
        return await self.redis.hgetall(name)
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        return await self.redis.hdel(name, *keys)
    
    async def hexists(self, name: str, key: str) -> bool:
        """Check if hash field exists."""
        return await self.redis.hexists(name, key)
    
    # List operations
    async def lpush(self, name: str, *values: str) -> int:
        return await self.redis.lpush(name, *values)
    
    async def rpush(self, name: str, *values: str) -> int:
        return await self.redis.rpush(name, *values)
    
    async def lpop(self, name: str) -> Optional[str]:
        return await self.redis.lpop(name)
    
    async def rpop(self, name: str) -> Optional[str]:
        return await self.redis.rpop(name)
    
    async def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        return await self.redis.lrange(name, start, end)
    
    async def llen(self, name: str) -> int:
        return await self.redis.llen(name)
    
    # Set operations
    async def sadd(self, name: str, *values: str) -> int:
        return await self.redis.sadd(name, *values)
    
    async def srem(self, name: str, *values: str) -> int:
        return await self.redis.srem(name, *values)
    
    async def smembers(self, name: str) -> set:
        return await self.redis.smembers(name)
    
    async def sismember(self, name: str, value: str) -> bool:
        return await self.redis.sismember(name, value)
    
    async def scard(self, name: str) -> int:
        return await self.redis.scard(name)
    
    # Sorted set operations
    async def zadd(self, name: str, mapping: dict) -> int:
        return await self.redis.zadd(name, mapping)
    
    async def zrem(self, name: str, *values: str) -> int:
        return await self.redis.zrem(name, *values)
    
    async def zrange(self, name: str, start: int = 0, end: int = -1, desc: bool = False) -> List[str]:
        return await self.redis.zrange(name, start, end, desc=desc)
    
    async def zrevrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        return await self.redis.zrevrange(name, start, end)
    
    async def zrangebyscore(
        self,
        name: str,
        min: float,
        max: float,
        start: int = None,
        num: int = None,
    ) -> List[str]:
        return await self.redis.zrangebyscore(name, min, max, start=start, num=num)
    
    async def zscore(self, name: str, value: str) -> Optional[float]:
        return await self.redis.zscore(name, value)
    
    async def zcard(self, name: str) -> int:
        return await self.redis.zcard(name)
    
    # Pub/Sub
    async def publish(self, channel: str, message: Any) -> int:
        return await self.redis.publish(channel, json.dumps(message, default=str))
    
    @asynccontextmanager
    async def subscribe(self, *channels: str):
        pubsub = self.redis.pubsub()
        try:
            await pubsub.subscribe(*channels)
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
    
    # Lua scripts for atomic operations
    def register_script(self, script: str):
        """Register a Lua script."""
        return self.redis.register_script(script)
    
    # Pipeline for batch operations
    def pipeline(self):
        return self.redis.pipeline()
    
    # Key management
    async def keys(self, pattern: str) -> List[str]:
        return await self.redis.keys(pattern)
    
    async def scan(self, cursor: int = 0, match: str = None, count: int = 100):
        return await self.redis.scan(cursor, match=match, count=count)
    
    async def scan_iter(self, match: str = None, count: int = 100):
        async for key in self.redis.scan_iter(match=match, count=count):
            yield key
    
    # TTL management
    async def pexpire(self, key: str, milliseconds: int) -> bool:
        return await self.redis.pexpire(key, milliseconds)
    
    async def pttl(self, key: str) -> int:
        return await self.redis.pttl(key)
    
    # Rename
    async def rename(self, src: str, dst: str) -> bool:
        return await self.redis.rename(src, dst)
    
    async def renamenx(self, src: str, dst: str) -> bool:
        return await self.redis.renamenx(src, dst)


async def get_redis_cache() -> RedisCache:
    """Get Redis cache instance."""
    redis_client = await get_redis()
    return RedisCache(_redis_client)


# Distributed lock
class DistributedLock:
    """Distributed lock using Redis."""
    
    def __init__(self, redis_client, name: str, timeout: int = 30):
        self.redis = redis_client
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.locked = False
    
    async def acquire(self, blocking: bool = True, timeout: int = None) -> bool:
        """Acquire the lock."""
        timeout = timeout or self.timeout
        end_time = time.time() + timeout
        
        while True:
            acquired = await self.redis.set(
                self.name,
                "locked",
                nx=True,
                ex=self.timeout,
            )
            if acquired:
                return True
            
            if not blocking:
                return False
            
            if time.time() >= end_time:
                return False
            
            await asyncio.sleep(0.1)
    
    async def release(self) -> bool:
        """Release the lock."""
        # Use Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        script = redis.register_script("""
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """)
        
        result = await script(keys=[self.name], args=[b"locked"])
        return result > 0
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
        return False
    
    async def release(self):
        """Release the lock."""
        await self.release()


# Rate limiter using sliding window
class SlidingWindowRateLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, redis_client, max_requests: int, window_seconds: int):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window_seconds
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - self.window
        key = f"ratelimit:{key}"
        
        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, time.time() - self.window)
        
        # Count current requests
        current_count = await self.redis.zcard(key)
        
        if current_count >= self.max_requests:
            # Get oldest request to calculate retry-after
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            retry_after = 0
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + self.window - time.time()) + 1
            
            return False, {
                "allowed": False,
                "limit": self.max_requests,
                "remaining": 0,
                "reset": int(time.time() + self.window),
                "retry_after": retry_after,
            }
        
        # Add current request
        await self.redis.zadd(key, {str(time.time()): time.time()})
        await self.redis.expire(key, self.window)
        
        return True, {
            "allowed": True,
            "limit": self.max_requests,
            "remaining": self.max_requests - current_count - 1,
            "reset": int(time.time() + self.window),
        }


# Session store
class SessionStore:
    """Session storage using Redis."""
    
    def __init__(self, redis_client, ttl: int = 1800):
        self.redis = redis_client
        self.ttl = ttl
        self.prefix = "session:"
    
    async def create(self, session_id: str, data: dict, ttl: int = None) -> bool:
        """Create a new session."""
        key = f"session:{session_id}"
        data_json = json.dumps(data, default=str)
        return await self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(data, default=str)
        )
    
    async def get(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        data = await self.redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    async def update(self, session_id: str, data: dict, ttl: int = None) -> bool:
        """Update session data."""
        key = f"session:{session_id}"
        existing = await self.redis.get(f"session:{session_id}")
        if not existing:
            return False
        
        current = json.loads(existing)
        current.update(data)
        
        return await self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(current, default=str)
        )
    
    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        return await self.redis.delete(f"session:{session_id}") > 0
    
    async def extend(self, session_id: str, ttl: int = None) -> bool:
        """Extend session TTL."""
        return await self.redis.expire(f"session:{session_id}", ttl or self.ttl)
    
    async def exists(self, session_id: str) -> bool:
        return await self.redis.exists(f"session:{session_id}") > 0
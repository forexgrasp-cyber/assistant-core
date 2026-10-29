"""
Streaming Engine Utilities
"""
import structlog
from typing import Any, Dict, Optional, Type
import orjson
from datetime import datetime, timedelta
import uuid
import asyncio


def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger."""
    return structlog.get_logger(name)


def serialize_event(event: Any) -> bytes:
    """Serialize event to bytes using orjson."""
    if hasattr(event, "model_dump"):
        return orjson.dumps(event.model_dump(mode="json"))
    return orjson.dumps(event)


def deserialize_event(data: bytes, model: type) -> Any:
    """Deserialize event from bytes."""
    return model.model_validate(orjson.loads(data))


def generate_event_id() -> str:
    """Generate unique event ID."""
    return uuid.uuid4().hex


def generate_correlation_id() -> str:
    """Generate correlation ID."""
    return uuid.uuid4().hex


def get_current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(datetime.utcnow().timestamp() * 1000)


def parse_timestamp_ms(timestamp_ms: int) -> datetime:
    """Parse timestamp from milliseconds."""
    return datetime.utcfromtimestamp(timestamp_ms / 1000)


def extract_partition_key(event: Any, fallback: str = "default") -> str:
    """Extract partition key from event."""
    # Try user_id first
    if hasattr(event, "user") and event.user:
        if event.user.user_id:
            return str(event.user.user_id)
        if event.user.anonymous_id:
            return str(event.user.anonymous_id)

    # Try event metadata
    if hasattr(event, "metadata"):
        if hasattr(event.metadata, "correlation_id") and event.metadata.correlation_id:
            return str(event.metadata.correlation_id)

    return fallback


def sanitize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, bytes]:
    """Sanitize headers for Kafka."""
    if not headers:
        return {}

    sanitized = {}
    for k, v in headers.items():
        if isinstance(v, (str, int, float, bool)):
            sanitized[k] = str(v).encode()
        elif isinstance(v, bytes):
            sanitized[k] = v
        else:
            sanitized[k] = str(v).encode()
    return sanitized


def calculate_processing_duration(start_time: datetime) -> int:
    """Calculate processing duration in milliseconds."""
    if start_time is None:
        return 0
    return int((datetime.utcnow() - start_time).total_seconds() * 1000)


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: Type[BaseException] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self.last_failure_time and datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay."""
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        delay *= (0.5 + random.random())
    return delay


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary."""
        async with self._lock:
            now = datetime.utcnow()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return

            # Wait for tokens to become available
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0


import asyncio
from datetime import timedelta
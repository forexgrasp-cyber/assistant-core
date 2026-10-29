"""
Event Producer for Kafka
"""
import asyncio
import uuid
from typing import Optional, List, Dict, Any, Callable, Awaitable
from datetime import datetime
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import orjson

from ..config import get_streaming_settings
from ..models import EventEnvelope, BaseEvent, StreamCheckpoint
from ..utils import get_logger, serialize_event

logger = get_logger(__name__)


class EventProducer:
    """
    High-performance event producer with exactly-once semantics support.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        transactional_id: Optional[str] = None,
        enable_idempotence: bool = True,
        max_batch_size: int = 16384,
        linger_ms: int = 5,
        compression_type: str = "zstd",
        acks: str = "all",
        **kwargs
    ):
        self.settings = get_streaming_settings()
        self.bootstrap_servers = bootstrap_servers or self.settings.kafka_bootstrap_servers
        self.transactional_id = transactional_id or f"producer-{uuid.uuid4().hex[:8]}"
        self.enable_idempotence = enable_idempotence
        self.max_batch_size = max_batch_size
        self.linger_ms = linger_ms
        self.compression_type = compression_type
        self.acks = acks
        self.extra_config = kwargs

        self._producer: Optional[AIOKafkaProducer] = None
        self._transaction_active = False
        self._callbacks: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {
            "on_send": [],
            "on_error": [],
            "on_transaction_commit": [],
            "on_transaction_abort": [],
        }

    async def start(self) -> None:
        """Initialize and start the producer."""
        if self._producer is not None:
            return

        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "enable_idempotence": self.enable_idempotence,
            "max_batch_size": self.max_batch_size,
            "linger_ms": self.linger_ms,
            "compression_type": self.compression_type,
            "acks": self.acks,
            "value_serializer": lambda v: orjson.dumps(v),
            "key_serializer": lambda k: k.encode() if k else None,
            **self.extra_config,
        }

        if self.settings.kafka_security_protocol != "PLAINTEXT":
            config.update({
                "security_protocol": self.settings.kafka_security_protocol,
            })
            if self.settings.kafka_sasl_mechanism:
                config.update({
                    "sasl_mechanism": self.settings.kafka_sasl_mechanism,
                    "sasl_plain_username": self.settings.kafka_sasl_username,
                    "sasl_plain_password": self.settings.kafka_sasl_password,
                })

        if self.transactional_id:
            config["transactional_id"] = self.transactional_id
            config["transaction_timeout_ms"] = self.settings.transaction_timeout_ms

        self._producer = AIOKafkaProducer(**config)
        await self._producer.start()

        if self.transactional_id:
            await self._producer.init_transactions()

        logger.info(
            "event_producer_started",
            transactional_id=self.transactional_id,
            bootstrap_servers=self.bootstrap_servers,
        )

    async def stop(self) -> None:
        """Stop the producer gracefully."""
        if self._producer is None:
            return

        if self._transaction_active:
            await self.abort_transaction()

        await self._producer.stop()
        self._producer = None
        self._transaction_active = False

        logger.info("event_producer_stopped", transactional_id=self.transactional_id)

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactional production."""
        if not self.transactional_id:
            raise RuntimeError("Transactional producer not configured with transactional_id")

        await self.begin_transaction()
        try:
            yield self
            await self.commit_transaction()
        except Exception:
            await self.abort_transaction()
            raise

    async def begin_transaction(self) -> None:
        """Begin a new transaction."""
        if self._transaction_active:
            raise RuntimeError("Transaction already active")

        await self._producer.begin_transaction()
        self._transaction_active = True
        logger.debug("transaction_begin", transactional_id=self.transactional_id)

    async def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._transaction_active:
            raise RuntimeError("No active transaction to commit")

        await self._producer.commit_transaction()
        self._transaction_active = False

        for callback in self._callbacks["on_transaction_commit"]:
            await callback(None)

        logger.debug("transaction_commit", transactional_id=self.transactional_id)

    async def abort_transaction(self) -> None:
        """Abort the current transaction."""
        if not self._transaction_active:
            return

        await self._producer.abort_transaction()
        self._transaction_active = False

        for callback in self._callbacks["on_transaction_abort"]:
            await callback(None)

        logger.warning("transaction_abort", transactional_id=self.transactional_id)

    async def send(
        self,
        topic: str,
        event: BaseEvent,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
    ) -> Any:
        """
        Send a single event to Kafka.

        Args:
            topic: Target topic
            event: Event to send
            key: Partition key (uses user_id if available)
            headers: Additional headers
            partition: Explicit partition (optional)
            timestamp_ms: Event timestamp in milliseconds

        Returns:
            Future with record metadata
        """
        if self._producer is None:
            raise RuntimeError("Producer not started. Call start() first.")

        envelope = EventEnvelope(
            event=event,
            partition_key=key,
            headers=headers or {},
        )

        # Use user_id as partition key for ordering
        if key is None and event.user and event.user.user_id:
            key = event.user.user_id
        elif key is None and event.user and event.user.anonymous_id:
            key = event.user.anonymous_id

        future = await self._producer.send(
            topic=topic,
            value=envelope.model_dump(mode="json"),
            key=key,
            headers=[(k, v.encode()) for k, v in (headers or {}).items()] if headers else None,
            partition=partition,
            timestamp_ms=timestamp_ms or int(event.metadata.timestamp.timestamp() * 1000),
        )

        record_metadata = await future

        # Execute callbacks
        for callback in self._callbacks["on_send"]:
            await callback(record_metadata)

        logger.debug(
            "event_sent",
            topic=topic,
            partition=record_metadata.partition,
            offset=record_metadata.offset,
            event_type=event.metadata.event_type,
        )

        return record_metadata

    async def send_batch(
        self,
        topic: str,
        events: List[BaseEvent],
        key_fn: Optional[Callable[[BaseEvent], str]] = None,
    ) -> List[Any]:
        """
        Send a batch of events efficiently.

        Args:
            topic: Target topic
            events: List of events to send
            key_fn: Function to extract partition key from event

        Returns:
            List of record metadata
        """
        if not events:
            return []

        futures = []
        for event in events:
            key = key_fn(event) if key_fn else None
            future = await self.send(topic, event, key=key)
            futures.append(future)

        return futures

    async def send_checkpoint(self, checkpoint: StreamCheckpoint) -> None:
        """Send stream processing checkpoint."""
        from ..models import EventEnvelope
        envelope = EventEnvelope(
            event=checkpoint,
            partition_key=f"{checkpoint.topic}-{checkpoint.partition}",
        )
        await self._producer.send(
            topic=self.settings.events_topic,
            value=envelope.model_dump(mode="json"),
            key=f"{checkpoint.topic}-{checkpoint.partition}",
        )

    def on_send(self, callback: Callable[[Any], Awaitable[None]]) -> None:
        """Register callback for successful sends."""
        self._callbacks["on_send"].append(callback)

    def on_error(self, callback: Callable[[Any], Awaitable[None]]) -> None:
        """Register callback for errors."""
        self._callbacks["on_error"].append(callback)

    def on_transaction_commit(self, callback: Callable[[Any], Awaitable[None]]) -> None:
        """Register callback for transaction commits."""
        self._callbacks["on_transaction_commit"].append(callback)

    def on_transaction_abort(self, callback: Callable[[Any], Awaitable[None]]) -> None:
        """Register callback for transaction aborts."""
        self._callbacks["on_transaction_abort"].append(callback)

    @property
    def is_active(self) -> bool:
        return self._producer is not None and not self._producer._closed

    @property
    def in_transaction(self) -> bool:
        return self._transaction_active


class EventProducerPool:
    """Pool of event producers for high-throughput scenarios."""

    def __init__(
        self,
        pool_size: int = 4,
        **producer_kwargs
    ):
        self.pool_size = pool_size
        self.producer_kwargs = producer_kwargs
        self._producers: List[EventProducer] = []
        self._index = 0

    async def start(self) -> None:
        """Start all producers in the pool."""
        for i in range(self.pool_size):
            producer = EventProducer(
                transactional_id=f"pool-producer-{i}-{uuid.uuid4().hex[:8]}",
                **self.producer_kwargs
            )
            await producer.start()
            self._producers.append(producer)

        logger.info("producer_pool_started", pool_size=self.pool_size)

    async def stop(self) -> None:
        """Stop all producers in the pool."""
        for producer in self._producers:
            await producer.stop()
        self._producers.clear()

    def get_producer(self) -> EventProducer:
        """Get next producer in round-robin fashion."""
        if not self._producers:
            raise RuntimeError("Pool not started")

        producer = self._producers[self._index]
        self._index = (self._index + 1) % self.pool_size
        return producer

    async def send(self, *args, **kwargs) -> Any:
        """Send using next available producer."""
        return await self.get_producer().send(*args, **kwargs)

    async def send_batch(self, *args, **kwargs) -> List[Any]:
        """Send batch using next available producer."""
        return await self.get_producer().send_batch(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return all(p.is_active for p in self._producers)
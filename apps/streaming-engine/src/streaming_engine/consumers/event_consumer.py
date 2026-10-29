"""
Event Consumer for Kafka
"""
import asyncio
import uuid
from typing import Optional, List, Dict, Any, Callable, Awaitable, Set
from datetime import datetime
from contextlib import asynccontextmanager
from collections import defaultdict

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from aiokafka.structs import TopicPartition, OffsetAndMetadata
import orjson

from ..config import get_streaming_settings
from ..models import EventEnvelope, BaseEvent, StreamCheckpoint, DeadLetterEvent
from ..utils import get_logger, extract_partition_key, exponential_backoff

logger = get_logger(__name__)


class EventConsumer:
    """
    High-performance event consumer with exactly-once semantics support.
    """

    def __init__(
        self,
        topics: List[str],
        group_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = False,
        max_poll_records: int = 500,
        max_poll_interval_ms: int = 300000,
        session_timeout_ms: int = 30000,
        heartbeat_interval_ms: int = 10000,
        isolation_level: str = "read_committed",
        **kwargs
    ):
        self.settings = get_streaming_settings()
        self.topics = topics
        self.group_id = group_id or self.settings.kafka_consumer_group
        self.bootstrap_servers = bootstrap_servers or self.settings.kafka_bootstrap_servers
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.max_poll_records = max_poll_records
        self.max_poll_interval_ms = max_poll_interval_ms
        self.session_timeout_ms = session_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms
        self.isolation_level = isolation_level
        self.extra_config = kwargs

        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._handlers: Dict[str, List[Callable[[BaseEvent], Awaitable[None]]]] = defaultdict(list)
        self._dead_letter_handler: Optional[Callable[[DeadLetterEvent], Awaitable[None]]] = None
        self._checkpoint_handler: Optional[Callable[[StreamCheckpoint], Awaitable[None]]] = None
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._offsets_to_commit: Dict[TopicPartition, OffsetAndMetadata] = {}
        self._commit_interval = 5  # seconds
        self._last_commit = datetime.utcnow()
        self._processed_count = 0
        self._error_count = 0

    async def start(self) -> None:
        """Initialize and start the consumer."""
        if self._consumer is not None:
            return

        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": self.group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "max_poll_records": self.max_poll_records,
            "max_poll_interval_ms": self.max_poll_interval_ms,
            "session_timeout_ms": self.session_timeout_ms,
            "heartbeat_interval_ms": self.heartbeat_interval_ms,
            "isolation_level": self.isolation_level,
            "value_deserializer": lambda v: orjson.loads(v) if v else None,
            "key_deserializer": lambda k: k.decode() if k else None,
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

        self._consumer = AIOKafkaConsumer(*self.topics, **config)
        await self._consumer.start()

        self._running = True
        logger.info(
            "event_consumer_started",
            topics=self.topics,
            group_id=self.group_id,
        )

        # Start background tasks
        asyncio.create_task(self._commit_offsets_periodically())
        asyncio.create_task(self._monitor_health())

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        self._running = False

        if self._consumer is not None:
            # Commit any pending offsets
            await self._commit_offsets()
            await self._consumer.stop()
            self._consumer = None

        logger.info("event_consumer_stopped", group_id=self.group_id)

    def on_event(self, event_type: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        """Register handler for specific event type."""
        self._handlers[event_type].append(handler)

    def on_any_event(self, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        """Register handler for all events."""
        self._handlers["*"].append(handler)

    def on_dead_letter(self, handler: Callable[[DeadLetterEvent], Awaitable[None]]) -> None:
        """Register handler for dead letter events."""
        self._dead_letter_handler = handler

    def on_checkpoint(self, handler: Callable[[StreamCheckpoint], Awaitable[None]]) -> None:
        """Register handler for checkpoints."""
        self._checkpoint_handler = handler

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        while self._running:
            try:
                records = await self._consumer.getmany(
                    timeout_ms=1000,
                    max_records=self.max_poll_records,
                )

                if not records:
                    continue

                for topic_partition, messages in records.items():
                    await self._process_batch(topic_partition, messages)

            except Exception as e:
                logger.error("consume_loop_error", error=str(e))
                await asyncio.sleep(1)

    async def _process_batch(
        self,
        topic_partition: TopicPartition,
        messages: List[Any]
    ) -> None:
        """Process a batch of messages."""
        for message in messages:
            if not self._running:
                break

            try:
                await self._process_message(message)
                self._processed_count += 1

                # Track offset for commit
                self._offsets_to_commit[topic_partition] = OffsetAndMetadata(
                    message.offset + 1,
                    message.timestamp
                )

            except Exception as e:
                self._error_count += 1
                logger.error(
                    "message_processing_error",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    error=str(e),
                )

                # Send to dead letter queue
                await self._send_to_dlq(message, str(e))

    async def _process_message(self, message: Any) -> None:
        """Process a single message."""
        if message.value is None:
            return

        try:
            envelope_data = message.value
            if not isinstance(envelope_data, dict):
                envelope_data = orjson.loads(message.value) if message.value else {}

            envelope = EventEnvelope.model_validate(envelope_data)
            event = envelope.event

            # Execute circuit breaker for external calls if needed
            event_type = event.metadata.event_type

            # Get or create circuit breaker for this event type
            if event_type not in self._circuit_breakers:
                self._circuit_breakers[event_type] = CircuitBreaker(
                    failure_threshold=10,
                    recovery_timeout=60,
                )

            # Process with circuit breaker
            circuit_breaker = self._circuit_breakers[event_type]

            # Execute handlers with retries
            await self._execute_handlers_with_retry(event)

        except Exception as e:
            logger.error("message_validation_error", error=str(e))
            raise

    async def _execute_handlers_with_retry(self, event: BaseEvent) -> None:
        """Execute all registered handlers with retry logic."""
        event_type = event.metadata.event_type

        # Get specific handlers and wildcard handlers
        handlers = self._handlers.get(event_type, []) + self._handlers.get("*", [])

        if not handlers:
            logger.warning("no_handler_for_event", event_type=event_type)
            return

        # Execute all handlers
        for handler in handlers:
            attempt = 0
            max_attempts = 3

            while attempt < max_attempts:
                try:
                    await handler(event)
                    break
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            "handler_failed_after_retries",
                            event_type=event.metadata.event_type,
                            handler=handler.__name__,
                            error=str(e),
                        )
                        # Send to DLQ after all retries exhausted
                        raise
                    else:
                        # Exponential backoff
                        delay = exponential_backoff(attempt)
                        await asyncio.sleep(delay)

    async def _send_to_dlq(self, message: Any, error: str) -> None:
        """Send failed message to dead letter queue."""
        try:
            envelope_data = message.value
            if not isinstance(envelope_data, dict):
                envelope_data = orjson.loads(message.value) if message.value else {}

            envelope = EventEnvelope.model_validate(envelope_data)

            dlq_event = DeadLetterEvent(
                original_event=envelope,
                error=error,
                error_type=type(Exception).__name__,
                processing_context={
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "timestamp": message.timestamp,
                }
            )

            if self._dead_letter_handler:
                await self._dead_letter_handler(dlq_event)

            logger.warning(
                "message_sent_to_dlq",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=error,
            )

        except Exception as e:
            logger.error("dlq_send_failed", error=str(e))

    async def _commit_offsets(self) -> None:
        """Commit processed offsets."""
        if not self._offsets_to_commit:
            return

        try:
            await self._consumer.commit(self._offsets_to_commit)
            self._offsets_to_commit.clear()
            self._last_commit = datetime.utcnow()
            logger.debug("offsets_committed", count=len(self._offsets_to_commit))
        except Exception as e:
            logger.error("offset_commit_failed", error=str(e))

    async def _commit_offsets_periodically(self) -> None:
        """Periodically commit offsets."""
        while self._running:
            await asyncio.sleep(self._commit_interval)
            await self._commit_offsets()

    async def _monitor_health(self) -> None:
        """Monitor consumer health."""
        while self._running:
            await asyncio.sleep(60)
            logger.info(
                "consumer_health",
                processed_count=self._processed_count,
                error_count=self._error_count,
                lag=await self._get_consumer_lag(),
            )

    async def _get_consumer_lag(self) -> Dict[int, int]:
        """Get consumer lag per partition."""
        if not self._consumer:
            return {}

        try:
            partitions = self._consumer.assignment()
            lag = {}
            for partition in partitions:
                end_offset = await self._consumer.get_end_offsets([partition])
                current_offset = await self._consumer.get_committed_offsets([partition])
                lag[partition.partition] = end_offset[partition] - current_offset.get(partition, 0)
            return lag
        except Exception:
            return {}

    @asynccontextmanager
    async def consuming(self):
        """Context manager for consuming events."""
        await self.start()
        consume_task = asyncio.create_task(self._consume_loop())
        try:
            yield self
        finally:
            self._running = False
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass
            await self.stop()

    @property
    def is_running(self) -> bool:
        return self._running and self._consumer is not None

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "running": self._running,
            "topics": self.topics,
            "group_id": self.group_id,
        }


class ConsumerGroup:
    """Manage multiple consumers for horizontal scaling."""

    def __init__(
        self,
        topics: List[str],
        group_id: str,
        num_consumers: int = 4,
        **consumer_kwargs
    ):
        self.topics = topics
        self.group_id = group_id
        self.num_consumers = num_consumers
        self.consumer_kwargs = consumer_kwargs
        self._consumers: List[EventConsumer] = []

    async def start(self) -> None:
        """Start all consumers in the group."""
        for i in range(self.num_consumers):
            consumer = EventConsumer(
                topics=self.topics,
                group_id=f"{self.group_id}-{i}",
                **self.consumer_kwargs
            )
            await consumer.start()
            self._consumers.append(consumer)

        logger.info("consumer_group_started", group_id=self.group_id, count=self.num_consumers)

    async def stop(self) -> None:
        """Stop all consumers in the group."""
        for consumer in self._consumers:
            await consumer.stop()
        self._consumers.clear()

    def on_event(self, event_type: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        """Register handler on all consumers."""
        for consumer in self._consumers:
            consumer.on_event(event_type, handler)

    def on_any_event(self, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        """Register handler for all events on all consumers."""
        for consumer in self._consumers:
            consumer.on_any_event(handler)

    def on_dead_letter(self, handler: Callable[[DeadLetterEvent], Awaitable[None]]) -> None:
        """Register DLQ handler on all consumers."""
        for consumer in self._consumers:
            consumer.on_dead_letter(handler)

    @property
    def stats(self) -> Dict[str, Any]:
        total_processed = sum(c._processed_count for c in self._consumers)
        total_errors = sum(c._error_count for c in self._consumers)
        return {
            "total_processed": total_processed,
            "total_errors": total_errors,
            "consumers": len(self._consumers),
            "consumer_stats": [c.stats for c in self._consumers],
        }
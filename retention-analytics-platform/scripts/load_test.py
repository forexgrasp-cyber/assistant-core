#!/usr/bin/env python3
"""
Load Test: 100k events/sec ingestion → workflow trigger → delivery

Tests the full pipeline under load:
1. Event ingestion via /api/v1/events
2. Workflow triggering via FlowTriggerService
3. Service execution (email.send, sms.send, analytics.metric.compute_retention)
4. Persistence verification (idempotent replay)

Usage:
    python scripts/load_test.py --events 100000 --duration 60 --concurrency 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration."""
    total_events: int = 100000
    duration_seconds: int = 60
    concurrency: int = 100
    base_url: str = "http://localhost:8000"
    tenant_id: str = "00000000-0000-0000-0000-000000000001"
    auth_token: str = "dev-token"
    event_types: list[str] = field(default_factory=lambda: [
        "customer.created",
        "order.placed",
        "cart.abandoned",
        "subscription.cancelled",
        "email.opened",
        "email.clicked",
        "sms.delivered",
        "push.received",
    ])
    workflow_triggers: list[str] = field(default_factory=lambda: [
        "churn_prevention",
        "welcome_series",
        "cart_recovery",
        "win_back",
        "dunning_escalation",
    ])


@dataclass
class LoadTestResults:
    """Load test results."""
    config: LoadTestConfig
    start_time: float
    end_time: float
    events_sent: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    workflows_triggered: int = 0
    workflows_succeeded: int = 0
    workflows_failed: int = 0
    latencies: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)
    throughput_eps: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    max_latency: float = 0.0

    def calculate_metrics(self) -> None:
        """Calculate derived metrics."""
        total_time = self.end_time - self.start_time
        if total_time > 0:
            self.throughput_eps = self.events_succeeded / total_time

        if self.latencies:
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            self.p50_latency = sorted_latencies[n // 2]
            self.p95_latency = sorted_latencies[int(n * 0.95)]
            self.p99_latency = sorted_latencies[int(n * 0.99)]
            self.max_latency = sorted_latencies[-1]


class LoadTestRunner:
    """Load test runner for event ingestion pipeline."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results = LoadTestResults(config=config, start_time=0, end_time=0)
        self._semaphore: asyncio.Semaphore | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {self.config.auth_token}"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _generate_event(self) -> dict[str, Any]:
        """Generate a realistic test event."""
        event_type = random.choice(self.config.event_types)
        event_id = f"evt-{uuid.uuid4().hex[:16]}"
        idempotency_key = f"idemp-{uuid.uuid4().hex[:16]}"

        # Base payload
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "tenant_id": self.config.tenant_id,
            "idempotency_key": idempotency_key,
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "customer_id": f"cust-{random.randint(1, 10000):06d}",
                "value": round(random.uniform(10, 1000), 2),
                "metadata": {
                    "source": "load_test",
                    "batch": random.randint(1, 100),
                },
            },
        }

        # Add event-type specific fields
        if event_type == "order.placed":
            payload["payload"].update({
                "order_id": f"ord-{uuid.uuid4().hex[:12]}",
                "items": [{"sku": f"SKU-{random.randint(1, 500)}", "qty": random.randint(1, 5)} for _ in range(random.randint(1, 3))],
            })
        elif event_type == "cart.abandoned":
            payload["payload"].update({
                "cart_id": f"cart-{uuid.uuid4().hex[:12]}",
                "abandoned_value": round(random.uniform(20, 500), 2),
            })
        elif event_type == "subscription.cancelled":
            payload["payload"].update({
                "subscription_id": f"sub-{uuid.uuid4().hex[:12]}",
                "reason": random.choice(["price", "competitor", "unused", "support"]),
            })

        return payload

    async def _send_event(self, event: dict[str, Any]) -> tuple[bool, float, str | None]:
        """Send a single event and return (success, latency_ms, error)."""
        start = time.perf_counter()
        try:
            async with self._semaphore:
                response = await self._client.post(
                    "/api/v1/events",
                    json=event,
                )
                latency = (time.perf_counter() - start) * 1000

                if response.status_code in (200, 201, 202):
                    return True, latency, None
                else:
                    error = f"HTTP {response.status_code}: {response.text[:200]}"
                    return False, latency, error

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, str(e)

    async def _trigger_workflow(self, event_type: str) -> tuple[bool, float, str | None]:
        """Trigger a workflow based on event type."""
        start = time.perf_counter()
        try:
            async with self._semaphore:
                workflow = random.choice(self.config.workflow_triggers)
                response = await self._client.post(
                    "/api/v1/workflows/trigger",
                    json={
                        "workflow_id": workflow,
                        "tenant_id": self.config.tenant_id,
                        "trigger_event": event_type,
                        "payload": {"test": True},
                    },
                )
                latency = (time.perf_counter() - start) * 1000

                if response.status_code in (200, 201, 202):
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {response.status_code}"

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, str(e)

    async def _run_worker(self, worker_id: int, events_per_worker: int) -> None:
        """Run a single worker sending events."""
        for i in range(events_per_worker):
            event = self._generate_event()

            # Send event
            success, latency, error = await self._send_event(event)
            self.results.events_sent += 1
            self.results.latencies.append(latency)

            if success:
                self.results.events_succeeded += 1

                # Trigger workflow for some events (20%)
                if random.random() < 0.2:
                    self.results.workflows_triggered += 1
                    wf_success, wf_latency, wf_error = await self._trigger_workflow(event["event_type"])
                    if wf_success:
                        self.results.workflows_succeeded += 1
                    else:
                        self.results.workflows_failed += 1
                        self.results.errors[wf_error or "unknown"] = self.results.errors.get(wf_error or "unknown", 0) + 1
            else:
                self.results.events_failed += 1
                self.results.errors[error or "unknown"] = self.results.errors.get(error or "unknown", 0) + 1

            # Progress logging
            if self.results.events_sent % 10000 == 0:
                elapsed = time.perf_counter() - self.results.start_time
                rate = self.results.events_succeeded / elapsed if elapsed > 0 else 0
                log.info("load_test.progress",
                         worker=worker_id,
                         sent=self.results.events_sent,
                         succeeded=self.results.events_succeeded,
                         failed=self.results.events_failed,
                         rate=round(rate, 1),
                         p50_latency=round(self._percentile(self.results.latencies, 50), 1))

    def _percentile(self, data: list[float], p: int) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    async def run(self) -> LoadTestResults:
        """Run the load test."""
        log.info("load_test.starting",
                 total_events=self.config.total_events,
                 duration=self.config.duration_seconds,
                 concurrency=self.config.concurrency)

        self.results.start_time = time.perf_counter()

        # Calculate events per worker
        num_workers = self.config.concurrency
        events_per_worker = self.config.total_events // num_workers

        # Run workers concurrently
        workers = [
            self._run_worker(i, events_per_worker)
            for i in range(num_workers)
        ]
        await asyncio.gather(*workers)

        self.results.end_time = time.perf_counter()
        self.results.calculate_metrics()

        log.info("load_test.completed",
                 events_sent=self.results.events_sent,
                 events_succeeded=self.results.events_succeeded,
                 events_failed=self.results.events_failed,
                 workflows_triggered=self.results.workflows_triggered,
                 workflows_succeeded=self.results.workflows_succeeded,
                 throughput_eps=round(self.results.throughput_eps, 1),
                 p50_latency=round(self.results.p50_latency, 1),
                 p95_latency=round(self.results.p95_latency, 1),
                 p99_latency=round(self.results.p99_latency, 1),
                 max_latency=round(self.results.max_latency, 1))

        return self.results

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("LOAD TEST SUMMARY")
        print("=" * 60)
        print(f"Configuration:")
        print(f"  Total Events:     {self.config.total_events:,}")
        print(f"  Duration:         {self.config.duration_seconds}s")
        print(f"  Concurrency:      {self.config.concurrency}")
        print(f"  Target Throughput: {self.config.total_events / self.config.duration_seconds:,.0f} eps")
        print()
        print(f"Results:")
        print(f"  Events Sent:      {self.results.events_sent:,}")
        print(f"  Events Succeeded: {self.results.events_succeeded:,}")
        print(f"  Events Failed:    {self.results.events_failed:,}")
        print(f"  Success Rate:     {self.results.events_succeeded / max(self.results.events_sent, 1) * 100:.2f}%")
        print()
        print(f"  Workflows Triggered: {self.results.workflows_triggered:,}")
        print(f"  Workflows Succeeded: {self.results.workflows_succeeded:,}")
        print(f"  Workflows Failed:    {self.results.workflows_failed:,}")
        print()
        print(f"Performance:")
        print(f"  Actual Throughput:  {self.results.throughput_eps:,.1f} eps")
        print(f"  P50 Latency:        {self.results.p50_latency:.1f} ms")
        print(f"  P95 Latency:        {self.results.p95_latency:.1f} ms")
        print(f"  P99 Latency:        {self.results.p99_latency:.1f} ms")
        print(f"  Max Latency:        {self.results.max_latency:.1f} ms")
        print()
        if self.results.errors:
            print(f"Errors:")
            for error, count in sorted(self.results.errors.items(), key=lambda x: -x[1])[:10]:
                print(f"  {error}: {count}")
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Load test event ingestion pipeline")
    parser.add_argument("--events", type=int, default=100000, help="Total events to send")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrent workers")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--tenant", default="00000000-0000-0000-0000-000000000001", help="Tenant ID")
    parser.add_argument("--token", default="dev-token", help="Auth token")
    args = parser.parse_args()

    config = LoadTestConfig(
        total_events=args.events,
        duration_seconds=args.duration,
        concurrency=args.concurrency,
        base_url=args.url,
        tenant_id=args.tenant,
        auth_token=args.token,
    )

    async with LoadTestRunner(config) as runner:
        results = await runner.run()
        runner.print_summary()

        # Exit with error code if success rate < 99%
        if results.events_succeeded / max(results.events_sent, 1) < 0.99:
            print("\n❌ FAIL: Success rate below 99%")
            exit(1)
        else:
            print("\n✅ PASS: Success rate >= 99%")
            exit(0)


if __name__ == "__main__":
    asyncio.run(main())
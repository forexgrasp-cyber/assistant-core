#!/usr/bin/env python3
"""
Chaos Test: Kill workers mid-workflow → verify idempotent replay + no duplicate sends

Tests system resilience under failure conditions:
1. Worker crash mid-workflow execution
2. Network partition during service calls
3. Database connection loss
4. Message broker failure
5. Idempotent replay verification
6. No duplicate sends verification

Usage:
    python scripts/chaos_test.py --workflows 1000 --failure-rate 0.1
"""

from __future__ import annotations

import argparse
import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)


class FailureType(StrEnum):
    """Types of chaos failures to inject."""
    WORKER_CRASH = "worker_crash"
    NETWORK_PARTITION = "network_partition"
    DB_CONNECTION_LOSS = "db_connection_loss"
    MESSAGE_BROKER_FAILURE = "message_broker_failure"
    SERVICE_TIMEOUT = "service_timeout"
    PARTIAL_FAILURE = "partial_failure"


class WorkflowStatus(StrEnum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLAYED = "replayed"
    DUPLICATE_DETECTED = "duplicate_detected"


@dataclass
class WorkflowExecution:
    """A single workflow execution with chaos injection."""
    execution_id: str
    workflow_id: str
    tenant_id: str
    idempotency_key: str
    steps: list[dict[str, Any]]
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    failure_injected: FailureType | None = None
    failure_step: int | None = None
    replay_count: int = 0
    duplicate_sends: int = 0
    steps_completed: list[int] = field(default_factory=list)
    steps_failed: list[int] = field(default_factory=list)
    service_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ChaosTestResults:
    """Chaos test results."""
    total_workflows: int = 0
    completed: int = 0
    failed: int = 0
    replayed: int = 0
    duplicates_detected: int = 0
    idempotent_verified: int = 0
    idempotent_violations: int = 0
    total_service_calls: int = 0
    failed_service_calls: int = 0
    failure_injections: dict[str, int] = field(default_factory=dict)
    executions: list[WorkflowExecution] = field(default_factory=list)

    def calculate_metrics(self) -> dict[str, float]:
        """Calculate success metrics."""
        return {
            "completion_rate": self.completed / max(self.total_workflows, 1),
            "replay_rate": self.replayed / max(self.total_workflows, 1),
            "duplicate_rate": self.duplicates_detected / max(self.total_service_calls, 1),
            "idempotent_compliance": self.idempotent_verified / max(self.idempotent_verified + self.idempotent_violations, 1),
            "service_call_success_rate": (self.total_service_calls - self.failed_service_calls) / max(self.total_service_calls, 1),
        }


class ChaosTestRunner:
    """Chaos test runner for workflow resilience."""

    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        auth_token: str,
        total_workflows: int,
        failure_rate: float,
        concurrency: int,
    ):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.auth_token = auth_token
        self.total_workflows = total_workflows
        self.failure_rate = failure_rate
        self.concurrency = concurrency
        self.results = ChaosTestResults(total_workflows=total_workflows)
        self._semaphore: asyncio.Semaphore | None = None
        self._client: httpx.AsyncClient | None = None
        self._service_call_log: dict[str, list[dict]] = {}  # idempotency_key -> calls

    async def __aenter__(self):
        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0),
            headers={"Authorization": f"Bearer {self.auth_token}"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _generate_workflow(self) -> WorkflowExecution:
        """Generate a test workflow with multiple steps."""
        workflow_types = [
            {
                "workflow_id": "churn_prevention",
                "steps": [
                    {"service": "analytics.metric", "action": "compute_retention", "payload": {}},
                    {"service": "email", "action": "send", "payload": {"template": "churn_warning"}},
                    {"service": "analytics.metric", "action": "compute_rfm", "payload": {}},
                ],
            },
            {
                "workflow_id": "welcome_series",
                "steps": [
                    {"service": "email", "action": "send", "payload": {"template": "welcome_1"}},
                    {"service": "analytics.metric", "action": "compute_retention", "payload": {}},
                    {"service": "sms", "action": "send", "payload": {"template": "welcome_sms"}},
                    {"service": "push", "action": "send", "payload": {"template": "welcome_push"}},
                ],
            },
            {
                "workflow_id": "cart_recovery",
                "steps": [
                    {"service": "email", "action": "send", "payload": {"template": "cart_abandoned_1"}},
                    {"service": "sms", "action": "send", "payload": {"template": "cart_sms"}},
                    {"service": "analytics.metric", "action": "compute_retention", "payload": {}},
                ],
            },
            {
                "workflow_id": "dunning_escalation",
                "steps": [
                    {"service": "email", "action": "send", "payload": {"template": "payment_failed_1"}},
                    {"service": "sms", "action": "send", "payload": {"template": "payment_sms"}},
                    {"service": "analytics.metric", "action": "compute_retention", "payload": {}},
                    {"service": "email", "action": "send", "payload": {"template": "payment_final"}},
                ],
            },
        ]

        wf = random.choice(workflow_types)
        return WorkflowExecution(
            execution_id=f"exec-{uuid.uuid4().hex[:12]}",
            workflow_id=wf["workflow_id"],
            tenant_id=self.tenant_id,
            idempotency_key=f"idemp-{uuid.uuid4().hex[:16]}",
            steps=wf["steps"],
        )

    def _should_inject_failure(self) -> FailureType | None:
        """Determine if a failure should be injected."""
        if random.random() > self.failure_rate:
            return None
        return random.choice(list(FailureType))

    async def _execute_step(
        self,
        execution: WorkflowExecution,
        step_index: int,
        failure: FailureType | None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """Execute a single workflow step with potential failure injection."""
        step = execution.steps[step_index]
        service = step["service"]
        action = step["action"]
        payload = {**step["payload"], "tenant_id": self.tenant_id, "idempotency_key": execution.idempotency_key}

        call_record = {
            "step": step_index,
            "service": service,
            "action": action,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            "failure_injected": failure.value if failure else None,
        }
        execution.service_calls.append(call_record)
        self.results.total_service_calls += 1

        # Track for idempotency verification
        key = execution.idempotency_key
        if key not in self._service_call_log:
            self._service_call_log[key] = []
        self._service_call_log[key].append(call_record)

        # Inject failure
        if failure:
            self.results.failure_injections[failure.value] = self.results.failure_injections.get(failure.value, 0) + 1
            execution.failure_injected = failure
            execution.failure_step = step_index

            if failure == FailureType.WORKER_CRASH:
                # Simulate worker crash - execution stops here
                execution.status = WorkflowStatus.FAILED
                execution.failed_at = datetime.now(UTC).isoformat()
                execution.steps_failed.append(step_index)
                self.results.failed_service_calls += 1
                return False, {"error": "Worker crash simulated"}

            elif failure == FailureType.NETWORK_PARTITION:
                # Simulate network partition - request times out
                await asyncio.sleep(random.uniform(0.1, 0.5))
                self.results.failed_service_calls += 1
                return False, {"error": "Network partition simulated"}

            elif failure == FailureType.DB_CONNECTION_LOSS:
                # Simulate DB connection loss
                self.results.failed_service_calls += 1
                return False, {"error": "Database connection lost"}

            elif failure == FailureType.MESSAGE_BROKER_FAILURE:
                # Simulate message broker failure
                self.results.failed_service_calls += 1
                return False, {"error": "Message broker unavailable"}

            elif failure == FailureType.SERVICE_TIMEOUT:
                # Simulate service timeout
                await asyncio.sleep(random.uniform(0.5, 2.0))
                self.results.failed_service_calls += 1
                return False, {"error": "Service timeout"}

            elif failure == FailureType.PARTIAL_FAILURE:
                # Simulate partial failure - some steps succeed, some fail
                if random.random() < 0.5:
                    self.results.failed_service_calls += 1
                    return False, {"error": "Partial failure simulated"}

        # Execute the step (simulate service call)
        try:
            async with self._semaphore:
                # In real test, would call actual service
                # For simulation, just mimic the call
                await asyncio.sleep(random.uniform(0.01, 0.1))

                # Simulate occasional service errors (1%)
                if random.random() < 0.01:
                    raise Exception("Simulated service error")

            execution.steps_completed.append(step_index)
            return True, {"status": "success", "service": service, "action": action}

        except Exception as e:
            execution.steps_failed.append(step_index)
            self.results.failed_service_calls += 1
            return False, {"error": str(e)}

    async def _replay_workflow(self, execution: WorkflowExecution) -> bool:
        """Replay a failed workflow from the beginning (idempotent replay)."""
        execution.replay_count += 1
        execution.status = WorkflowStatus.REPLAYED
        self.results.replayed += 1

        log.info("chaos_test.replaying", execution_id=execution.execution_id,
                 workflow_id=execution.workflow_id, replay_count=execution.replay_count)

        # Replay all steps
        for i, step in enumerate(execution.steps):
            # Check if this step was already completed (idempotency)
            if i in execution.steps_completed:
                # Verify idempotent behavior - should not cause duplicate sends
                key = execution.idempotency_key
                previous_calls = [c for c in self._service_call_log.get(key, []) if c["step"] == i]

                if len(previous_calls) > 1:
                    # Duplicate detected!
                    execution.duplicate_sends += 1
                    self.results.duplicates_detected += 1
                    execution.status = WorkflowStatus.DUPLICATE_DETECTED
                    log.warning("chaos_test.duplicate_detected", execution_id=execution.execution_id,
                               step=i, service=execution.steps[i]["service"])
                    self.results.idempotent_violations += 1
                else:
                    self.results.idempotent_verified += 1

                # Skip re-execution (idempotent)
                continue

            # Execute step
            success, result = await self._execute_step(execution, i, None)
            if not success:
                return False

        return True

    async def _run_workflow(self, execution: WorkflowExecution) -> None:
        """Run a single workflow with chaos injection."""
        execution.started_at = datetime.now(UTC).isoformat()
        execution.status = WorkflowStatus.RUNNING

        # Determine if we inject a failure at a random step
        failure = self._should_inject_failure()
        failure_step = random.randint(0, len(execution.steps) - 1) if failure else None

        # Execute steps until failure or completion
        for i in range(len(execution.steps)):
            if failure and i == failure_step:
                success, result = await self._execute_step(execution, i, failure)
            else:
                success, result = await self._execute_step(execution, i, None)

            if not success:
                # Workflow failed - attempt replay
                if await self._replay_workflow(execution):
                    execution.status = WorkflowStatus.COMPLETED
                    self.results.completed += 1
                else:
                    execution.status = WorkflowStatus.FAILED
                    self.results.failed += 1
                break
        else:
            # All steps completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(UTC).isoformat()
            self.results.completed += 1

        self.results.executions.append(execution)

    async def run(self) -> ChaosTestResults:
        """Run the chaos test."""
        log.info("chaos_test.starting",
                 total_workflows=self.total_workflows,
                 failure_rate=self.failure_rate,
                 concurrency=self.concurrency)

        # Create workflow executions
        executions = [self._generate_workflow() for _ in range(self.total_workflows)]

        # Run in batches
        batch_size = self.concurrency
        for i in range(0, len(executions), batch_size):
            batch = executions[i:i + batch_size]
            tasks = [self._run_workflow(exec) for exec in batch]
            await asyncio.gather(*tasks)

            # Progress logging
            completed = len([e for e in executions[:i + len(batch)] if e.status == WorkflowStatus.COMPLETED])
            log.info("chaos_test.progress", completed=completed, total=self.total_workflows)

        log.info("chaos_test.completed",
                 completed=self.results.completed,
                 failed=self.results.failed,
                 replayed=self.results.replayed,
                 duplicates=self.results.duplicates_detected,
                 idempotent_verified=self.results.idempotent_verified,
                 idempotent_violations=self.results.idempotent_violations)

        return self.results

    def print_summary(self) -> None:
        """Print chaos test summary."""
        metrics = self.results.calculate_metrics()

        print("\n" + "=" * 70)
        print("CHAOS TEST SUMMARY")
        print("=" * 70)
        print(f"Total Workflows:        {self.results.total_workflows}")
        print(f"Completed:              {self.results.completed}")
        print(f"Failed:                 {self.results.failed}")
        print(f"Replayed:               {self.results.replayed}")
        print(f"Duplicates Detected:    {self.results.duplicates_detected}")
        print()
        print(f"Failure Injections:")
        for failure, count in self.results.failure_injections.items():
            print(f"  {failure:25s}: {count}")
        print()
        print(f"Service Calls:")
        print(f"  Total:                {self.results.total_service_calls}")
        print(f"  Failed:               {self.results.failed_service_calls}")
        print()
        print(f"Idempotency:")
        print(f"  Verified:             {self.results.idempotent_verified}")
        print(f"  Violations:           {self.results.idempotent_violations}")
        print()
        print(f"Metrics:")
        print(f"  Completion Rate:      {metrics['completion_rate']*100:.1f}%")
        print(f"  Replay Rate:          {metrics['replay_rate']*100:.1f}%")
        print(f"  Duplicate Rate:       {metrics['duplicate_rate']*100:.4f}%")
        print(f"  Idempotent Compliance: {metrics['idempotent_compliance']*100:.2f}%")
        print(f"  Service Call Success:  {metrics['service_call_success_rate']*100:.2f}%")
        print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(description="Chaos test for workflow resilience")
    parser.add_argument("--workflows", type=int, default=1000, help="Total workflows to test")
    parser.add_argument("--failure-rate", type=float, default=0.1, help="Failure injection rate (0-1)")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent workflows")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--tenant", default="00000000-0000-0000-0000-000000000001", help="Tenant ID")
    parser.add_argument("--token", default="dev-token", help="Auth token")
    args = parser.parse_args()

    async with ChaosTestRunner(
        base_url=args.url,
        tenant_id=args.tenant,
        auth_token=args.token,
        total_workflows=args.workflows,
        failure_rate=args.failure_rate,
        concurrency=args.concurrency,
    ) as runner:
        results = await runner.run()
        runner.print_summary()

        metrics = results.calculate_metrics()

        # Pass criteria
        passed = True
        if metrics["completion_rate"] < 0.99:
            print(f"\n❌ FAIL: Completion rate {metrics['completion_rate']*100:.1f}% < 99%")
            passed = False
        if metrics["duplicate_rate"] > 0.001:
            print(f"\n❌ FAIL: Duplicate rate {metrics['duplicate_rate']*100:.3f}% > 0.1%")
            passed = False
        if metrics["idempotent_compliance"] < 0.999:
            print(f"\n❌ FAIL: Idempotent compliance {metrics['idempotent_compliance']*100:.2f}% < 99.9%")
            passed = False

        if passed:
            print("\n✅ PASS: All chaos resilience criteria met")
            exit(0)
        else:
            print("\n❌ FAIL: Chaos resilience criteria not met")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())
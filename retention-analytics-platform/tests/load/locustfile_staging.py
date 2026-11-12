"""Staging load test: 100 users, 5 min ramp.

Run against staging:
    locust -f tests/load/locustfile_staging.py --headless -u 100 -r 10 -t 5m --host https://staging.example.com
"""

from __future__ import annotations

import uuid

from locust import HttpUser, between, task


class StagingUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.headers = {
            "Authorization": f"Bearer {self.environment.parsed_options.api_token or 'dev-token'}",
        }

    @task(5)
    def health(self) -> None:
        self.client.get("/health", headers=self.headers)

    @task(3)
    def list_services(self) -> None:
        self.client.get("/api/v1/services", headers=self.headers)

    @task(3)
    def list_workflows(self) -> None:
        self.client.get("/api/v1/workflows", headers=self.headers)

    @task(2)
    def run_workflow(self) -> None:
        self.client.post(
            "/api/v1/workflows/churn-prevention/run",
            json={"context": {"email": f"load-{uuid.uuid4().hex[:6]}@test.com"}},
            headers=self.headers,
        )

    @task(2)
    def ingest_event(self) -> None:
        self.client.post(
            "/api/v1/events",
            json={
                "type": "client.churn_risk",
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "idempotency_key": f"load-{uuid.uuid4().hex}",
                "payload": {"client_email": f"load-{uuid.uuid4().hex[:6]}@test.com"},
            },
            headers=self.headers,
        )

    @task(1)
    def metrics(self) -> None:
        self.client.get("/metrics")

    @task(1)
    def feature_flag(self) -> None:
        self.client.get("/api/v1/feature-flags/load-test", headers=self.headers)

    @task(1)
    def report(self) -> None:
        self.client.post("/api/v1/reports?format=json", headers=self.headers)

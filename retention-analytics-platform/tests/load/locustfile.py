"""Locust load test for the retention analytics API.

Smoke-level: 10 users, 10s. Run with:
    locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 10s --host http://localhost:47319
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class PlatformUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.headers = {"Authorization": "Bearer " + os.environ.get("API_TOKEN", "dev-token")}

    @task(3)
    def health(self) -> None:
        self.client.get("/health", headers=self.headers)

    @task(2)
    def list_services(self) -> None:
        self.client.get("/api/v1/services", headers=self.headers)

    @task(2)
    def list_workflows(self) -> None:
        self.client.get("/api/v1/workflows", headers=self.headers)

    @task(1)
    def run_workflow(self) -> None:
        self.client.post(
            "/api/v1/workflows/churn-prevention/run",
            json={},
            headers=self.headers,
        )

    @task(1)
    def metrics(self) -> None:
        self.client.get("/metrics")

    @task(1)
    def feature_flag(self) -> None:
        self.client.get("/api/v1/feature-flags/load-test", headers=self.headers)

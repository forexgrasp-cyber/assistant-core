#!/usr/bin/env python3
"""
Cost Model: Measure infra cost per 1M events / 1k active workflows

Analyzes infrastructure costs at scale:
1. Event ingestion pipeline costs
2. Workflow execution costs
3. Service compute costs
4. Storage costs
5. Network/egress costs
6. Total cost per unit metrics

Usage:
    python scripts/cost_model.py --events-per-month 1000000 --workflows-per-month 1000
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InfrastructureConfig:
    """Infrastructure configuration for cost modeling."""
    # Compute
    api_instances: int = 3
    api_instance_type: str = "c6i.xlarge"  # 4 vCPU, 8 GB
    api_hourly_cost: float = 0.134  # us-east-1 on-demand

    worker_instances: int = 10
    worker_instance_type: str = "c6i.2xlarge"  # 8 vCPU, 16 GB
    worker_hourly_cost: float = 0.268

    # Database
    db_instance_type: str = "db.r6g.2xlarge"  # 8 vCPU, 64 GB
    db_hourly_cost: float = 0.544
    db_storage_gb: int = 500
    db_storage_cost_per_gb: float = 0.115

    # Cache
    cache_instance_type: str = "cache.r6g.xlarge"  # 4 vCPU, 13 GB
    cache_hourly_cost: float = 0.176
    cache_nodes: int = 2

    # Message Queue
    mq_instance_type: str = "mq.m5.large"  # 2 vCPU, 8 GB
    mq_hourly_cost: float = 0.192
    mq_broker_count: int = 2

    # Storage
    object_storage_gb: int = 1000
    object_storage_cost_per_gb: float = 0.023
    object_storage_requests_per_million: int = 10
    object_storage_request_cost: float = 0.0004

    # Network
    egress_gb_per_month: int = 500
    egress_cost_per_gb: float = 0.09

    # Monitoring
    monitoring_cost_per_month: float = 500

    # CDN
    cdn_gb_per_month: int = 200
    cdn_cost_per_gb: float = 0.085


@dataclass
class WorkloadProfile:
    """Workload profile for cost modeling."""
    events_per_month: int = 1_000_000
    workflows_per_month: int = 1_000
    avg_steps_per_workflow: int = 4
    avg_event_size_kb: float = 2.5
    avg_workflow_duration_seconds: float = 5.0
    peak_multiplier: float = 3.0  # Peak vs average traffic
    retention_days: int = 90


@dataclass
class CostBreakdown:
    """Cost breakdown by category."""
    compute: float = 0.0
    database: float = 0.0
    cache: float = 0.0
    messaging: float = 0.0
    storage: float = 0.0
    network: float = 0.0
    monitoring: float = 0.0
    cdn: float = 0.0
    total: float = 0.0

    def calculate_totals(self) -> None:
        self.total = (self.compute + self.database + self.cache + self.messaging +
                      self.storage + self.network + self.monitoring + self.cdn)


class CostModel:
    """Infrastructure cost model calculator."""

    def __init__(self, infra: InfrastructureConfig, workload: WorkloadProfile):
        self.infra = infra
        self.workload = workload
        self.costs = CostBreakdown()

    def calculate_compute_costs(self) -> float:
        """Calculate compute costs (API + Workers)."""
        hours_per_month = 730  # 30.44 days * 24

        # API instances (always running)
        api_cost = self.infra.api_instances * self.infra.api_hourly_cost * hours_per_month

        # Worker instances (scale with workload)
        # Base workers + peak scaling
        base_workers = max(2, self.infra.worker_instances // 3)
        peak_workers = self.infra.worker_instances
        # Average workers = base + (peak - base) / peak_multiplier
        avg_workers = base_workers + (peak_workers - base_workers) / self.workload.peak_multiplier
        worker_cost = avg_workers * self.infra.worker_hourly_cost * hours_per_month

        self.costs.compute = api_cost + worker_cost
        return self.costs.compute

    def calculate_database_costs(self) -> float:
        """Calculate database costs."""
        hours_per_month = 730

        # Primary + read replica
        db_compute = 2 * self.infra.db_hourly_cost * hours_per_month
        db_storage = self.infra.db_storage_gb * self.infra.db_storage_cost_per_gb

        self.costs.database = db_compute + db_storage
        return self.costs.database

    def calculate_cache_costs(self) -> float:
        """Calculate cache (Redis) costs."""
        hours_per_month = 730
        self.costs.cache = self.infra.cache_nodes * self.infra.cache_hourly_cost * hours_per_month
        return self.costs.cache

    def calculate_messaging_costs(self) -> float:
        """Calculate message queue costs."""
        hours_per_month = 730
        self.costs.messaging = self.infra.mq_broker_count * self.infra.mq_hourly_cost * hours_per_month
        return self.costs.messaging

    def calculate_storage_costs(self) -> float:
        """Calculate object storage costs."""
        # Event storage
        event_storage_gb = (self.workload.events_per_month * self.workload.avg_event_size_kb) / (1024 * 1024)
        event_storage_gb *= self.workload.retention_days / 30  # Monthly equivalent

        # Workflow execution logs
        workflow_logs_gb = (self.workload.workflows_per_month *
                            self.workload.avg_steps_per_workflow * 1) / 1024  # ~1KB per step

        total_storage_gb = self.infra.object_storage_gb + event_storage_gb + workflow_logs_gb
        storage_cost = total_storage_gb * self.infra.object_storage_cost_per_gb

        # Request costs
        total_requests = (self.workload.events_per_month +
                          self.workload.workflows_per_month * self.workload.avg_steps_per_workflow)
        request_cost = (total_requests / 1_000_000) * self.infra.object_storage_request_cost

        self.costs.storage = storage_cost + request_cost
        return self.costs.storage

    def calculate_network_costs(self) -> float:
        """Calculate network/egress costs."""
        # API egress + webhook delivery + inter-service
        self.costs.network = self.infra.egress_gb_per_month * self.infra.egress_cost_per_gb
        return self.costs.network

    def calculate_monitoring_costs(self) -> float:
        """Calculate monitoring costs."""
        self.costs.monitoring = self.infra.monitoring_cost_per_month
        return self.costs.monitoring

    def calculate_cdn_costs(self) -> float:
        """Calculate CDN costs."""
        self.costs.cdn = self.infra.cdn_gb_per_month * self.infra.cdn_cost_per_gb
        return self.costs.cdn

    def calculate_all(self) -> CostBreakdown:
        """Calculate all costs."""
        self.calculate_compute_costs()
        self.calculate_database_costs()
        self.calculate_cache_costs()
        self.calculate_messaging_costs()
        self.calculate_storage_costs()
        self.calculate_network_costs()
        self.calculate_monitoring_costs()
        self.calculate_cdn_costs()
        self.costs.calculate_totals()
        return self.costs

    def calculate_unit_costs(self) -> dict[str, float]:
        """Calculate cost per unit metrics."""
        total = self.costs.total
        events = self.workload.events_per_month
        workflows = self.workload.workflows_per_month

        return {
            "cost_per_million_events": (total / events) * 1_000_000 if events > 0 else 0,
            "cost_per_thousand_workflows": (total / workflows) * 1_000 if workflows > 0 else 0,
            "cost_per_event": total / events if events > 0 else 0,
            "cost_per_workflow": total / workflows if workflows > 0 else 0,
            "compute_per_million_events": (self.costs.compute / events) * 1_000_000 if events > 0 else 0,
            "db_per_million_events": (self.costs.database / events) * 1_000_000 if events > 0 else 0,
        }

    def print_breakdown(self) -> None:
        """Print cost breakdown."""
        print("\n" + "=" * 70)
        print("INFRASTRUCTURE COST MODEL")
        print("=" * 70)
        print(f"Workload Profile:")
        print(f"  Events/Month:         {self.workload.events_per_month:,}")
        print(f"  Workflows/Month:      {self.workload.workflows_per_month:,}")
        print(f"  Avg Steps/Workflow:   {self.workload.avg_steps_per_workflow}")
        print(f"  Peak Multiplier:      {self.workload.peak_multiplier}x")
        print(f"  Retention:            {self.workload.retention_days} days")
        print()

        print("Monthly Cost Breakdown:")
        print(f"  Compute (API + Workers):    ${self.costs.compute:>10.2f}")
        print(f"  Database (Primary + Replica): ${self.costs.database:>10.2f}")
        print(f"  Cache (Redis):              ${self.costs.cache:>10.2f}")
        print(f"  Message Queue:              ${self.costs.messaging:>10.2f}")
        print(f"  Object Storage:             ${self.costs.storage:>10.2f}")
        print(f"  Network/Egress:             ${self.costs.network:>10.2f}")
        print(f"  Monitoring:                 ${self.costs.monitoring:>10.2f}")
        print(f"  CDN:                        ${self.costs.cdn:>10.2f}")
        print(f"  {'TOTAL':<30} ${self.costs.total:>10.2f}")
        print()

        unit_costs = self.calculate_unit_costs()
        print("Unit Costs:")
        print(f"  Cost per 1M Events:      ${unit_costs['cost_per_million_events']:>10.2f}")
        print(f"  Cost per 1K Workflows:   ${unit_costs['cost_per_thousand_workflows']:>10.2f}")
        print(f"  Cost per Event:          ${unit_costs['cost_per_event']:>10.6f}")
        print(f"  Cost per Workflow:       ${unit_costs['cost_per_workflow']:>10.4f}")
        print()
        print("Component Cost per 1M Events:")
        print(f"  Compute:                 ${unit_costs['compute_per_million_events']:>10.2f}")
        print(f"  Database:                ${unit_costs['db_per_million_events']:>10.2f}")
        print()

        # Cost distribution
        print("Cost Distribution:")
        for name, cost in [
            ("Compute", self.costs.compute),
            ("Database", self.costs.database),
            ("Cache", self.costs.cache),
            ("Messaging", self.costs.messaging),
            ("Storage", self.costs.storage),
            ("Network", self.costs.network),
            ("Monitoring", self.costs.monitoring),
            ("CDN", self.costs.cdn),
        ]:
            pct = (cost / self.costs.total * 100) if self.costs.total > 0 else 0
            print(f"  {name:<15}: ${cost:>10.2f} ({pct:>5.1f}%)")
        print("=" * 70)

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary."""
        unit_costs = self.calculate_unit_costs()
        return {
            "workload": {
                "events_per_month": self.workload.events_per_month,
                "workflows_per_month": self.workload.workflows_per_month,
                "avg_steps_per_workflow": self.workload.avg_steps_per_workflow,
                "peak_multiplier": self.workload.peak_multiplier,
                "retention_days": self.workload.retention_days,
            },
            "monthly_costs": {
                "compute": self.costs.compute,
                "database": self.costs.database,
                "cache": self.costs.cache,
                "messaging": self.costs.messaging,
                "storage": self.costs.storage,
                "network": self.costs.network,
                "monitoring": self.costs.monitoring,
                "cdn": self.costs.cdn,
                "total": self.costs.total,
            },
            "unit_costs": unit_costs,
            "cost_distribution": {
                name: (cost / self.costs.total * 100) if self.costs.total > 0 else 0
                for name, cost in [
                    ("compute", self.costs.compute),
                    ("database", self.costs.database),
                    ("cache", self.costs.cache),
                    ("messaging", self.costs.messaging),
                    ("storage", self.costs.storage),
                    ("network", self.costs.network),
                    ("monitoring", self.costs.monitoring),
                    ("cdn", self.costs.cdn),
                ]
            },
        }


def main():
    parser = argparse.ArgumentParser(description="Infrastructure cost model")
    parser.add_argument("--events", type=int, default=1_000_000, help="Events per month")
    parser.add_argument("--workflows", type=int, default=1_000, help="Workflows per month")
    parser.add_argument("--steps", type=int, default=4, help="Avg steps per workflow")
    parser.add_argument("--peak", type=float, default=3.0, help="Peak multiplier")
    parser.add_argument("--retention", type=int, default=90, help="Retention days")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    infra = InfrastructureConfig()
    workload = WorkloadProfile(
        events_per_month=args.events,
        workflows_per_month=args.workflows,
        avg_steps_per_workflow=args.steps,
        peak_multiplier=args.peak,
        retention_days=args.retention,
    )

    model = CostModel(infra, workload)
    model.calculate_all()
    model.print_breakdown()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(model.to_dict(), f, indent=2)
        print(f"\nResults saved to {args.output}")

    # Check against thresholds
    unit_costs = model.calculate_unit_costs()
    cost_per_m = unit_costs["cost_per_million_events"]
    cost_per_k_wf = unit_costs["cost_per_thousand_workflows"]

    print(f"\nCost Targets:")
    print(f"  Target: <$500 per 1M events  | Actual: ${cost_per_m:.2f}  | {'PASS' if cost_per_m < 500 else 'FAIL'}")
    print(f"  Target: <$100 per 1K workflows | Actual: ${cost_per_k_wf:.2f}  | {'PASS' if cost_per_k_wf < 100 else 'FAIL'}")


if __name__ == "__main__":
    main()
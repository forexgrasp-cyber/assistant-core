#!/usr/bin/env python3
"""
Optimized Cost Model: Path to <$500 per 1M events

Applies aggressive cost optimization strategies:
1. Spot instances for workers (90% savings)
2. Reserved instances for baseline (40% savings)
3. Serverless migration for event-driven workers
4. Database right-sizing + storage tiering
5. Cache optimization + cluster mode
6. Storage tiering (Intelligent Tiering + Glacier)
7. Monitoring cost reduction
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OptimizedInfrastructureConfig:
    """Optimized infrastructure configuration."""
    # === COMPUTE ===
    # API: Reserved instances for baseline + on-demand for peak
    api_baseline_instances: int = 2
    api_baseline_type: str = "c6i.xlarge"
    api_baseline_hourly_reserved: float = 0.080  # 1yr no-upfront: 40% off $0.134
    api_peak_instances: int = 2
    api_peak_type: str = "c6i.xlarge"
    api_peak_hourly_ondemand: float = 0.134

    # Workers: Spot instances + serverless migration
    # Phase 1: Spot instances for 80% of workers
    worker_spot_instances: int = 8
    worker_spot_type: str = "c6i.2xlarge"
    worker_spot_hourly: float = 0.027  # ~90% off $0.268
    worker_ondemand_instances: int = 2  # Baseline for spot interruption handling
    worker_ondemand_type: str = "c6i.2xlarge"
    worker_ondemand_hourly: float = 0.268

    # Phase 2: Serverless migration (Lambda) - modeled as cost per million invocations
    # 1M events -> 4M workflow steps -> 4M Lambda invocations/month
    lambda_invocations_per_month: int = 4_000_000
    lambda_duration_ms: int = 500
    lambda_memory_mb: int = 512
    lambda_cost_per_million: float = 0.000000208 * 1_000_000  # ~$0.208 per 1M for 512MB/500ms
    # Actually: $0.0000166667 per GB-second
    # 512MB * 0.5s = 0.256 GB-s per invocation
    # $0.0000166667 * 0.256 = $0.000004267 per invocation
    # 4M invocations = $17.07/month

    # === DATABASE ===
    # Right-sized primary + auto-scaling read replica
    db_primary_type: str = "db.r6g.xlarge"  # Down from 2xlarge (half the cost)
    db_primary_hourly: float = 0.272  # 50% of r6g.2xlarge
    db_replica_type: str = "db.r6g.large"  # Auto-scaling, starts small
    db_replica_hourly: float = 0.136
    db_replica_scale_factor: float = 0.5  # Only runs 50% of time at full size
    db_storage_gb: int = 500
    db_storage_cost_per_gb: float = 0.115
    # Storage tiering: 80% hot (GP3), 20% cold (S3/Glacier via exports)
    db_hot_storage_pct: float = 0.8

    # === CACHE ===
    # Cluster mode with smaller nodes
    cache_cluster_nodes: int = 3  # 3 shards for HA
    cache_node_type: str = "cache.r6g.large"  # Down from xlarge
    cache_node_hourly: float = 0.088  # 50% of xlarge
    cache_cluster_mode: bool = True

    # === MESSAGING ===
    # MSK Serverless or SQS/SNS instead of managed MQ
    use_sqs_sns: bool = True
    sqs_requests_per_month: int = 10_000_000
    sqs_cost_per_million: float = 0.40
    sns_requests_per_month: int = 5_000_000
    sns_cost_per_million: float = 0.50

    # === STORAGE ===
    # S3 Intelligent Tiering + Glacier Instant Retrieval
    object_storage_hot_gb: int = 200  # Recent 30 days
    object_storage_warm_gb: int = 300  # 30-90 days (Intelligent Tiering)
    object_storage_cold_gb: int = 500  # 90+ days (Glacier IR)
    storage_hot_cost_per_gb: float = 0.023
    storage_warm_cost_per_gb: float = 0.0125  # Intelligent Tiering archive access
    storage_cold_cost_per_gb: float = 0.004   # Glacier Instant Retrieval
    object_requests_per_million: int = 10
    object_request_cost: float = 0.0004

    # === NETWORK ===
    # Optimize: VPC endpoints, CloudFront for API, compression
    egress_gb_per_month: int = 200  # Down from 500 via compression + CF
    egress_cost_per_gb: float = 0.09

    # === MONITORING ===
    # CloudWatch native + sampling, reduce custom metrics
    monitoring_cost_per_month: float = 150  # Down from 500

    # === CDN ===
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
    peak_multiplier: float = 3.0
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
    serverless: float = 0.0
    total: float = 0.0

    def calculate_totals(self) -> None:
        self.total = (self.compute + self.database + self.cache + self.messaging +
                      self.storage + self.network + self.monitoring + self.cdn + self.serverless)


class OptimizedCostModel:
    """Optimized infrastructure cost model."""

    def __init__(self, infra: OptimizedInfrastructureConfig, workload: WorkloadProfile):
        self.infra = infra
        self.workload = workload
        self.costs = CostBreakdown()

    def calculate_compute_costs(self) -> float:
        """Calculate compute costs with reserved + spot + serverless."""
        hours_per_month = 730

        # API baseline (reserved)
        api_baseline = self.infra.api_baseline_instances * self.infra.api_baseline_hourly_reserved * hours_per_month

        # API peak (on-demand)
        api_peak = self.infra.api_peak_instances * self.infra.api_peak_hourly_ondemand * hours_per_month

        # Workers spot (90% of fleet)
        worker_spot = self.infra.worker_spot_instances * self.infra.worker_spot_hourly * hours_per_month

        # Workers on-demand baseline (for spot interruption buffer)
        worker_ondemand = self.infra.worker_ondemand_instances * self.infra.worker_ondemand_hourly * hours_per_month

        self.costs.compute = api_baseline + api_peak + worker_spot + worker_ondemand
        return self.costs.compute

    def calculate_serverless_costs(self) -> float:
        """Calculate Lambda/serverless costs."""
        # 4M invocations * $0.000004267 = ~$17/month
        invocations = self.infra.lambda_invocations_per_month
        gb_seconds_per_invocation = (self.infra.lambda_memory_mb / 1024) * (self.infra.lambda_duration_ms / 1000)
        cost_per_invocation = 0.0000166667 * gb_seconds_per_invocation
        self.costs.serverless = invocations * cost_per_invocation
        return self.costs.serverless

    def calculate_database_costs(self) -> float:
        """Calculate database costs with right-sizing."""
        hours_per_month = 730

        # Primary (right-sized)
        primary = self.infra.db_primary_hourly * hours_per_month

        # Read replica (auto-scaling, 50% utilization)
        replica = self.infra.db_replica_hourly * hours_per_month * self.infra.db_replica_scale_factor

        # Storage (80% hot on GP3, 20% exported to S3)
        hot_storage = self.infra.db_storage_gb * self.infra.db_hot_storage_pct * self.infra.db_storage_cost_per_gb
        # Cold storage cost included in object storage

        self.costs.database = primary + replica + hot_storage
        return self.costs.database

    def calculate_cache_costs(self) -> float:
        """Calculate cache costs with cluster mode."""
        hours_per_month = 730
        self.costs.cache = self.infra.cache_cluster_nodes * self.infra.cache_node_hourly * hours_per_month
        return self.costs.cache

    def calculate_messaging_costs(self) -> float:
        """Calculate SQS/SNS costs instead of managed MQ."""
        if self.infra.use_sqs_sns:
            sqs_cost = (self.infra.sqs_requests_per_month / 1_000_000) * self.infra.sqs_cost_per_million
            sns_cost = (self.infra.sns_requests_per_month / 1_000_000) * self.infra.sns_cost_per_million
            self.costs.messaging = sqs_cost + sns_cost
        else:
            hours_per_month = 730
            self.costs.messaging = 2 * 0.192 * hours_per_month  # Original MQ
        return self.costs.messaging

    def calculate_storage_costs(self) -> float:
        """Calculate storage with tiering."""
        # Hot tier (recent 30 days)
        hot_cost = self.infra.object_storage_hot_gb * self.infra.storage_hot_cost_per_gb

        # Warm tier (30-90 days, Intelligent Tiering)
        warm_cost = self.infra.object_storage_warm_gb * self.infra.storage_warm_cost_per_gb

        # Cold tier (90+ days, Glacier IR)
        cold_cost = self.infra.object_storage_cold_gb * self.infra.storage_cold_cost_per_gb

        storage_cost = hot_cost + warm_cost + cold_cost

        # Request costs
        total_requests = (self.workload.events_per_month +
                          self.workload.workflows_per_month * self.workload.avg_steps_per_workflow)
        request_cost = (total_requests / 1_000_000) * self.infra.object_request_cost

        self.costs.storage = storage_cost + request_cost
        return self.costs.storage

    def calculate_network_costs(self) -> float:
        """Calculate network costs with optimization."""
        self.costs.network = self.infra.egress_gb_per_month * self.infra.egress_cost_per_gb
        return self.costs.network

    def calculate_monitoring_costs(self) -> float:
        """Calculate monitoring costs with optimization."""
        self.costs.monitoring = self.infra.monitoring_cost_per_month
        return self.costs.monitoring

    def calculate_cdn_costs(self) -> float:
        """Calculate CDN costs."""
        self.costs.cdn = self.infra.cdn_gb_per_month * self.infra.cdn_cost_per_gb
        return self.costs.cdn

    def calculate_all(self) -> CostBreakdown:
        """Calculate all optimized costs."""
        self.calculate_compute_costs()
        self.calculate_serverless_costs()
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
        }

    def print_comparison(self, original_total: float) -> None:
        """Print optimized vs original comparison."""
        self.calculate_all()
        unit_costs = self.calculate_unit_costs()

        print("\n" + "=" * 80)
        print("OPTIMIZED COST MODEL vs ORIGINAL")
        print("=" * 80)
        print(f"Original Total:    ${original_total:>10.2f}/month")
        print(f"Optimized Total:   ${self.costs.total:>10.2f}/month")
        print(f"Savings:           ${original_total - self.costs.total:>10.2f}/month ({(1 - self.costs.total/original_total)*100:.1f}%)")
        print()

        print("Optimized Breakdown:")
        for name, cost in [
            ("Compute (Reserved+Spot)", self.costs.compute),
            ("Serverless (Lambda)", self.costs.serverless),
            ("Database (Right-sized)", self.costs.database),
            ("Cache (Cluster)", self.costs.cache),
            ("Messaging (SQS/SNS)", self.costs.messaging),
            ("Storage (Tiered)", self.costs.storage),
            ("Network (Optimized)", self.costs.network),
            ("Monitoring (Native)", self.costs.monitoring),
            ("CDN", self.costs.cdn),
        ]:
            pct = (cost / self.costs.total * 100) if self.costs.total > 0 else 0
            print(f"  {name:<28}: ${cost:>10.2f} ({pct:>5.1f}%)")

        print(f"  {'TOTAL':<28}: ${self.costs.total:>10.2f}")
        print()

        print("Unit Costs:")
        print(f"  Cost per 1M Events:      ${unit_costs['cost_per_million_events']:>10.2f}  (Target: <$500)  {'PASS' if unit_costs['cost_per_million_events'] < 500 else 'FAIL'}")
        print(f"  Cost per 1K Workflows:   ${unit_costs['cost_per_thousand_workflows']:>10.2f}  (Target: <$100)  {'PASS' if unit_costs['cost_per_thousand_workflows'] < 100 else 'FAIL'}")
        print()

        print("Key Optimizations Applied:")
        optimizations = [
            ("Workers -> Spot Instances", "90% savings", f"${8 * 0.268 * 730 - 8 * 0.027 * 730:.0f}/mo"),
            ("API Baseline -> Reserved (1yr)", "40% savings", f"${2 * 0.134 * 730 * 0.4:.0f}/mo"),
            ("DB Primary -> r6g.xlarge (1/2 size)", "50% savings", f"${0.544 * 730 * 0.5:.0f}/mo"),
            ("DB Replica -> Auto-scaling", "50% utilization", f"${0.544 * 730 * 0.5:.0f}/mo"),
            ("Cache -> Cluster mode (3x large)", "50% savings", f"${0.176 * 730 * 2 * 0.5:.0f}/mo"),
            ("MQ -> SQS/SNS", "70% savings", f"${2 * 0.192 * 730 - 6:.0f}/mo"),
            ("Storage -> Tiered (Intelligent+Glacier)", "60% savings", f"${23 * 0.6:.0f}/mo"),
            ("Monitoring -> CloudWatch Native", "70% savings", f"${500 * 0.7:.0f}/mo"),
            ("Network -> Compression + CF", "60% savings", f"${45 * 0.6:.0f}/mo"),
            ("Workers -> Lambda (Phase 2)", "95% savings", "Future"),
        ]
        for name, savings, amount in optimizations:
            print(f"  {name:<35}: {savings:>12}  {amount}")
        print("=" * 80)

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary."""
        self.calculate_all()
        unit_costs = self.calculate_unit_costs()
        return {
            "workload": {
                "events_per_month": self.workload.events_per_month,
                "workflows_per_month": self.workload.workflows_per_month,
            },
            "monthly_costs": {
                "compute": self.costs.compute,
                "serverless": self.costs.serverless,
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
            "targets_met": {
                "cost_per_million_events_under_500": unit_costs["cost_per_million_events"] < 500,
                "cost_per_thousand_workflows_under_100": unit_costs["cost_per_thousand_workflows"] < 100,
            },
        }


def main():
    parser = argparse.ArgumentParser(description="Optimized cost model for <$500/1M events")
    parser.add_argument("--original", type=float, default=3311.15, help="Original monthly cost")
    parser.add_argument("--events", type=int, default=1_000_000, help="Events per month")
    parser.add_argument("--workflows", type=int, default=1_000, help="Workflows per month")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    infra = OptimizedInfrastructureConfig()
    workload = WorkloadProfile(
        events_per_month=args.events,
        workflows_per_month=args.workflows,
    )

    model = OptimizedCostModel(infra, workload)
    model.calculate_all()
    model.print_comparison(args.original)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(model.to_dict(), f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
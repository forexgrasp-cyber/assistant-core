#!/usr/bin/env python3
"""
Accuracy Benchmark: Seed known conversion data → run attribution → compare to ground truth

Tests multi-touch attribution accuracy against known ground truth:
1. Seed synthetic customer journeys with known touchpoints and conversions
2. Run attribution with all 5 models (first_touch, last_touch, linear, time_decay, position_based)
3. Compare attributed revenue to ground truth
4. Report accuracy metrics per model

Usage:
    python scripts/accuracy_benchmark.py --customers 1000 --journeys-per-customer 5
"""

from __future__ import annotations

import argparse
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)


@dataclass
class GroundTruthJourney:
    """A customer journey with known ground truth attribution."""
    customer_id: str
    touches: list[dict[str, Any]]  # Ordered touchpoints
    conversion_value: float
    conversion_timestamp: str
    ground_truth: dict[str, float]  # channel -> true attributed revenue


@dataclass
class AttributionResult:
    """Attribution result from the platform."""
    customer_id: str
    model: str
    attributed: dict[str, float]  # channel -> attributed revenue
    touch_count: int


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a model."""
    model: str
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    correlation: float  # Pearson correlation
    channel_accuracy: dict[str, float]  # channel -> accuracy %
    total_customers: int


class AccuracyBenchmark:
    """Attribution accuracy benchmark runner."""

    def __init__(self, base_url: str, tenant_id: str, auth_token: str):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.auth_token = auth_token
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0),
            headers={"Authorization": f"Bearer {self.auth_token}"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def _generate_synthetic_journey(self, customer_id: str) -> GroundTruthJourney:
        """Generate a synthetic customer journey with known ground truth."""
        channels = ["email", "sms", "push", "ad", "referral", "direct", "organic_search"]
        touchpoints = ["impression", "click", "open", "visit", "form_submit"]
        campaigns = [f"campaign_{i}" for i in range(1, 21)]

        # Number of touches (1-8)
        num_touches = random.randint(1, 8)

        # Generate touches with timestamps
        base_time = datetime.now(UTC) - timedelta(days=random.randint(1, 90))
        touches = []
        total_weight = 0

        for i in range(num_touches):
            channel = random.choice(channels)
            touchpoint = random.choice(touchpoints)
            campaign = random.choice(campaigns)

            # Time decay: more recent touches get higher weight
            touch_time = base_time + timedelta(
                hours=random.randint(0, int((datetime.now(UTC) - base_time).total_seconds() / 3600))
            )

            # Ground truth weight based on position and recency
            position_weight = 1.0 / (i + 1)  # First touch gets more weight in position-based
            recency_weight = 1.0 / (num_touches - i)  # More recent gets more weight in time decay

            touches.append({
                "channel": channel,
                "touchpoint": touchpoint,
                "campaign_id": campaign,
                "timestamp": touch_time.isoformat(),
                "value": round(random.uniform(1, 100), 2),
                "ground_truth_weight": position_weight * recency_weight,
            })
            total_weight += position_weight * recency_weight

        # Normalize ground truth weights
        for touch in touches:
            touch["ground_truth_weight"] = touch["ground_truth_weight"] / total_weight

        # Conversion value
        conversion_value = round(random.uniform(50, 5000), 2)
        conversion_time = datetime.now(UTC).isoformat()

        # Calculate ground truth per channel
        ground_truth = {}
        for touch in touches:
            channel = touch["channel"]
            attributed = conversion_value * touch["ground_truth_weight"]
            ground_truth[channel] = round(ground_truth.get(channel, 0) + attributed, 2)

        return GroundTruthJourney(
            customer_id=customer_id,
            touches=touches,
            conversion_value=conversion_value,
            conversion_timestamp=conversion_time,
            ground_truth=ground_truth,
        )

    async def seed_journeys(self, journeys: list[GroundTruthJourney]) -> dict[str, Any]:
        """Seed journeys into the platform via attribution multitouch service."""
        seeded = 0
        errors = 0

        for journey in journeys:
            for touch in journey.touches:
                try:
                    response = await self.client.post(
                        "/api/v1/attribution/touch",
                        json={
                            "tenant_id": self.tenant_id,
                            "customer_id": journey.customer_id,
                            "channel": touch["channel"],
                            "campaign_id": touch["campaign_id"],
                            "touchpoint": touch["touchpoint"],
                            "value": touch["value"],
                            "at": touch["timestamp"],
                            "converted": False,
                        },
                    )
                    if response.status_code in (200, 201):
                        seeded += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

            # Mark last touch as converted
            if journey.touches:
                last_touch = journey.touches[-1]
                try:
                    response = await self.client.post(
                        "/api/v1/attribution/touch",
                        json={
                            "tenant_id": self.tenant_id,
                            "customer_id": journey.customer_id,
                            "channel": last_touch["channel"],
                            "campaign_id": last_touch["campaign_id"],
                            "touchpoint": last_touch["touchpoint"],
                            "value": journey.conversion_value,
                            "at": journey.conversion_timestamp,
                            "converted": True,
                        },
                    )
                    if response.status_code in (200, 201):
                        seeded += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        return {"seeded": seeded, "errors": errors}

    async def run_attribution(self, customer_id: str, model: str) -> AttributionResult | None:
        """Run attribution for a customer with a specific model."""
        try:
            response = await self.client.post(
                "/api/v1/attribution/multitouch",
                json={
                    "tenant_id": self.tenant_id,
                    "customer_id": customer_id,
                    "model": model,
                    "conversion_value": 1000,  # Will be overridden by actual conversion
                },
            )
            if response.status_code == 200:
                data = response.json()
                return AttributionResult(
                    customer_id=customer_id,
                    model=model,
                    attributed=data.get("by_channel", {}),
                    touch_count=data.get("touch_count", 0),
                )
        except Exception as e:
            log.error("attribution_failed", customer_id=customer_id, model=model, error=str(e))
        return None

    def calculate_accuracy(self, ground_truth: dict[str, float], attributed: dict[str, float]) -> tuple[float, float, float]:
        """Calculate MAPE, RMSE, and correlation between ground truth and attributed."""
        all_channels = set(ground_truth.keys()) | set(attributed.keys())
        if not all_channels:
            return 0.0, 0.0, 1.0

        gt_values = [ground_truth.get(c, 0) for c in all_channels]
        at_values = [attributed.get(c, 0) for c in all_channels]

        # MAPE
        mape_values = []
        for gt, at in zip(gt_values, at_values):
            if gt > 0:
                mape_values.append(abs(gt - at) / gt)
        mape = sum(mape_values) / len(mape_values) * 100 if mape_values else 0

        # RMSE
        mse = sum((gt - at) ** 2 for gt, at in zip(gt_values, at_values)) / len(gt_values)
        rmse = mse ** 0.5

        # Correlation (Pearson)
        n = len(gt_values)
        if n > 1:
            gt_mean = sum(gt_values) / n
            at_mean = sum(at_values) / n
            numerator = sum((gt - gt_mean) * (at - at_mean) for gt, at in zip(gt_values, at_values))
            gt_std = (sum((gt - gt_mean) ** 2 for gt in gt_values) / n) ** 0.5
            at_std = (sum((at - at_mean) ** 2 for at in at_values) / n) ** 0.5
            if gt_std > 0 and at_std > 0:
                correlation = numerator / (n * gt_std * at_std)
            else:
                correlation = 0.0
        else:
            correlation = 1.0 if gt_values == at_values else 0.0

        return mape, rmse, correlation

    async def run_benchmark(self, num_customers: int, journeys_per_customer: int) -> dict[str, AccuracyMetrics]:
        """Run the full accuracy benchmark."""
        log.info("benchmark.starting", customers=num_customers, journeys_per_customer=journeys_per_customer)

        # Generate ground truth journeys
        journeys = []
        for i in range(num_customers):
            customer_id = f"bench-cust-{uuid.uuid4().hex[:12]}"
            for j in range(journeys_per_customer):
                journey_id = f"{customer_id}-journey-{j}"
                journeys.append(self._generate_synthetic_journey(journey_id))

        log.info("benchmark.generated_journeys", count=len(journeys))

        # Seed journeys
        seed_result = await self.seed_journeys(journeys)
        log.info("benchmark.seeded", **seed_result)

        # Run attribution for each model
        models = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]
        results_by_model: dict[str, list[tuple[dict[str, float], dict[str, float]]]] = {m: [] for m in models}

        for journey in journeys:
            for model in models:
                result = await self.run_attribution(journey.customer_id, model)
                if result:
                    results_by_model[model].append((journey.ground_truth, result.attributed))

        # Calculate accuracy metrics
        metrics = {}
        for model in models:
            pairs = results_by_model[model]
            if not pairs:
                continue

            mapes = []
            rmses = []
            correlations = []
            channel_accuracies: dict[str, list[float]] = {}

            for gt, at in pairs:
                mape, rmse, corr = self.calculate_accuracy(gt, at)
                mapes.append(mape)
                rmses.append(rmse)
                correlations.append(corr)

                # Per-channel accuracy
                all_channels = set(gt.keys()) | set(at.keys())
                for channel in all_channels:
                    gt_val = gt.get(channel, 0)
                    at_val = at.get(channel, 0)
                    if gt_val > 0:
                        acc = 100 - (abs(gt_val - at_val) / gt_val * 100)
                        channel_accuracies.setdefault(channel, []).append(max(0, acc))

            metrics[model] = AccuracyMetrics(
                model=model,
                mape=sum(mapes) / len(mapes) if mapes else 0,
                rmse=sum(rmses) / len(rmses) if rmses else 0,
                correlation=sum(correlations) / len(correlations) if correlations else 0,
                channel_accuracy={c: sum(v) / len(v) for c, v in channel_accuracies.items()},
                total_customers=len(pairs),
            )

        return metrics

    def print_results(self, metrics: dict[str, AccuracyMetrics]) -> None:
        """Print benchmark results."""
        print("\n" + "=" * 80)
        print("ATTRIBUTION ACCURACY BENCHMARK RESULTS")
        print("=" * 80)

        for model, m in metrics.items():
            print(f"\nModel: {model.upper()}")
            print(f"  Customers Tested:  {m.total_customers}")
            print(f"  MAPE:              {m.mape:.2f}%")
            print(f"  RMSE:              {m.rmse:.2f}")
            print(f"  Correlation:       {m.correlation:.4f}")

            if m.channel_accuracy:
                print(f"  Channel Accuracy:")
                for channel, acc in sorted(m.channel_accuracy.items(), key=lambda x: -x[1]):
                    print(f"    {channel:20s}: {acc:.1f}%")

        # Summary table
        print("\n" + "-" * 80)
        print(f"{'Model':<20} {'MAPE':>10} {'RMSE':>10} {'Correlation':>12} {'Customers':>10}")
        print("-" * 80)
        for model, m in sorted(metrics.items(), key=lambda x: x[1].mape):
            print(f"{model:<20} {m.mape:>10.2f} {m.rmse:>10.2f} {m.correlation:>12.4f} {m.total_customers:>10}")
        print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="Attribution accuracy benchmark")
    parser.add_argument("--customers", type=int, default=1000, help="Number of customers")
    parser.add_argument("--journeys", type=int, default=3, help="Journeys per customer")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--tenant", default="00000000-0000-0000-0000-000000000001", help="Tenant ID")
    parser.add_argument("--token", default="dev-token", help="Auth token")
    args = parser.parse_args()

    async with AccuracyBenchmark(args.url, args.tenant, args.token) as benchmark:
        metrics = await benchmark.run_benchmark(args.customers, args.journeys)
        benchmark.print_results(metrics)

        # Exit with error if any model has MAPE > 20%
        max_mape = max(m.mape for m in metrics.values())
        if max_mape > 20:
            print(f"\n❌ FAIL: Max MAPE {max_mape:.1f}% exceeds 20% threshold")
            exit(1)
        else:
            print(f"\n✅ PASS: All models MAPE <= 20% (max: {max_mape:.1f}%)")
            exit(0)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
Analytics API endpoints: Metrics, Attribution, Cohorts, RFM.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    DailyMetric, CohortMetric, RFMMetric, AttributionTouchpoint, AttributionResult,
    PredictiveMetric, AnomalyEvent, Customer, Order
)

logger = structlog.get_logger()
router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(
    client_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func
    from ...models import DailyMetric
    
    query = select(DailyMetric).where(DailyMetric.client_id == current_user.client_id)
    
    if client_id:
        query = query.where(DailyMetric.client_id == client_id)
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = query.where(DailyMetric.date >= cutoff)
    
    result = await db.execute(query.order_by(DailyMetric.date.desc()))
    metrics = result.scalars().all()
    
    total_revenue = sum(float(m.total_revenue or 0) for m in metrics)
    total_orders = sum(m.total_orders or 0 for m in metrics)
    total_customers = sum(m.new_customers or 0 for m in metrics)
    
    email_revenue = sum(float(m.email_revenue or 0) for m in metrics)
    sms_revenue = sum(float(m.sms_revenue or 0) for m in metrics)
    push_revenue = sum(float(m.push_revenue or 0) for m in metrics)
    organic_revenue = sum(float(m.organic_revenue or 0) for m in metrics)
    
    return {
        "period_days": days,
        "totals": {
            "revenue": total_revenue,
            "orders": total_orders,
            "new_customers": total_customers,
        },
        "channel_breakdown": {
            "email": email_revenue,
            "sms": sms_revenue,
            "push": push_revenue,
            "organic": organic_revenue,
        },
        "daily_series": [
            {
                "date": m.date.isoformat(),
                "revenue": float(m.total_revenue or 0),
                "orders": m.total_orders,
                "sessions": m.sessions,
            }
            for m in metrics[:30]
        ],
    }

@router.get("/cohorts")
async def get_cohorts(
    client_id: Optional[str] = None,
    months: int = Query(12, ge=1, le=24),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import CohortMetric
    from sqlalchemy import func
    
    query = select(CohortMetric).where(CohortMetric.client_id == current_user.client_id)
    
    if client_id:
        query = query.where(CohortMetric.client_id == client_id)
    
    cutoff = datetime.utcnow().replace(day=1) - timedelta(days=months * 30)
    query = query.where(CohortMetric.cohort_month >= cutoff.strftime("%Y-%m"))
    
    result = await db.execute(query.order_by(CohortMetric.cohort_month.desc(), CohortMetric.period))
    cohorts = result.scalars().all()
    
    cohort_data = {}
    for c in cohorts:
        key = c.cohort_month
        if key not in cohort_data:
            cohort_data[key] = {
                "cohort_month": key,
                "cohort_size": c.cohort_size,
                "periods": [],
            }
        cohort_data[key]["periods"].append({
            "period": c.period,
            "retained": c.retained_customers,
            "repeat_rate": float(c.repeat_rate),
            "revenue_per_customer": float(c.revenue_per_customer),
        })
    
    return {"cohorts": list(cohort_data.values())}

@router.get("/rfm")
async def get_rfm(
    client_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import RFMMetric
    from sqlalchemy import func
    
    query = select(RFMMetric).where(RFMMetric.client_id == current_user.client_id)
    
    if client_id:
        query = query.where(RFMMetric.client_id == client_id)
    
    result = await db.execute(query)
    rfm_metrics = result.scalars().all()
    
    segment_data = {}
    for rfm in rfm_metrics:
        segment = rfm.segment
        if segment not in segment_data:
            segment_data[segment] = {
                "segment": segment,
                "count": 0,
                "total_revenue": 0,
                "avg_ltv": 0,
            }
        segment_data[segment]["count"] += 1
        segment_data[segment]["total_revenue"] += float(rfm.monetary or 0)
    
    for seg, data in segment_data.items():
        data["avg_ltv"] = data["total_revenue"] / max(data["count"], 1)
    
    return {"segments": list(segment_data.values())}

@router.get("/attribution")
async def get_attribution(
    client_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import AttributionResult, AttributionTouchpoint
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = select(AttributionResult).where(
        AttributionResult.client_id == current_user.client_id
    )
    
    if client_id:
        query = query.where(AttributionResult.client_id == client_id)
    
    result = await db.execute(query)
    results = result.scalars().all()
    
    channel_data = {}
    for ar in results:
        for channel, revenue in ar.channel_revenue.items():
            if channel not in channel_data:
                channel_data[channel] = {"revenue": 0, "touchpoints": 0}
            channel_data[channel]["revenue"] += float(revenue)
            channel_data[channel]["touchpoints"] += ar.channel_touchpoints.get(channel, 0)
    
    return {
        "period_days": days,
        "channels": channel_data,
        "total_attributed_revenue": sum(c["revenue"] for c in channel_data.values()),
    }

@router.get("/predictive")
async def get_predictive(
    client_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import PredictiveMetric
    from sqlalchemy import func
    
    query = select(PredictiveMetric).where(PredictiveMetric.client_id == current_user.client_id)
    
    if client_id:
        query = query.where(PredictiveMetric.client_id == client_id)
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    high_churn = sum(1 for m in metrics if m.churn_risk_level in ("high", "critical"))
    avg_ltv = sum(float(m.predicted_ltv or 0) for m in metrics) / max(len(metrics), 1)
    avg_churn = sum(float(m.churn_probability or 0) for m in metrics) / max(len(metrics), 1)
    
    return {
        "total_customers": len(metrics),
        "high_churn_risk": high_churn,
        "avg_predicted_ltv": avg_ltv,
        "avg_churn_probability": avg_churn,
    }

@router.get("/anomalies")
async def get_anomalies(
    client_id: Optional[str] = None,
    status: str = Query("open"),
    days: int = Query(30, ge=1, le=90),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import AnomalyEvent
    from datetime import datetime, timedelta
    
    query = select(AnomalyEvent).where(
        AnomalyEvent.client_id == current_user.client_id,
        AnomalyEvent.detected_at >= datetime.utcnow() - timedelta(days=days)
    )
    
    if client_id:
        query = query.where(AnomalyEvent.client_id == client_id)
    
    if status:
        query = query.where(AnomalyEvent.status == status)
    
    result = await db.execute(query.order_by(desc(AnomalyEvent.detected_at)).limit(100))
    anomalies = result.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "metric": a.metric_name,
            "type": a.anomaly_type,
            "severity": a.severity,
            "expected": float(a.expected_value),
            "actual": float(a.actual_value),
            "deviation": float(a.deviation),
            "deviation_pct": float(a.deviation_percent),
            "status": a.status,
            "detected_at": a.detected_at.isoformat(),
        }
        for a in anomalies
    ]

@router.get("/realtime")
async def get_realtime(
    client_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import DailyMetric
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    query = select(DailyMetric).where(
        DailyMetric.client_id == current_user.client_id,
        DailyMetric.date >= today
    )
    
    if client_id:
        query = query.where(DailyMetric.client_id == client_id)
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    if not metrics:
        return {"message": "No data available for today"}
    
    latest = metrics[0]
    return {
        "date": today.isoformat(),
        "revenue": float(latest.total_revenue or 0),
        "orders": latest.total_orders or 0,
        "sessions": latest.sessions or 0,
        "conversion_rate": float(latest.conversion_rate or 0),
    }

@router.get("/channel-breakdown")
async def get_channel_breakdown(
    client_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import DailyMetric
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    query = select(DailyMetric).where(DailyMetric.client_id == current_user.client_id)
    
    if client_id:
        query = query.where(DailyMetric.client_id == client_id)
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = query.where(DailyMetric.date >= cutoff)
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    return {
        "email": sum(float(m.email_revenue or 0) for m in metrics),
        "sms": sum(float(m.sms_revenue or 0) for m in metrics),
        "push": sum(float(m.push_revenue or 0) for m in metrics),
        "organic": sum(float(m.organic_revenue or 0) for m in metrics),
        "direct": sum(float(m.direct_revenue or 0) for m in metrics),
        "referral": sum(float(m.referral_revenue or 0) for m in metrics),
    }

@router.get("/export")
async def export_data(
    client_id: Optional[str] = None,
    start_date: str = Query(...),
    end_date: str = Query(...),
    format: str = Query("csv"),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import DailyMetric
    from datetime import datetime
    import io
    import csv
    
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    query = select(DailyMetric).where(
        DailyMetric.client_id == current_user.client_id,
        DailyMetric.date >= start,
        DailyMetric.date <= end
    )
    
    if client_id:
        query = query.where(DailyMetric.client_id == client_id)
    
    result = await db.execute(query.order_by(DailyMetric.date))
    metrics = result.scalars().all()
    
    if format == "csv":
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "date", "client_id", "total_revenue", "orders", "sessions",
            "email_revenue", "sms_revenue", "organic_revenue"
        ])
        for m in metrics:
            writer.writerow([
                m.date.isoformat(),
                str(m.client_id),
                float(m.total_revenue or 0),
                m.total_orders,
                m.sessions,
                float(m.email_revenue or 0),
                float(m.sms_revenue or 0),
                float(m.organic_revenue or 0),
            ])
        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=analytics_{datetime.now().date()}.csv"}
        )
    
    return [m.__dict__ for m in metrics]
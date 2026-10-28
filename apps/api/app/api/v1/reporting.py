"""
Reporting API endpoints: Report generation, scheduling, exports.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import io
import csv
import json
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    ReportDefinition, ReportTemplate, ReportRun, ReportSchedule,
    ReportExport, Client
)

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.get("/templates")
async def list_templates(
    category: Optional[str] = None,
    vertical: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportTemplate
    query = select(ReportTemplate).where(ReportTemplate.is_active == True)
    
    if category:
        query = query.where(ReportTemplate.category == category)
    if vertical:
        query = query.where(ReportTemplate.vertical == vertical)
    
    result = await db.execute(query.order_by(ReportTemplate.name))
    templates = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "vertical": t.vertical,
            "default_formats": t.default_formats,
            "tags": t.tags,
        }
        for t in templates
    ]

@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportTemplate
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "vertical": template.vertical,
        "sections": template.sections,
        "default_filters": template.default_filters,
        "default_formats": template.default_formats,
        "default_schedule": template.default_schedule,
        "tags": template.tags,
    }

@router.post("", status_code=201)
async def create_report(
    report_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition
    
    report = ReportDefinition(
        client_id=current_user.client_id,
        name=report_data.get("name"),
        description=report_data.get("description"),
        template_id=report_data.get("template_id"),
        sections=report_data.get("sections", []),
        filters=report_data.get("filters", []),
        schedule=report_data.get("schedule"),
        formats=report_data.get("formats", ["pdf"]),
        recipients=report_data.get("recipients", []),
        slack_channels=report_data.get("slack_channels", []),
        webhook_urls=report_data.get("webhook_urls", []),
        tags=report_data.get("tags", []),
        vertical=report_data.get("vertical"),
        created_by=current_user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {"id": str(report.id), "message": "Report created"}

@router.get("")
async def list_reports(
    status: Optional[str] = None,
    vertical: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition
    from sqlalchemy import desc
    
    query = select(ReportDefinition).where(ReportDefinition.client_id == current_user.client_id)
    
    if status:
        query = query.where(ReportDefinition.status == status)
    if vertical:
        query = query.where(ReportDefinition.vertical == vertical)
    if client_id:
        query = query.where(ReportDefinition.id == client_id)
    
    query = query.order_by(desc(ReportDefinition.updated_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "status": r.status,
            "vertical": r.vertical,
            "template_id": r.template_id,
            "schedule": r.schedule,
            "formats": r.formats,
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in reports
    ]

@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.id == report_id,
            ReportDefinition.client_id == current_user.client_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "name": report.name,
        "description": report.description,
        "template_id": report.template_id,
        "sections": report.sections,
        "filters": report.filters,
        "schedule": report.schedule,
        "formats": report.formats,
        "recipients": report.recipients,
        "slack_channels": report.slack_channels,
        "webhook_urls": report.webhook_urls,
        "status": report.status,
        "tags": report.tags,
        "vertical": report.vertical,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
    }

@router.patch("/{report_id}")
async def update_report(
    report_id: str,
    report_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.id == report_id,
            ReportDefinition.client_id == current_user.client_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    update_data = report_data
    for field, value in update_data.items():
        if hasattr(report, field):
            setattr(report, field, value)
    
    report.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(report)
    return {"message": "Report updated"}

@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.id == report_id,
            ReportDefinition.client_id == current_user.client_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    await db.delete(report)
    await db.commit()
    return Response(status_code=204)

@router.post("/{report_id}/run")
async def run_report(
    report_id: str,
    parameters: dict = {},
    filters: list = [],
    date_range: dict = {},
    formats: list = [],
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportDefinition, ReportRun
    import uuid
    
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.id == report_id,
            ReportDefinition.client_id == current_user.client_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    run = ReportRun(
        id=uuid.uuid4(),
        report_id=report.id,
        client_id=current_user.client_id,
        triggered_by="manual",
        parameters=parameters,
        filters_applied=filters,
        date_range=date_range,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    
    return {"run_id": str(run.id), "status": "queued"}

@router.get("/{report_id}/runs")
async def list_report_runs(
    report_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportRun
    from sqlalchemy import desc
    
    query = select(ReportRun).where(ReportRun.report_id == report_id)
    if status:
        query = query.where(ReportRun.status == status)
    query = query.order_by(desc(ReportRun.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "status": r.status,
            "triggered_by": r.triggered_by,
            "progress": r.progress,
            "widgets_rendered": r.widgets_rendered,
            "widgets_failed": r.widgets_failed,
            "total_time_ms": r.total_time_ms,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]

@router.get("/{report_id}/runs/{run_id}")
async def get_report_run(
    report_id: str,
    run_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportRun
    result = await db.execute(
        select(ReportRun).where(
            ReportRun.id == run_id,
            ReportRun.report_id == report_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "id": run.id,
        "report_id": run.report_id,
        "status": r.status,
        "triggered_by": r.triggered_by,
        "parameters": r.parameters,
        "filters_applied": r.filters_applied,
        "date_range": r.date_range,
        "output_files": r.output_files,
        "widgets_rendered": r.widgets_rendered,
        "widgets_failed": r.widgets_failed,
        "render_time_ms": r.render_time_ms,
        "total_time_ms": r.total_time_ms,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }

@router.get("/{report_id}/runs/{run_id}/download/{format}")
async def download_report(
    report_id: str,
    run_id: str,
    format: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportRun
    result = await db.execute(
        select(ReportRun).where(
            ReportRun.id == run_id,
            ReportRun.report_id == report_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    file_info = next((f for f in run.output_files if f.get("format") == format), None)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_info.get("path"),
        filename=file_info.get("filename"),
        media_type="application/pdf" if format == "pdf" else "text/html",
    )

@router.get("/schedules")
async def list_schedules(
    report_id: Optional[str] = None,
    active_only: bool = True,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule
    query = select(ReportSchedule)
    if report_id:
        query = query.where(ReportSchedule.report_id == report_id)
    if active_only:
        query = query.where(ReportSchedule.is_active == True)
    query = query.where(ReportSchedule.client_id == current_user.client_id)
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "report_id": s.report_id,
            "cron_expression": s.cron_expression,
            "timezone": s.timezone,
            "is_active": s.is_active,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "run_count": s.run_count,
            "failure_count": s.failure_count,
        }
        for s in schedules
    ]

@router.post("/schedules", status_code=201)
async def create_schedule(
    schedule_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule
    schedule = ReportSchedule(
        report_id=schedule_data["report_id"],
        cron_expression=schedule_data["cron_expression"],
        timezone=schedule_data.get("timezone", "UTC"),
        default_parameters=schedule_data.get("default_parameters", {}),
        recipients=schedule_data.get("recipients", []),
        slack_channels=schedule_data.get("slack_channels", []),
        webhook_urls=schedule_data.get("webhook_urls", []),
    )
    schedule = ReportSchedule(**schedule_data)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return {"id": schedule.id, "report_id": schedule.report_id, "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None}

@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule, ReportRun
    import uuid
    result = await db.execute(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.client_id == current_user.client_id
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    run = await db.execute(
        select(ReportRun).where(
            ReportRun.report_id == schedule.report_id,
            ReportRun.triggered_by == "manual_schedule_trigger"
        ).order_by(desc(ReportRun.created_at)).limit(1)
    )
    run = run.scalar_one_or_none()
    
    if not run:
        run = ReportRun(
            id=uuid.uuid4(),
            report_id=schedule.report_id,
            client_id=current_user.client_id,
            triggered_by="manual_schedule_trigger",
            parameters=schedule.default_parameters,
            status="pending",
            started_at=datetime.utcnow(),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
    
    return {"run_id": str(run.id)}

@router.post("/schedules/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule
    result = await db.execute(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.client_id == current_user.client_id
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_active = False
    await db.commit()
    return {"success": True}

@router.post("/schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule
    result = await db.execute(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.client_id == current_user.client_id
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_active = True
    await db.commit()
    return {"success": True}

@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import ReportSchedule
    result = await db.execute(
        select(ReportSchedule).where(
            ReportSchedule.id == schedule_id,
            ReportSchedule.client_id == current_user.client_id
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(schedule)
    await db.commit()
    return Response(status_code=204)

@router.get("/exports/formats")
async def list_export_formats():
    return [
        {"format": "pdf", "name": "PDF", "description": "Portable Document Format"},
        {"format": "html", "name": "HTML", "description": "HyperText Markup Language"},
        {"format": "csv", "name": "CSV", "description": "Comma-Separated Values"},
        {"format": "json", "name": "JSON", "description": "JavaScript Object Notation"},
        {"format": "xlsx", "name": "Excel", "description": "Microsoft Excel"},
        {"format": "md", "name": "Markdown", "description": "Markdown"},
    ]
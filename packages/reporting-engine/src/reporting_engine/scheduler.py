"""
Report Scheduler

Manages scheduled report execution using cron expressions.
Integrates with Celery for distributed task execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from croniter import croniter

from .models import ReportSchedule, ReportDefinition, RunStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import ReportingEngine

log = structlog.get_logger()


class ReportScheduler:
    """Scheduler for recurring report execution."""

    def __init__(self, engine: ReportingEngine):
        self.engine = engine
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._check_interval = 60  # Check every minute

    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        log.info("report_scheduler_started")
        
        # Schedule all active schedules
        for schedule in self.engine.list_schedules(active_only=True):
            await self._schedule_report(schedule)
        
        # Start scheduler loop
        asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks.values():
            task.cancel()
        
        # Wait for cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        
        self._tasks.clear()
        log.info("report_scheduler_stopped")

    async def add_schedule(self, schedule: ReportSchedule) -> ReportSchedule:
        """Add a new schedule and start it."""
        schedule = self.engine.create_schedule(schedule)
        
        if schedule.is_active:
            await self._schedule_report(schedule)
        
        return schedule

    async def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        # Cancel running task
        if schedule_id in self._tasks:
            self._tasks[schedule_id].cancel()
            del self._tasks[schedule_id]
        
        return self.engine.delete_schedule(schedule_id)

    async def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        schedule = self.engine.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.is_active = False
        schedule.updated_at = datetime.utcnow()
        
        if schedule_id in self._tasks:
            self._tasks[schedule_id].cancel()
            del self._tasks[schedule_id]
        
        return True

    async def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        schedule = self.engine.get_schedule(schedule_id)
        if not schedule:
            return False
        
        schedule.is_active = True
        schedule.updated_at = datetime.utcnow()
        
        await self._schedule_report(schedule)
        return True

    async def trigger_now(self, schedule_id: str) -> Optional[str]:
        """Manually trigger a scheduled report immediately."""
        schedule = self.engine.get_schedule(schedule_id)
        if not schedule:
            return None
        
        report = self.engine.get_report(schedule.report_id)
        if not report:
            return None
        
        run = await self.engine.run_report(
            report_id=report.id,
            triggered_by="schedule",
            parameters=schedule.default_parameters,
        )
        
        # Update schedule stats
        schedule.last_run_at = datetime.utcnow()
        schedule.run_count += 1
        if run.status == RunStatus.FAILED:
            schedule.failure_count += 1
        
        return run.id

    async def _schedule_report(self, schedule: ReportSchedule):
        """Schedule a report for recurring execution."""
        if schedule.id in self._tasks:
            self._tasks[schedule.id].cancel()

        task = asyncio.create_task(self._run_schedule_loop(schedule))
        self._tasks[schedule.id] = task

    async def _run_schedule_loop(self, schedule: ReportSchedule):
        """Run loop for a single schedule."""
        try:
            while self._running:
                # Calculate next run
                next_run = self._get_next_run(schedule)
                schedule.next_run_at = next_run
                
                # Wait until next run
                wait_seconds = (next_run - datetime.utcnow()).total_seconds()
                
                if wait_seconds > 0:
                    try:
                        await asyncio.sleep(wait_seconds)
                    except asyncio.CancelledError:
                        break
                
                if not self._running:
                    break
                
                # Check if schedule is still active
                current_schedule = self.engine.get_schedule(schedule.id)
                if not current_schedule or not current_schedule.is_active:
                    break
                
                # Execute report
                report = self.engine.get_report(schedule.report_id)
                if not report:
                    log.warning("scheduled_report_not_found", schedule_id=schedule.id)
                    break
                
                log.info("scheduled_report_triggered", schedule_id=schedule.id, report_id=report.id)
                
                try:
                    run = await self.engine.run_report(
                        report_id=report.id,
                        triggered_by="schedule",
                        parameters=schedule.default_parameters,
                    )
                    
                    # Update schedule stats
                    current_schedule.last_run_at = datetime.utcnow()
                    current_schedule.run_count += 1
                    current_schedule.next_run_at = self._get_next_run(current_schedule)
                    
                    if run.status == RunStatus.FAILED:
                        current_schedule.failure_count += 1
                        log.error("scheduled_report_failed", schedule_id=schedule.id, run_id=run.id)
                    else:
                        log.info("scheduled_report_completed", schedule_id=schedule.id, run_id=run.id)
                        
                except Exception as e:
                    log.exception("scheduled_report_error", schedule_id=schedule.id, error=str(e))
                    current_schedule.failure_count += 1
                
        except asyncio.CancelledError:
            log.info("schedule_cancelled", schedule_id=schedule.id)
        except Exception as e:
            log.exception("schedule_loop_error", schedule_id=schedule.id, error=str(e))

    async def _scheduler_loop(self):
        """Main scheduler loop - checks for new/updated schedules."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                
                # Sync schedules with engine
                current_schedules = {s.id: s for s in self.engine.list_schedules(active_only=True)}
                
                # Start new schedules
                for schedule_id, schedule in current_schedules.items():
                    if schedule_id not in self._tasks:
                        await self._schedule_report(schedule)
                
                # Stop removed schedules
                for task_id in list(self._tasks.keys()):
                    if task_id not in current_schedules:
                        self._tasks[task_id].cancel()
                        del self._tasks[task_id]
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception("scheduler_loop_error", error=str(e))

    def _get_next_run(self, schedule: ReportSchedule) -> datetime:
        """Calculate next run time from cron expression."""
        now = datetime.utcnow()
        cron = croniter(schedule.cron_expression, now)
        return cron.get_next(datetime)

    def get_next_runs(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming scheduled runs."""
        schedules = self.engine.list_schedules(active_only=True)
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        
        upcoming = []
        for schedule in schedules:
            next_run = schedule.next_run_at or self._get_next_run(schedule)
            if next_run <= cutoff:
                report = self.engine.get_report(schedule.report_id)
                upcoming.append({
                    "schedule_id": schedule.id,
                    "report_id": schedule.report_id,
                    "report_name": report.name if report else "Unknown",
                    "next_run_at": next_run.isoformat(),
                    "cron_expression": schedule.cron_expression,
                })
        
        upcoming.sort(key=lambda x: x["next_run_at"])
        return upcoming

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "active_schedules": len(self._tasks),
            "total_schedules": len(self.engine.list_schedules(active_only=True)),
            "check_interval_seconds": self._check_interval,
        }
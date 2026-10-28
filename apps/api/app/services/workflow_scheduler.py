"""
Workflow Scheduler - Handles scheduled workflow triggers and manages the execution queue.
"""
import asyncio
import structlog
from datetime import datetime, timedelta
from typing import Optional, List
from croniter import croniter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.workflows import WorkflowDefinition, WorkflowTrigger, WorkflowExecution
from app.services.workflow_engine import WorkflowEngine, get_workflow_engine

logger = structlog.get_logger()


class WorkflowScheduler:
    """Background scheduler for workflow triggers."""
    
    def __init__(self):
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._scheduler_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("workflow_scheduler_started")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("workflow_scheduler_stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop - runs every minute."""
        while True:
            try:
                await self._check_scheduled_workflows()
                await self._check_due_executions()
            except Exception as e:
                logger.error("scheduler_error", error=str(e))
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _check_scheduled_workflows(self):
        """Check for workflows with cron schedules that should run."""
        from app.core.database import async_session_maker
        from app.models.workflows import WorkflowDefinition
        from sqlalchemy import select, and_
        
        async with async_session_maker() as db:
            now = datetime.utcnow()
            
            # Find workflows with cron schedules that should run
            query = select(WorkflowDefinition).where(
                WorkflowDefinition.schedule.isnot(None),
                WorkflowDefinition.status == "published",
                WorkflowDefinition.schedule != ""
            )
            
            result = await self.db.execute(select(WorkflowDefinition).where(
                WorkflowDefinition.schedule.isnot(None),
                WorkflowDefinition.status == "published",
                WorkflowDefinition.schedule != ""
            ))
            workflows = result.scalars().all()
            
            for workflow in workflows:
                if self._should_run_now(workflow.schedule):
                    await self._queue_workflow_execution(workflow)
    
    def _should_run_now(self, cron_expression: str) -> bool:
        """Check if cron expression matches current time."""
        try:
            cron = croniter(cron_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)
            # Run if next run is within the next minute
            return datetime.utcnow() >= next_run - timedelta(seconds=30)
        except Exception:
            return False
    
    async def _queue_workflow_execution(self, workflow, trigger_data: dict = None):
        """Queue a workflow execution."""
        from app.core.database import async_session_maker
        from app.models.workflows import WorkflowExecution
        import uuid
        
        async with async_session_maker() as db:
            execution = WorkflowExecution(
                workflow_id=workflow.id,
                client_id=workflow.client_id,
                trigger_type="schedule",
                trigger_data={},
                trigger_source="scheduler",
                status="pending",
                variables={},
                queued_at=datetime.utcnow(),
                priority=0,
            )
            db.add(workflow)
            await db.commit()
            logger.info("workflow_queued", workflow_id=str(workflow.id), execution_id=str(execution.id))


class WorkflowQueueProcessor:
    """Processes workflow execution queue."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
    
    async def start(self):
        if self._running:
            return
        self._running = True
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(task)
        logger.info("workflow_queue_processor_started", workers=self.max_concurrent)
    
    async def stop(self):
        self._running = False
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        logger.info("workflow_queue_processor_stopped")
    
    async def _worker(self, worker_name: str):
        while True:
            try:
                execution = await self._claim_next_execution()
                if execution:
                    await self._process_execution(execution)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("worker_error", worker=worker_name, error=str(e))
                await asyncio.sleep(5)
    
    async def _claim_next_execution(self) -> Optional[WorkflowExecution]:
        """Atomically claim the next pending execution."""
        from app.core.database import async_session_maker
        from sqlalchemy import update
        from app.models.workflows import WorkflowExecution
        
        async with async_session_maker() as db:
            # Find pending execution with highest priority
            result = await db.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.status == "pending")
                .order_by(WorkflowExecution.priority.desc(), WorkflowExecution.queued_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            execution = result.scalar_one_or_none()
            
            if execution:
                execution.status = "running"
                execution.started_at = datetime.utcnow()
                await db.commit()
                return execution
        return None
    
    async def _process_execution(self, execution):
        """Process a single workflow execution."""
        from app.core.database import async_session_maker
        from app.services.workflow_engine import get_workflow_engine
        
        async with async_session_maker() as db:
            engine = get_workflow_engine(db)
            
            # Load workflow
            from sqlalchemy import select
            from app.models.workflows import WorkflowDefinition
            result = await db.execute(
                select(WorkflowDefinition)
                .where(WorkflowDefinition.id == execution.workflow_id)
                .options(selectinload(WorkflowDefinition.nodes), selectinload(WorkflowDefinition.edges))
            )
            workflow = result.scalar_one_or_none()
            
            if not workflow:
                execution.status = "failed"
                execution.error = "Workflow not found"
                await db.commit()
                return
            
            # Execute workflow
            engine = WorkflowEngine(db)
            await engine.execute_workflow(execution, workflow)


# Celery-style task definitions for background jobs
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "retention_analytics",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_workflow_task(self, execution_id: str):
    """Celery task to execute a workflow."""
    import asyncio
    from app.core.database import async_session_maker
    from app.services.workflow_engine import get_workflow_engine
    from app.models.workflows import WorkflowExecution
    
    async def _run():
        async with async_session_maker() as db:
            from sqlalchemy import select
            from app.models.workflows import WorkflowExecution
            from app.services.workflow_engine import get_workflow_engine
            
            async with async_session_maker() as db:
                result = await db.execute(
                    select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                )
                execution = result.scalar_one_or_none()
                
                if not execution:
                    return {"status": "not_found"}
                
                from sqlalchemy import select
                from app.models.workflows import WorkflowDefinition
                from app.services.workflow_engine import get_workflow_engine
                
                result = await db.execute(
                    select(WorkflowDefinition)
                    .where(WorkflowDefinition.id == execution.workflow_id)
                    .options(selectinload(WorkflowDefinition.nodes), selectinload(WorkflowDefinition.edges))
                )
                workflow = result.scalar_one_or_none()
                
                if not workflow:
                    execution.status = "failed"
                    execution.error = "Workflow not found"
                    await db.commit()
                    return {"status": "failed", "error": "Workflow not found"}
                
                from app.services.workflow_engine import get_workflow_engine
                engine = get_workflow_engine(db)
                await engine.execute_workflow(execution, workflow)
                await db.refresh(execution)
                return {"status": execution.status, "execution_id": str(execution.id)}
    
    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_node_task(self, execution_id: str, node_id: str):
    """Execute a single workflow node."""
    import asyncio
    from app.core.database import async_session_maker
    from app.models.workflows import WorkflowNodeExecution, WorkflowExecution
    from app.services.workflow_engine import get_workflow_engine, NodeExecutor
    
    async def _run():
        async with async_session_maker() as db:
            from sqlalchemy import select
            from app.models.workflows import WorkflowNodeExecution
            
            result = await db.execute(
                select(WorkflowNodeExecution).where(
                    WorkflowNodeExecution.id == node_id,
                    WorkflowNodeExecution.execution_id == execution_id
                )
            )
            node_execution = result.scalar_one_or_none()
            
            if not node_execution:
                return {"status": "not_found"}
            
            from app.services.workflow_engine import get_workflow_engine, NodeExecutor
            engine = get_workflow_engine(db)
            node_execution = await db.get(WorkflowNodeExecution, node_execution.id)
            
            if not node_execution:
                return {"status": "not_found"}
            
            # Get node definition
            from app.models.workflows import WorkflowDefinition
            result = await db.execute(
                select(WorkflowDefinition).where(WorkflowDefinition.id == node_execution.execution.workflow_id)
            )
            workflow = result.scalar_one_or_none()
            
            if not workflow:
                return {"status": "error", "error": "Workflow not found"}
            
            node = next((n for n in workflow.nodes if n["id"] == node_execution.node_id), None)
            if not node:
                return {"status": "error", "error": "Node not found"}
            
            from app.services.workflow_engine import NODE_EXECUTORS, NodeExecutor
            executor_cls = NODE_EXECUTORS.get(node.get("type"))
            
            if not executor_cls:
                node_execution.status = "failed"
                node_execution.error = f"No executor for node type: {node.get('type')}"
                await db.commit()
                return {"status": "error", "error": f"No executor for type {node.get('type')}"}
            
            executor = NODE_EXECUTORS[node.get("type")](db, node_execution.execution, node)
            context = NodeContext(
                execution_id=str(execution.id),
                workflow_id=str(node_execution.execution.workflow_id),
                node_id=node["id"],
                node_type=node.get("type"),
                node_name=node.get("name", ""),
                input_data=node_execution.input_data,
                variables=node_execution.execution.variables,
                execution_variables=node_execution.execution.variables,
                execution_id=str(execution_id),
                workflow_id=str(node_execution.execution.workflow_id),
            )
            
            executor = NODE_EXECUTORS[node.get("type")](db, execution, node)
            result = await executor.execute(context)
            
            node_execution.status = "completed" if result.success else "failed"
            node_execution.output_data = result.output_data
            node_execution.error = result.error
            node_execution.completed_at = datetime.utcnow()
            node_execution.duration_ms = int((datetime.utcnow() - node_execution.started_at).total_seconds() * 1000) if node_execution.started_at else 0
            
            await db.commit()
            return {"status": node_execution.status}
    
    return asyncio.run(_run())


# High-level workflow orchestration service
class WorkflowOrchestrator:
    """High-level workflow orchestration service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = WorkflowEngine(db)
    
    async def create_and_execute(
        self,
        workflow_data: dict,
        trigger_data: dict = None,
        current_user = None
    ) -> WorkflowExecution:
        """Create and immediately execute a workflow."""
        # Create workflow
        from app.models.workflows import WorkflowDefinition
        workflow = WorkflowDefinition(
            client_id=current_user.client_id,
            name=workflow_data.get("name"),
            description=workflow_data.get("description"),
            category=workflow_data.get("category", "general"),
            nodes=workflow_data.get("nodes", []),
            edges=workflow_data.get("edges", []),
            triggers=workflow_data.get("triggers", []),
            settings=workflow_data.get("settings", {}),
        )
        self.db.add(workflow)
        await self.db.flush()
        
        # Execute immediately
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            client_id=current_user.client_id,
            trigger_type="manual",
            trigger_data=trigger_data or {},
            trigger_source="api",
            variables=trigger_data or {},
            status="pending",
            queued_at=datetime.utcnow(),
        )
        self.db.add(workflow)
        self.db.add(execution)
        await self.db.commit()
        
        # Execute
        engine = WorkflowEngine(self.db)
        return await self.engine.execute_workflow(workflow, execution, trigger_data)
    
    async def schedule_workflow(
        self,
        workflow_id: str,
        cron_expression: str,
        timezone: str = "UTC",
        trigger_data: dict = None
    ):
        """Schedule a workflow with cron expression."""
        from app.models.workflows import WorkflowTrigger
        
        trigger = WorkflowTrigger(
            workflow_id=workflow_id,
            name=f"Schedule: {cron_expression}",
            type="schedule",
            config={"cron": cron_expression, "timezone": timezone},
            is_active=True,
        )
        self.db.add(trigger)
        await self.db.commit()
        return trigger
    
    async def get_execution_status(self, execution_id: str) -> dict:
        """Get detailed execution status with node progress."""
        from app.models.workflows import WorkflowExecution, WorkflowNodeExecution
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return {"error": "Not found"}
        
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(WorkflowNodeExecution.execution_id == execution.id)
            .order_by(WorkflowNodeExecution.started_at)
        )
        node_executions = result.scalars().all()
        
        return {
            "execution_id": str(execution.id),
            "workflow_id": str(execution.workflow_id),
            "status": execution.status,
            "progress_percent": float(execution.progress_percent or 0),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "error": execution.error,
            "current_node": execution.current_node_id,
            "completed_nodes": execution.completed_nodes,
            "total_nodes": execution.total_nodes,
            "retry_count": execution.retry_count,
            "revenue_attributed": float(execution.revenue_attributed or 0),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_name": n.node_name,
                    "status": n.status,
                    "started_at": n.started_at.isoformat() if n.started_at else None,
                    "completed_at": n.completed_at.isoformat() if n.completed_at else None,
                    "duration_ms": n.duration_ms,
                    "error": n.error,
                }
                for n in node_executions
            ]
        }


# Integration with external services
class IntegrationManager:
    """Manages connections to external platforms (Klaviyo, Shopify, etc.)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def sync_client_data(self, client_id: str, platforms: List[str] = None):
        """Sync data from connected platforms for a client."""
        # Trigger sync workflows for each platform
        pass
    
    async def sync_klaviyo(self, client_id: str, since: datetime = None):
        """Sync Klaviyo data (campaigns, flows, metrics)."""
        pass
    
    async def sync_shopify(self, client_id: str, since: datetime = None):
        """Sync Shopify data (orders, customers, products)."""
        pass
    
    async def sync_recharge(self, client_id: str, since: datetime = None):
        """Sync Recharge subscription data."""
        pass
    
    async def sync_postscript(self, client_id: str, since: datetime = None):
        """Sync Postscript SMS data."""
        pass
    
    async def sync_attentive(self, client_id: str, since: datetime = None):
        """Sync Attentive SMS data."""
        pass
    
    async def sync_omnisend(self, client_id: str, since: datetime = None):
        """Sync Omnisend data."""
        pass
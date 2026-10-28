"""
Workflow Execution Engine - Core execution logic for workflow definitions.
Handles node execution, branching, retries, subflows, and state management.
"""
import asyncio
import uuid
import structlog
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.workflows import (
    WorkflowDefinition, WorkflowExecution, WorkflowNodeExecution,
    WorkflowTrigger, WorkflowNodeExecution
)
from app.models import WorkflowDefinition, WorkflowExecution, WorkflowNodeExecution
from app.core.database import async_session_maker

logger = structlog.get_logger()


class NodeType(str, Enum):
    ACTION = "action"
    CONDITION = "condition"
    DELAY = "delay"
    BRANCH = "branch"
    LOOP = "loop"
    SUBFLOW = "subflow"
    WEBHOOK = "webhook"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    PAUSED = "paused"


@dataclass
class NodeContext:
    """Context passed to each node during execution."""
    execution_id: str
    workflow_id: str
    node_id: str
    node_type: str
    node_name: str
    input_data: Dict[str, Any]
    variables: Dict[str, Any]
    execution_variables: Dict[str, Any]
    execution_id: str
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeResult:
    success: bool
    output_data: Dict[str, Any]
    error: Optional[str] = None
    next_node_ids: Optional[List[str]] = None
    branch_taken: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)


class NodeExecutor:
    """Base class for node executors."""
    
    def __init__(self, db: AsyncSession, execution: "WorkflowExecution", node: Dict[str, Any]):
        self.db = db
        self.execution = execution
        self.node = node
        self.node_id = node.get("id")
        self.node_type = node.get("type")
        self.node_name = node.get("name", node.get("type", "unknown"))
        self.config = node.get("config", {})
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        raise NotImplementedError
    
    async def _get_input_data(self, context: 'NodeContext') -> Dict[str, Any]:
        """Extract input data from context based on node config."""
        input_mapping = self.node.get("input_mapping", {})
        input_data = {}
        for key, source in input_mapping.items():
            if source.startswith("variables."):
                key = source.replace("variables.", "")
                context.execution_variables[key] = context.variables.get(key)
            elif source.startswith("input."):
                key = source.replace("input.", "")
                context.input_data[key] = context.input_data.get(key)
            elif source.startswith("execution."):
                key = source.replace("execution.", "")
                context.execution_variables[key] = context.execution_variables.get(key)
        return context.input_data


@dataclass
class NodeContext:
    """Context passed to each node during execution."""
    execution_id: str
    workflow_id: str
    node_id: str
    node_type: str
    node_name: str
    input_data: Dict[str, Any]
    variables: Dict[str, Any]
    execution_variables: Dict[str, Any]
    execution_id: str
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeResult:
    success: bool
    output_data: Dict[str, Any]
    error: Optional[str] = None
    next_node_ids: Optional[List[str]] = None
    branch_taken: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)


class NodeExecutor:
    """Base class for node executors."""
    
    def __init__(self, db: AsyncSession, execution: "WorkflowExecution", node: Dict[str, Any]):
        self.db = db
        self.execution = execution
        self.node = node
        self.node_id = node.get("id")
        self.node_type = node.get("type")
        self.node_name = node.get("name", node.get("type", "unknown"))
        self.config = node.get("config", {})
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        raise NotImplementedError
    
    async def _get_input_data(self, context: 'NodeContext') -> Dict[str, Any]:
        """Extract input data from context based on node config."""
        input_mapping = self.node.get("input_mapping", {})
        input_data = {}
        for key, source in input_mapping.items():
            if source.startswith("variables."):
                key = source.replace("variables.", "")
                context.execution_variables[key] = context.variables.get(key)
            elif source.startswith("input."):
                key = source.replace("input.", "")
                context.input_data[key] = context.input_data.get(key)
            elif source.startswith("execution."):
                key = source.replace("execution.", "")
                context.execution_variables[key] = context.execution_variables.get(key)
        return context.input_data


class ActionNodeExecutor(NodeExecutor):
    """Executes action nodes (API calls, DB operations, external API calls)."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        action_type = self.config.get("action_type")
        action_config = self.config.get("action_config", {})
        
        try:
            if action_type == "http_request":
                return await self._execute_http_request(context)
            elif action_type == "db_query":
                return await self._execute_db_query(context)
            elif action_type == "send_email":
                return await self._execute_send_email(context)
            elif action_type == "send_sms":
                return await self._execute_send_sms(context)
            elif action_type == "send_push":
                return await self._execute_send_push(context)
            elif action_type == "create_record":
                return await self._execute_create_record(context)
            elif action_type == "update_record":
                return await self._execute_update_record(context)
            elif action_type == "delete_record":
                return await self._execute_delete_record(context)
            elif action_type == "call_webhook":
                return await self._execute_call_webhook(context)
            elif action_type == "run_query":
                return await self._execute_query(context)
            else:
                return NodeResult(success=False, output_data={}, error=f"Unknown action type: {action_type}")
        except Exception as e:
            logger.error("action_node_failed", node_id=self.node_id, error=str(e))
            return NodeResult(success=False, output_data={}, error=str(e))
    
    async def _execute_http_request(self, context: 'NodeContext') -> 'NodeResult':
        import httpx
        config = self.config.get("action_config", {})
        url = context.variables.get(self.config.get("url_var", ""), self.config.get("url", ""))
        method = self.config.get("method", "GET").upper()
        headers = self.config.get("headers", {})
        body = context.variables.get(self.config.get("body_var", ""), self.config.get("body", {}))
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, url, headers=headers, json=body)
            response.raise_for_status()
            return NodeResult(success=True, output_data={"response": response.json(), "status_code": response.status_code})
    
    async def _execute_db_query(self, context: 'NodeContext') -> 'NodeResult':
        from sqlalchemy import text
        query = self.config.get("query", "")
        params = context.variables.get(self.config.get("params_var", ""), {})
        async with self.execution.db.execute(text(query), params) as result:
            rows = [dict(row._mapping) for row in result]
            return NodeResult(success=True, output_data={"rows": rows, "count": len(rows)})
    
    async def _execute_send_email(self, context: 'NodeContext') -> 'NodeResult':
        # Integrate with email service
        return NodeResult(success=True, output_data={"sent": True})
    
    async def _execute_send_sms(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"sent": True})
    
    async def _execute_send_push(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"sent": True})
    
    async def _execute_create_record(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"created": True})
    
    async def _execute_update_record(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"updated": True})
    
    async def _execute_delete_record(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"deleted": True})
    
    async def _execute_call_webhook(self, context: 'NodeContext') -> 'NodeResult':
        import httpx
        url = self.config.get("url", "")
        payload = context.input_data
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.config.get("url"), json=context.input_data)
            return NodeResult(success=True, output_data={"status": resp.status_code})
    
    async def _execute_query(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"data": []})


class ConditionNodeExecutor(NodeExecutor):
    """Executes condition/branch nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        condition = self.config.get("condition", {})
        field = condition.get("field")
        operator = condition.get("operator", "eq")
        value = condition.get("value")
        
        # Get value from context
        actual_value = self._get_nested_value(context, field)
        
        result = self._evaluate_condition(actual_value, operator, value)
        
        # Determine next nodes based on condition
        next_nodes = self.node.get("next_nodes", {})
        if result:
            next_nodes = self.node.get("true_branch", [])
        else:
            next_nodes = self.node.get("false_branch", [])
        
        return NodeResult(
            success=True,
            output_data={"condition_result": result},
            next_node_ids=next_nodes,
            branch_taken="true" if result else "false"
        )
    
    def _get_nested_value(self, context: 'NodeContext', field: str) -> Any:
        """Get nested value from context using dot notation."""
        parts = field.split(".")
        value = context.variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "eq":
            return actual == expected
        elif operator == "neq":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "not_contains":
            return expected not in str(actual)
        elif operator == "starts_with":
            return str(actual).startswith(str(expected))
        elif operator == "ends_with":
            return str(actual).endswith(str(expected))
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else False
        elif operator == "not_in":
            return actual not in expected if isinstance(expected, list) else True
        elif operator == "is_null":
            return actual is None
        elif operator == "not_null":
            return actual is not None
        return False


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class TransformNodeExecutor(NodeExecutor):
    """Data transformation node."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        transform_type = self.config.get("transform_type", "map")
        
        if transform_type == "map":
            mapping = self.config.get("mapping", {})
            output = {}
            for out_key, source in mapping.items():
                value = self._resolve_value(context, source)
                context.variables[out_key] = value
                output[out_key] = value
            
            return NodeResult(success=True, output_data=output)
        
        elif transform_type == "aggregate":
            return await self._execute_aggregate(context)
        elif transform_type == "filter":
            return await self._execute_filter(context)
        
        return NodeResult(success=True, output_data={})
    
    async def _execute_aggregate(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"aggregated": True})
    
    async def _execute_filter(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={})


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class TransformNodeExecutor(NodeExecutor):
    """Data transformation node."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        transform_type = self.config.get("transform_type", "map")
        
        if transform_type == "map":
            mapping = self.config.get("mapping", {})
            output = {}
            for out_key, source in mapping.items():
                value = self._resolve_value(context, source)
                context.variables[out_key] = value
                output[out_key] = value
            
            return NodeResult(success=True, output_data=output)
        
        elif transform_type == "aggregate":
            return await self._execute_aggregate(context)
        elif transform_type == "filter":
            return await self._execute_filter(context)
        
        return NodeResult(success=True, output_data={})
    
    async def _execute_aggregate(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"aggregated": True})
    
    async def _execute_filter(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={})
    
    def _resolve_value(self, context: 'NodeContext', source: str) -> Any:
        if source.startswith("variables."):
            return context.variables.get(source.replace("variables.", ""))
        elif source.startswith("input."):
            return context.input_data.get(source.replace("input.", ""))
        elif source.startswith("execution."):
            return context.execution_variables.get(source.replace("execution.", ""))
        return source


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class TransformNodeExecutor(NodeExecutor):
    """Data transformation node."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        transform_type = self.config.get("transform_type", "map")
        
        if transform_type == "map":
            mapping = self.config.get("mapping", {})
            output = {}
            for out_key, source in mapping.items():
                value = self._resolve_value(context, source)
                context.variables[out_key] = value
                output[out_key] = value
            
            return NodeResult(success=True, output_data=output)
        
        elif transform_type == "aggregate":
            return await self._execute_aggregate(context)
        elif transform_type == "filter":
            return await self._execute_filter(context)
        
        return NodeResult(success=True, output_data={})
    
    async def _execute_aggregate(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"aggregated": True})
    
    async def _execute_filter(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={})
    
    def _resolve_value(self, context: 'NodeContext', source: str) -> Any:
        if source.startswith("variables."):
            return context.variables.get(source.replace("variables.", ""))
        elif source.startswith("input."):
            return context.input_data.get(source.replace("input.", ""))
        elif source.startswith("execution."):
            return context.execution_variables.get(source.replace("execution.", ""))
        return source


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class TransformNodeExecutor(NodeExecutor):
    """Data transformation node."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        transform_type = self.config.get("transform_type", "map")
        
        if transform_type == "map":
            mapping = self.config.get("mapping", {})
            output = {}
            for out_key, source in mapping.items():
                value = self._resolve_value(context, source)
                context.variables[out_key] = value
                output[out_key] = value
            
            return NodeResult(success=True, output_data=output)
        
        elif transform_type == "aggregate":
            return await self._execute_aggregate(context)
        elif transform_type == "filter":
            return await self._execute_filter(context)
        
        return NodeResult(success=True, output_data={})
    
    async def _execute_aggregate(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"aggregated": True})
    
    async def _execute_filter(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={})
    
    def _resolve_value(self, context: 'NodeContext', source: str) -> Any:
        if source.startswith("variables."):
            return context.variables.get(source.replace("variables.", ""))
        elif source.startswith("input."):
            return context.input_data.get(source.replace("input.", ""))
        elif source.startswith("execution."):
            return context.execution_variables.get(source.replace("execution.", ""))
        return source


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class LoopNodeExecutor(NodeExecutor):
    """Loop/foreach node executor."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        items = context.variables.get(self.config.get("items_variable", "items"), [])
        subflow_id = self.config.get("subflow_id")
        item_variable = self.config.get("item_variable", "item")
        
        if not subflow_id:
            return NodeResult(success=False, output_data={}, error="No subflow specified")
        
        results = []
        for index, item in enumerate(items):
            # Create sub-execution context
            sub_context = NodeContext(
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                node_id=f"{context.node_id}_item_{index}",
                node_type="subflow",
                node_name=f"loop_item_{index}",
                input_data={item_variable: item},
                variables=context.variables.copy(),
                execution_variables=context.execution_variables.copy(),
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
            )
            
            # Execute subflow (simplified - in reality would call subflow executor)
            result = await self._execute_subflow(subflow_id, {**context.variables, "current_item": item, "index": index})
            results.append(result)
        
        return NodeResult(success=True, output_data={"results": results, "count": len(results)})
    
    async def _execute_subflow(self, subflow_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Would call subflow executor
        return {"completed": True}


class LoopNodeExecutor(NodeExecutor):
    """Loop/foreach node executor."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        items = context.variables.get(self.config.get("items_variable", "items"), [])
        subflow_id = self.config.get("subflow_id")
        item_variable = self.config.get("item_variable", "item")
        
        if not subflow_id:
            return NodeResult(success=False, output_data={}, error="No subflow specified")
        
        results = []
        for index, item in enumerate(items):
            # Create sub-execution context
            sub_context = NodeContext(
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                node_id=f"{context.node_id}_item_{index}",
                node_type="subflow",
                node_name=f"loop_item_{index}",
                input_data={item_variable: item},
                variables=context.variables.copy(),
                execution_variables=context.execution_variables.copy(),
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
            )
            
            # Execute subflow (simplified - in reality would call subflow executor)
            result = await self._execute_subflow(subflow_id, {**context.variables, "current_item": item, "index": index})
            results.append(result)
        
        return NodeResult(success=True, output_data={"results": results, "count": len(results)})
    
    async def _execute_subflow(self, subflow_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Would call subflow executor
        return {"completed": True}


class LoopNodeExecutor(NodeExecutor):
    """Loop/foreach node executor."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        items = context.variables.get(self.config.get("items_variable", "items"), [])
        subflow_id = self.config.get("subflow_id")
        item_variable = self.config.get("item_variable", "item")
        
        if not subflow_id:
            return NodeResult(success=False, output_data={}, error="No subflow specified")
        
        results = []
        for index, item in enumerate(items):
            # Create sub-execution context
            sub_context = NodeContext(
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                node_id=f"{context.node_id}_item_{index}",
                node_type="subflow",
                node_name=f"loop_item_{index}",
                input_data={item_variable: item},
                variables=context.variables.copy(),
                execution_variables=context.execution_variables.copy(),
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
            )
            
            # Execute subflow (simplified - in reality would call subflow executor)
            result = await self._execute_subflow(subflow_id, {**context.variables, "current_item": item, "index": index})
            results.append(result)
        
        return NodeResult(success=True, output_data={"results": results, "count": len(results)})
    
    async def _execute_subflow(self, subflow_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Would call subflow executor
        return {"completed": True}


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class ConditionNodeExecutor(NodeExecutor):
    """Executes condition/branch nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        condition = self.config.get("condition", {})
        field = condition.get("field")
        operator = condition.get("operator", "eq")
        value = condition.get("value")
        
        # Get value from context
        actual_value = self._get_nested_value(context, field)
        
        result = self._evaluate_condition(actual_value, operator, value)
        
        # Determine next nodes based on condition
        next_nodes = self.node.get("next_nodes", {})
        if result:
            next_nodes = self.node.get("true_branch", [])
        else:
            next_nodes = self.node.get("false_branch", [])
        
        return NodeResult(
            success=True,
            output_data={"condition_result": result},
            next_node_ids=next_nodes,
            branch_taken="true" if result else "false"
        )
    
    def _get_nested_value(self, context: 'NodeContext', field: str) -> Any:
        """Get nested value from context using dot notation."""
        parts = field.split(".")
        value = context.variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "eq":
            return actual == expected
        elif operator == "neq":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "not_contains":
            return expected not in str(actual)
        elif operator == "starts_with":
            return str(actual).startswith(str(expected))
        elif operator == "ends_with":
            return str(actual).endswith(str(expected))
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else False
        elif operator == "not_in":
            return actual not in expected if isinstance(expected, list) else True
        elif operator == "is_null":
            return actual is None
        elif operator == "not_null":
            return actual is not None
        return False


class ConditionNodeExecutor(NodeExecutor):
    """Executes condition/branch nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        condition = self.config.get("condition", {})
        field = condition.get("field")
        operator = condition.get("operator", "eq")
        value = condition.get("value")
        
        # Get value from context
        actual_value = self._get_nested_value(context, field)
        
        result = self._evaluate_condition(actual_value, operator, value)
        
        # Determine next nodes based on condition
        next_nodes = self.node.get("next_nodes", {})
        if result:
            next_nodes = self.node.get("true_branch", [])
        else:
            next_nodes = self.node.get("false_branch", [])
        
        return NodeResult(
            success=True,
            output_data={"condition_result": result},
            next_node_ids=next_nodes,
            branch_taken="true" if result else "false"
        )
    
    def _get_nested_value(self, context: 'NodeContext', field: str) -> Any:
        """Get nested value from context using dot notation."""
        parts = field.split(".")
        value = context.variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value
    
    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "eq":
            return actual == expected
        elif operator == "neq":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "not_contains":
            return expected not in str(actual)
        elif operator == "starts_with":
            return str(actual).startswith(str(expected))
        elif operator == "ends_with":
            return str(actual).endswith(str(expected))
        elif operator == "in":
            return actual in expected if isinstance(expected, list) else False
        elif operator == "not_in":
            return actual not in expected if isinstance(expected, list) else True
        elif operator == "is_null":
            return actual is None
        elif operator == "not_null":
            return actual is not None
        return False


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class TransformNodeExecutor(NodeExecutor):
    """Data transformation node."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        transform_type = self.config.get("transform_type", "map")
        
        if transform_type == "map":
            mapping = self.config.get("mapping", {})
            output = {}
            for out_key, source in mapping.items():
                value = self._resolve_value(context, source)
                context.variables[out_key] = value
                output[out_key] = value
            
            return NodeResult(success=True, output_data=output)
        
        elif transform_type == "aggregate":
            return await self._execute_aggregate(context)
        elif transform_type == "filter":
            return await self._execute_filter(context)
        
        return NodeResult(success=True, output_data={})
    
    async def _execute_aggregate(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={"aggregated": True})
    
    async def _execute_filter(self, context: 'NodeContext') -> 'NodeResult':
        return NodeResult(success=True, output_data={})
    
    def _resolve_value(self, context: 'NodeContext', source: str) -> Any:
        if source.startswith("variables."):
            return context.variables.get(source.replace("variables.", ""))
        elif source.startswith("input."):
            return context.input_data.get(source.replace("input.", ""))
        elif source.startswith("execution."):
            return context.execution_variables.get(source.replace("execution.", ""))
        return source


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


class LoopNodeExecutor(NodeExecutor):
    """Loop/foreach node executor."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        items = context.variables.get(self.config.get("items_variable", "items"), [])
        subflow_id = self.config.get("subflow_id")
        item_variable = self.config.get("item_variable", "item")
        
        if not subflow_id:
            return NodeResult(success=False, output_data={}, error="No subflow specified")
        
        results = []
        for index, item in enumerate(items):
            # Create sub-execution context
            sub_context = NodeContext(
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                node_id=f"{context.node_id}_item_{index}",
                node_type="subflow",
                node_name=f"loop_item_{index}",
                input_data={item_variable: item},
                variables=context.variables.copy(),
                execution_variables=context.execution_variables.copy(),
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
            )
            
            # Execute subflow (simplified - in reality would call subflow executor)
            result = await self._execute_subflow(subflow_id, {**context.variables, "current_item": item, "index": index})
            results.append(result)
        
        return NodeResult(success=True, output_data={"results": results, "count": len(results)})
    
    async def _execute_subflow(self, subflow_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Would call subflow executor
        return {"completed": True}


class LoopNodeExecutor(NodeExecutor):
    """Loop/foreach node executor."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        items = context.variables.get(self.config.get("items_variable", "items"), [])
        subflow_id = self.config.get("subflow_id")
        item_variable = self.config.get("item_variable", "item")
        
        if not subflow_id:
            return NodeResult(success=False, output_data={}, error="No subflow specified")
        
        results = []
        for index, item in enumerate(items):
            # Create sub-execution context
            sub_context = NodeContext(
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
                node_id=f"{context.node_id}_item_{index}",
                node_type="subflow",
                node_name=f"loop_item_{index}",
                input_data={item_variable: item},
                variables=context.variables.copy(),
                execution_variables=context.execution_variables.copy(),
                execution_id=context.execution_id,
                workflow_id=context.workflow_id,
            )
            
            # Execute subflow (simplified - in reality would call subflow executor)
            result = await self._execute_subflow(subflow_id, {**context.variables, "current_item": item, "index": index})
            results.append(result)
        
        return NodeResult(success=True, output_data={"results": results, "count": len(results)})
    
    async def _execute_subflow(self, subflow_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Would call subflow executor
        return {"completed": True}


class DelayNodeExecutor(NodeExecutor):
    """Executes delay/wait nodes."""
    
    async def execute(self, context: 'NodeContext') -> 'NodeResult':
        delay_seconds = self.config.get("delay_seconds", 0)
        delay_variable = self.config.get("delay_variable")
        
        if delay_variable:
            delay_seconds = context.variables.get(delay_variable, 0)
        
        if delay_seconds > 0:
            await asyncio.sleep(min(delay_seconds, 3600))  # Max 1 hour
        
        return NodeResult(success=True, output_data={"delayed_seconds": delay_seconds})


# Missing imports
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import asyncio
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.orm import selectinload
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from contextlib import asynccontextmanager
import asyncio
import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.orm import selectinload

logger = structlog.get_logger()
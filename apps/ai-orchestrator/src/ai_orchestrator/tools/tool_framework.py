"""
Tool Framework for AI Orchestrator

Provides a framework for defining, registering, and executing tools that
agents can use to interact with external systems.

Tools are callable functions with typed parameters that agents can invoke
through the LLM's function calling interface.
"""

import asyncio
import inspect
import json
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

from ..config import get_ai_orchestrator_settings
from ..models import ToolDefinition

import logging
logger = logging.getLogger("ai-orchestrator.tools")


class Tool:
    """
    Base class for tools that agents can call.
    
    Tools encapsulate external capabilities like HTTP requests,
    database queries, file operations, etc.
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        category: str = "custom",
        required_permissions: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        retryable: bool = True,
        idempotent: bool = False,
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.category = category
        self.required_permissions = required_permissions or []
        self.timeout_seconds = timeout_seconds
        self.retryable = retryable
        self.idempotent = idempotent
        self._handler = handler
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters."""
        self.execution_count += 1
        start_time = datetime.utcnow()

        try:
            if self._handler:
                if asyncio.iscoroutinefunction(self._handler):
                    result = await self._handler(parameters)
                else:
                    result = self._handler(parameters)
            else:
                raise ValueError(f"Tool {self.name} has no handler")

            self.success_count += 1
            return result
        except Exception as e:
            self.failure_count += 1
            logger.error(
                "tool_execution_error",
                tool_name=self.name,
                error=str(e),
            )
            raise
        finally:
            self.total_latency_ms += int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
            "required_permissions": self.required_permissions,
            "timeout_seconds": self.timeout_seconds,
            "retryable": self.retryable,
            "idempotent": self.idempotent,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_latency_ms": self.total_latency_ms,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_llm_tool_definition(self) -> Dict[str, Any]:
        """Convert tool to LLM function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param["name"]] = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if param.get("required", False):
                required.append(param["name"])

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """
    Registry for managing tool definitions and execution.
    
    Provides tool registration, discovery, execution, and lifecycle management.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool
        self._categories[tool.category].append(tool.name)
        logger.info(
            "tool_registered",
            tool_name=tool.name,
            category=tool.category,
        )

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool."""
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            self._categories[tool.category].remove(tool.name)
            del self._tools[tool_name]
            logger.info("tool_unregistered", tool_name=tool_name)

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def find_tools(self, query: str) -> List[Tool]:
        """Find tools matching a query string."""
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.description.lower()
                or query_lower in tool.category.lower()
            ):
                results.append(tool)
        return results

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute a tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        return await tool.execute(parameters)

    def to_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tools as LLM function calling definitions."""
        return [tool.to_llm_tool_definition() for tool in self._tools.values()]

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "tools_by_category": {
                category: len(tools)
                for category, tools in self._categories.items()
            },
            "total_executions": sum(t.execution_count for t in self._tools.values()),
            "total_successes": sum(t.success_count for t in self._tools.values()),
            "total_failures": sum(t.failure_count for t in self._tools.values()),
        }


# Built-in tool implementations

class HTTPRequestTool(Tool):
    """Tool for making HTTP requests."""

    def __init__(self):
        super().__init__(
            name="http_request",
            description="Make HTTP requests to external APIs",
            parameters=[
                {
                    "name": "url",
                    "type": "string",
                    "description": "URL to make request to",
                    "required": True,
                },
                {
                    "name": "method",
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                    "required": False,
                    "default": "GET",
                },
                {
                    "name": "headers",
                    "type": "object",
                    "description": "HTTP headers",
                    "required": False,
                },
                {
                    "name": "body",
                    "type": "object",
                    "description": "Request body for POST/PUT/PATCH",
                    "required": False,
                },
                {
                    "name": "timeout",
                    "type": "number",
                    "description": "Request timeout in seconds",
                    "required": False,
                    "default": 30,
                },
            ],
            category="data_access",
        )
        import httpx
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        import httpx
        method = parameters.get("method", "GET").upper()
        url = parameters["url"]
        headers = parameters.get("headers", {})
        body = parameters.get("body")
        timeout = parameters.get("timeout", 30)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if method in ("POST", "PUT", "PATCH") else None,
            )
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
            }


class WebSearchTool(Tool):
    """Tool for web search."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information",
            parameters=[
                {
                    "name": "query",
                    "type": "string",
                    "description": "Search query",
                    "required": True,
                },
                {
                    "name": "num_results",
                    "type": "number",
                    "description": "Number of results to return",
                    "required": False,
                    "default": 5,
                },
            ],
            category="search",
        )

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        # This is a placeholder - in production, integrate with a search API
        query = parameters.get("query", "")
        num_results = parameters.get("num_results", 5)
        return {
            "query": query,
            "results": [
                {
                    "title": f"Result {i+1} for {query}",
                    "url": f"https://example.com/search?q={query}",
                    "snippet": f"Search result {i+1} for {query}",
                }
                for i in range(num_results)
            ],
        }


class CalculatorTool(Tool):
    """Tool for mathematical calculations."""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform mathematical calculations",
            parameters=[
                {
                    "name": "expression",
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                    "required": True,
                },
            ],
            category="computation",
        )

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        import math
        expression = parameters["expression"]
        # Safe eval - only allow math operations
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("_")
        }
        allowed_names["abs"] = abs
        allowed_names["round"] = round
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": result}


class FileReadTool(Tool):
    """Tool for reading files."""

    def __init__(self):
        super().__init__(
            name="file_read",
            description="Read file contents",
            parameters=[
                {
                    "name": "file_path",
                    "type": "string",
                    "description": "Path to file to read",
                    "required": True,
                },
            ],
            category="file_operation",
        )

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        import aiofiles
        file_path = parameters["file_path"]
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()
        return {"file_path": file_path, "content": content}


class FileWriteTool(Tool):
    """Tool for writing files."""

    def __init__(self):
        super().__init__(
            name="file_write",
            description="Write content to a file",
            parameters=[
                {
                    "name": "file_path",
                    "type": "string",
                    "description": "Path to write file to",
                    "required": True,
                },
                {
                    "name": "content",
                    "type": "string",
                    "description": "Content to write",
                    "required": True,
                },
            ],
            category="file_operation",
        )

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        import aiofiles
        file_path = parameters["file_path"]
        content = parameters["content"]
        async with aiofiles.open(file_path, "w") as f:
            await f.write(content)
        return {"file_path": file_path, "bytes_written": len(content)}


# Tool Registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        # Register built-in tools
        _tool_registry.register(HTTPRequestTool())
        _tool_registry.register(WebSearchTool())
        _tool_registry.register(CalculatorTool())
        _tool_registry.register(FileReadTool())
        _tool_registry.register(FileWriteTool())
        logger.info("tool_registry_initialized", tool_count=len(_tool_registry._tools))
    return _tool_registry
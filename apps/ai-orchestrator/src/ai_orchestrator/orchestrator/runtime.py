"""
Agent Runtime Engine - Core execution engine for AI agents

Provides:
- Agent lifecycle management (idle -> running -> completed/failed)
- Tool calling with execution sandbox
- Skill execution with retries and fallback
- Execution tracing and observability
- Context management across iterations
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, cast

from ..config import get_ai_orchestrator_settings
from ..models import (
    AgentConfig,
    AgentState,
    AgentResult,
    AgentStatus,
    AgentTask,
    LLMMessage,
    ToolDefinition,
)

logger = __import__("logging").getLogger("ai-orchestrator.runtime")


class AgentRuntimeError(Exception):
    """Base exception for agent runtime errors"""
    pass


class AgentTimeoutError(AgentRuntimeError):
    """Raised when agent execution exceeds timeout"""
    pass


class AgentSafetyError(AgentRuntimeError):
    """Raised when agent violates safety constraints"""
    pass


class AgentRuntime:
    """
    Core agent execution engine.

    Manages the full lifecycle of an agent task:
    1. Initialize agent context from configuration
    2. Execute iteration loop (thinking -> tool calling -> result processing)
    3. Handle errors and retries
    4. Track execution trace and token usage
    5. Finalize and return results
    """

    def __init__(
        self,
        agent_config: AgentConfig,
        llm_provider=None,
        skill_registry=None,
        tool_registry=None,
        memory_manager=None,
        max_iterations: Optional[int] = None,
        max_tool_calls_per_iteration: Optional[int] = None,
        execution_timeout_seconds: Optional[int] = None,
    ):
        self.config = agent_config
        self.agent_id = agent_config.agent_id
        self.llm_provider = llm_provider
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager

        # Runtime settings from config with overrides
        self.max_iterations = max_iterations or agent_config.max_iterations
        self.max_tool_calls_per_iteration = max_tool_calls_per_iteration or agent_config.max_tool_calls_per_iteration
        self.execution_timeout_seconds = execution_timeout_seconds or agent_config.execution_timeout_seconds

        # Runtime state
        self.state: Optional[AgentState] = None
        self._is_running = False
        self._should_stop = False
        self._start_time: Optional[datetime] = None
        self._completion_time: Optional[datetime] = None

        # Event callbacks for observability
        self._on_iteration_start: list = []
        self._on_iteration_end: list = []
        self._on_tool_call: list = []
        self._on_skill_execution: list = []
        self._on_error: list = []

    async def start(self) -> None:
        """Initialize the runtime for execution."""
        self.state = AgentState(
            agent_id=self.agent_id,
            status=AgentStatus.IDLE,
            context={},
            conversation_history=[],
        )
        self._is_running = True
        self._should_stop = False
        self._start_time = datetime.utcnow()
        logger.info("agent_runtime_started", agent_id=self.agent_id, name=self.config.name)

    async def stop(self) -> None:
        """Stop the agent runtime gracefully."""
        self._should_stop = True
        self._is_running = False
        logger.info("agent_runtime_stopped", agent_id=self.agent_id)

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a complete agent task.

        This is the main entry point for agent execution.
        """
        if self._is_running:
            raise AgentRuntimeError("Agent is already running")

        await self.start()

        try:
            return await self._execute_task(task)
        finally:
            await self.stop()

    async def _execute_task(self, task: AgentTask) -> AgentResult:
        """Core task execution loop."""
        # Initialize state
        self.state = AgentState(
            agent_id=self.agent_id,
            status=AgentStatus.RUNNING,
            context=task.context.copy(),
            conversation_history=[],
        )
        self._start_time = datetime.utcnow()

        # Build system prompt from agent config
        system_message = LLMMessage(
            role="system",
            content=self.config.system_prompt or f"You are a {self.config.role} agent. Help the user complete their task.",
        )
        self.state.conversation_history.append(system_message)

        # Track execution
        total_tokens = 0
        total_latency_ms = 0

        try:
            # Main execution loop
            for iteration in range(self.max_iterations):
                self.state.current_iteration = iteration + 1

                # Check if we should stop
                if self._should_stop:
                    self.state.status = AgentStatus.CANCELLED
                    break

                # Emit iteration start event
                self._emit_iteration_start(iteration + 1)

                # Step 1: Call LLM to get next action
                llm_response = await self._call_llm(
                    messages=self.state.conversation_history,
                    tools=self._get_available_tools(),
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )

                # Track token usage
                if llm_response.usage:
                    total_tokens += llm_response.usage.get("total_tokens", 0)
                self.state.total_latency_ms += llm_response.latency_ms

                # Add assistant message to conversation
                assistant_msg = LLMMessage(
                    role="assistant",
                    content=llm_response.content or "",
                    tool_calls=llm_response.tool_calls,
                )
                self.state.conversation_history.append(assistant_msg)

                # Check if we should stop based on finish_reason
                if llm_response.finish_reason == "stop":
                    self.state.status = AgentStatus.COMPLETED
                    break

                # Step 2: Execute tool calls if any
                if llm_response.tool_calls:
                    tool_call_results = await self._execute_tool_calls(llm_response.tool_calls)
                    self.state.tool_calls.extend(cast(List[Any], tool_call_results))

                    # Add tool results to conversation
                    for tc_result in tool_call_results:
                        tool_msg = LLMMessage(
                            role="tool",
                            content=str(tc_result.get("result", "")),
                            tool_call_id=tc_result.get("id", ""),
                            name=tc_result.get("name", ""),
                        )
                        self.state.conversation_history.append(tool_msg)

                    # Check if we hit max tool calls per iteration
                    if len(tool_call_results) >= self.max_tool_calls_per_iteration:
                        logger.warning(
                            "max_tool_calls_reached",
                            agent_id=self.agent_id,
                            count=len(tool_call_results),
                        )
                        break

                else:
                    # No tool calls - agent is done or needs more thinking
                    # If there's content but no tool calls, the agent might be done
                    if llm_response.content and llm_response.content.strip():
                        # Check if it looks like a final answer
                        if self._is_final_answer(llm_response.content):
                            self.state.status = AgentStatus.COMPLETED
                            break

                # Emit iteration end event
                await self._emit_iteration_end(iteration + 1)

            # Finalize
            self._completion_time = datetime.utcnow()

            if self.state.status == AgentStatus.RUNNING:
                # Max iterations reached
                self.state.status = AgentStatus.FAILED
                self.state.error = "Max iterations reached without completion"

            # Build result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status=self.state.status,
                output=self.state.conversation_history[-1].content if self.state.conversation_history else "",
                error=self.state.error,
                iterations=self.state.current_iteration,
                tokens_used=total_tokens,
                latency_ms=int((self._completion_time - self._start_time).total_seconds() * 1000),
                tool_calls=self.state.tool_calls,
                skill_executions=[],
                started_at=self._start_time,
                completed_at=self._completion_time,
            )

            logger.info(
                "agent_task_completed",
                agent_id=self.agent_id,
                task_id=task.task_id,
                status=self.state.status.value,
                iterations=self.state.current_iteration,
                tokens_used=total_tokens,
            )

            return result

        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)
            logger.error("agent_task_failed", agent_id=self.agent_id, error=str(e), exc_info=True)

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                error=str(e),
                iterations=self.state.current_iteration if self.state else 0,
                tokens_used=total_tokens,
                latency_ms=int((datetime.utcnow() - self._start_time).total_seconds() * 1000) if self._start_time else 0,
                tool_calls=self.state.tool_calls if self.state else [],
                skill_executions=[],
                started_at=self._start_time or datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )

    async def _call_llm(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Call the LLM provider."""
        if self.llm_provider is None:
            raise AgentRuntimeError("No LLM provider configured")

        # Get skills as tool definitions if available
        skill_tools = []
        if self.skill_registry:
            for skill_id in self.config.skills:
                skill = self.skill_registry.get_skill(skill_id)
                if skill:
                    tool_def = skill.to_tool_definition()
                    if tool_def:
                        skill_tools.append(tool_def)

        # Merge with provided tools
        all_tools = tools or []
        if skill_tools:
            all_tools.extend(skill_tools)

        # Convert LLMMessage objects to dict for LLM provider
        messages_dict = [msg.model_dump() for msg in messages]

        return await self.llm_provider.complete(
            messages=messages_dict,
            tools=all_tools if all_tools else None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls in parallel."""
        results = []

        async def execute_single_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            tool_call_id = tool_call.get("id", "")

            try:
                # Try skills first, then tools
                result = await self._execute_skill(tool_name, tool_args)
                if result is not None:
                    return {
                        "id": tool_call_id,
                        "name": tool_name,
                        "result": result,
                        "status": "completed",
                    }
            except Exception:
                pass  # Fall through to tool registry

            try:
                result = await self._execute_tool(tool_name, tool_args)
                return {
                    "id": tool_call_id,
                    "name": tool_name,
                    "result": result,
                    "status": "completed",
                }
            except Exception as e:
                return {
                    "id": tool_call_id,
                    "name": tool_name,
                    "result": None,
                    "error": str(e),
                    "status": "failed",
                }

        # Execute all tool calls concurrently
        tasks = [execute_single_tool(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tc = tool_calls[i]
                final_results.append({
                    "id": tc.get("id", ""),
                    "name": tc.get("function", {}).get("name", ""),
                    "result": None,
                    "error": str(result),
                    "status": "failed",
                })
            else:
                final_results.append(result)

        return final_results

    async def _execute_skill(self, skill_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """Execute a skill by name."""
        if not self.skill_registry:
            return None

        skill = self.skill_registry.get_skill(skill_name)
        if not skill:
            return None

        result = skill.execute(args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """Execute a tool by name."""
        if not self.tool_registry:
            return None

        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return None

        return await tool.execute(args)

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools as LLM function definitions."""
        tools = []

        # Get tool definitions from tool registry
        if self.tool_registry:
            for tool in self.tool_registry.get_all_tools():
                if hasattr(tool, 'to_dict'):
                    tools.append(tool.to_dict())
                elif isinstance(tool, dict):
                    tools.append(tool)
                else:
                    tools.append(tool.__dict__ if hasattr(tool, '__dict__') else str(tool))

        # Get skill definitions as tools
        if self.skill_registry:
            for skill in self.skill_registry.get_all_skills():
                tool_def = skill.to_tool_definition()
                if tool_def:
                    tools.append(tool_def)

        return tools

    def _is_final_answer(self, content: str) -> bool:
        """Check if the LLM response is a final answer."""
        # Simple heuristic - check for common final answer patterns
        content_lower = content.lower().strip()
        final_indicators = [
            "final answer:",
            "answer:",
            "conclusion:",
            "in summary:",
            "to summarize:",
            "the answer is",
            "final result:",
        ]
        return any(indicator in content_lower for indicator in final_indicators)

    def _emit_iteration_start(self, iteration: int) -> None:
        """Emit iteration start event."""
        for handler in self._on_iteration_start:
            try:
                handler(iteration, self.state)
            except Exception:
                pass

    async def _emit_iteration_end(self, iteration: int) -> None:
        """Emit iteration end event."""
        for handler in self._on_iteration_end:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(iteration, self.state)
                else:
                    handler(iteration, self.state)
            except Exception:
                pass

    # Event handler registration
    def on_iteration_start(self, handler: Callable[[int, AgentState], None]) -> None:
        self._on_iteration_start.append(handler)

    def on_iteration_end(self, handler: Callable[[int, AgentState], None]) -> None:
        self._on_iteration_end.append(handler)

    def on_tool_call(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._on_tool_call.append(handler)

    def on_skill_execution(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._on_skill_execution.append(handler)

    def on_error(self, handler: Callable[[str, Exception], None]) -> None:
        self._on_error.append(handler)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_state(self) -> Optional[AgentState]:
        return self.state


class AgentRuntimeManager:
    """
    Manages multiple agent runtimes.

    Provides:
    - Agent lifecycle management (create, start, stop, delete)
    - Runtime pooling for efficiency
    - Health monitoring
    """

    def __init__(self):
        self._runtimes: Dict[str, AgentRuntime] = {}
        self._configs: Dict[str, AgentConfig] = {}
        self._llm_providers: Dict[str, Any] = {}
        self._skill_registry = None
        self._tool_registry = None
        self._memory_manager = None

    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent configuration."""
        self._configs[config.agent_id] = config
        logger.info("agent_registered", agent_id=config.agent_id, name=config.name)

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent configuration."""
        if agent_id in self._runtimes:
            await self._runtimes[agent_id].stop()
            del self._runtimes[agent_id]
        if agent_id in self._configs:
            del self._configs[agent_id]
        logger.info("agent_unregistered", agent_id=agent_id)

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration."""
        return self._configs.get(agent_id)

    def get_runtime(self, agent_id: str) -> Optional[AgentRuntime]:
        """Get agent runtime."""
        return self._runtimes.get(agent_id)

    async def start_agent(self, agent_id: str) -> AgentRuntime:
        """Start an agent runtime."""
        if agent_id in self._runtimes:
            return self._runtimes[agent_id]

        config = self._configs.get(agent_id)
        if not config:
            raise ValueError(f"Agent {agent_id} not registered")

        runtime = AgentRuntime(
            agent_config=config,
            llm_provider=self._llm_providers.get(config.agent_id),
            skill_registry=self._skill_registry,
            tool_registry=self._tool_registry,
            memory_manager=self._memory_manager,
        )
        await runtime.start()
        self._runtimes[agent_id] = runtime
        logger.info("agent_runtime_started", agent_id=agent_id)
        return runtime

    async def stop_agent(self, agent_id: str) -> None:
        """Stop an agent runtime."""
        runtime = self._runtimes.get(agent_id)
        if runtime:
            await runtime.stop()
            del self._runtimes[agent_id]
            logger.info("agent_runtime_stopped", agent_id=agent_id)

    async def execute_task(self, agent_id: str, task: AgentTask) -> AgentResult:
        """Execute a task on an agent."""
        runtime = self._runtimes.get(agent_id)
        if not runtime:
            runtime = await self.start_agent(agent_id)
        return await runtime.execute(task)

    async def stop_all(self) -> None:
        """Stop all agent runtimes."""
        for agent_id in list(self._runtimes.keys()):
            await self.stop_agent(agent_id)

    def set_llm_provider(self, agent_id: str, provider: Any) -> None:
        """Set LLM provider for an agent."""
        self._llm_providers[agent_id] = provider

    def set_skill_registry(self, registry: Any) -> None:
        """Set skill registry for all agents."""
        self._skill_registry = registry

    def set_tool_registry(self, registry: Any) -> None:
        """Set tool registry for all agents."""
        self._tool_registry = registry

    def set_memory_manager(self, manager: Any) -> None:
        """Set memory manager for all agents."""
        self._memory_manager = manager

    @property
    def running_agents(self) -> List[str]:
        """Get list of running agent IDs."""
        return [
            agent_id
            for agent_id, runtime in self._runtimes.items()
            if runtime.is_running
        ]

    @property
    def stats(self) -> Dict[str, Any]:
        """Get runtime manager statistics."""
        return {
            "total_agents": len(self._configs),
            "running_agents": len(self.running_agents),
            "agent_ids": list(self._configs.keys()),
        }


# Global runtime manager instance
_runtime_manager: Optional[AgentRuntimeManager] = None


def get_agent_runtime_manager() -> AgentRuntimeManager:
    """Get or create the global agent runtime manager."""
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = AgentRuntimeManager()
    return _runtime_manager
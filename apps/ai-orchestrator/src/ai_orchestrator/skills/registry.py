"""
Skill Registry for AI Orchestrator

Manages skill registration, discovery, execution, and auto-training.
Skills are modular capabilities that agents can use to perform specific tasks.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import importlib
import inspect

from ..config import get_ai_orchestrator_settings
from ..models import (
    SkillDefinition,
    SkillExecution,
    SkillType,
)

import logging
logger = logging.getLogger("ai-orchestrator.skills")


class Skill:
    """
    Base class for AI Orchestrator skills.
    
    Skills are modular capabilities that agents can use to perform
    specific tasks (e.g., web search, database query, image generation).
    """

    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        skill_type: SkillType = SkillType.CUSTOM,
        version: str = "1.0.0",
        parameters: Optional[List[Dict[str, Any]]] = None,
        required_params: Optional[List[str]] = None,
        system_prompt: str = "",
        user_prompt_template: str = "",
        examples: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        allowed_tools: Optional[List[str]] = None,
        required_context: Optional[List[str]] = None,
        auto_training_enabled: bool = False,
        min_training_samples: int = 100,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.version = version
        self.parameters = parameters or []
        self.required_params = required_params or []
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.examples = examples or []
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.allowed_tools = allowed_tools or []
        self.required_context = required_context or []
        self.auto_training_enabled = auto_training_enabled
        self.min_training_samples = min_training_samples
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0

    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the skill with given parameters."""
        self.execution_count += 1
        start_time = datetime.utcnow()

        try:
            result = await self._execute(parameters)
            self.success_count += 1
            return result
        except Exception as e:
            self.failure_count += 1
            logger.error(
                "skill_execution_error",
                skill_id=self.skill_id,
                skill_name=self.name,
                error=str(e),
            )
            raise
        finally:
            self.total_latency_ms += int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.updated_at = datetime.utcnow()

    async def _execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the skill logic. Override in subclasses."""
        raise NotImplementedError("Skill.execute() not implemented")

    def to_tool_definition(self) -> Optional[Dict[str, Any]]:
        """Convert skill to LLM tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.skill_id,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p["name"]: {
                            "type": p["type"],
                            "description": p["description"],
                        }
                        for p in self.parameters
                    },
                    "required": self.required_params,
                },
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary representation."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type.value,
            "version": self.version,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "examples": self.examples,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "allowed_tools": self.allowed_tools,
            "required_context": self.required_context,
            "auto_training_enabled": self.auto_training_enabled,
            "min_training_samples": self.min_training_samples,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_latency_ms": self.total_latency_ms,
        }


class SkillRegistry:
    """
    Registry for managing skill definitions and execution.
    
    Provides skill registration, discovery, execution tracking,
    and auto-training capabilities.
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_categories: Dict[SkillType, List[str]] = defaultdict(list)
        self._training_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._execution_history: List[Dict[str, Any]] = []

    def register(self, skill: Skill) -> None:
        """Register a skill in the registry."""
        self._skills[skill.skill_id] = skill
        self._skill_categories[skill.skill_type].append(skill.skill_id)
        logger.info(
            "skill_registered",
            skill_id=skill.skill_id,
            name=skill.name,
            type=skill.skill_type.value,
        )

    def unregister(self, skill_id: str) -> None:
        """Unregister a skill."""
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            self._skill_categories[skill.skill_type].remove(skill_id)
            del self._skills[skill_id]
            logger.info("skill_unregistered", skill_id=skill_id)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def get_all_skills(self) -> List[Skill]:
        """Get all registered skills."""
        return list(self._skills.values())

    def get_skills_by_type(self, skill_type: SkillType) -> List[Skill]:
        """Get all skills of a specific type."""
        skill_ids = self._skill_categories.get(skill_type, [])
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def find_skills(self, query: str) -> List[Skill]:
        """Find skills matching a query string."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or query_lower in skill.skill_type.value.lower()
            ):
                results.append(skill)
        return results

    async def execute_skill(
        self,
        skill_id: str,
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute a skill by ID."""
        skill = self._skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        return await skill.execute(parameters)

    def record_training_data(
        self,
        skill_id: str,
        input_params: Dict[str, Any],
        expected_output: Any,
        quality_score: float = 1.0,
        source: str = "agent",
        tags: Optional[List[str]] = None,
    ) -> None:
        """Record training data for a skill."""
        self._training_data[skill_id].append({
            "input_params": input_params,
            "expected_output": expected_output,
            "quality_score": quality_score,
            "source": source,
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat(),
        })

    def get_training_data(
        self,
        skill_id: str,
    ) -> List[Dict[str, Any]]:
        """Get training data for a skill."""
        return self._training_data.get(skill_id, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_skills": len(self._skills),
            "skills_by_type": {
                st.value: len(ids)
                for st, ids in self._skill_categories.items()
            },
            "total_executions": sum(s.execution_count for s in self._skills.values()),
            "total_successes": sum(s.success_count for s in self._skills.values()),
            "total_failures": sum(s.failure_count for s in self._skills.values()),
        }


# Global skill registry instance
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
"""Tools - built-in tools and tool registry."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from shared.agent_runtime import ToolRegistry


def register_builtin_tools(registry: ToolRegistry, data_dir: str):
    """Register built-in tools for all assistants."""

    @registry.register("read_file")
    def read_file(path: str) -> str:
        full_path = Path(data_dir) / path
        if not full_path.exists():
            return f"File not found: {path}"
        return full_path.read_text()

    @registry.register("write_file")
    def write_file(path: str, content: str) -> str:
        full_path = Path(data_dir) / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return f"Written to {path}"

    @registry.register("list_files")
    def list_files(path: str = ".") -> list[str]:
        full_path = Path(data_dir) / path
        if not full_path.exists():
            return []
        return [str(p.relative_to(data_dir)) for p in full_path.rglob("*") if p.is_file()]

    @registry.register("run_command")
    def run_command(cmd: str, cwd: str = ".") -> str:
        allowed = ["ls", "cat", "grep", "find", "python", "pip", "git", "docker", "curl", "wget"]
        if not any(cmd.startswith(a) for a in allowed):
            return "Command not allowed"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=Path(data_dir) / cwd)
            return result.stdout or result.stderr
        except Exception as e:
            return f"Error: {e}"

    @registry.register("web_search")
    def web_search(query: str) -> str:
        return f"Search results for: {query} (not implemented)"

    @registry.register("remember")
    def remember(key: str, value: str, category: str = "general") -> str:
        # This would integrate with MemoryStore
        return f"Remembered: {key} = {value}"

    @registry.register("recall")
    def recall(query: str) -> str:
        return f"Recall for: {query} (not implemented)"


def create_tool_registry(data_dir: str) -> "ToolRegistry":
    from shared.agent_runtime import ToolRegistry
    registry = ToolRegistry()
    register_builtin_tools(registry, data_dir)
    return registry
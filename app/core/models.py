"""Model Management - UI-controllable model selection and management."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from shared.llm.ollama_adapter import OllamaAdapter


@dataclass
class ModelInfo:
    name: str
    size: str
    modified: str
    digest: str
    details: dict = field(default_factory=dict)
    source: str = "ollama"  # ollama, huggingface, custom


class ModelManager:
    """Manages LLM models - listing, pulling, switching, via UI/API."""

    def __init__(self, ollama: OllamaAdapter, data_dir: str):
        self.ollama = ollama
        self.data_dir = Path(data_dir)
        self._current_model: str | None = None

    async def list_installed(self) -> list[ModelInfo]:
        """List locally installed models."""
        try:
            models = await self.ollama.list_models()
            result = []
            for m in models:
                result.append(ModelInfo(
                    name=m.get("name", ""),
                    size=self._format_size(m.get("size", 0)),
                    modified=m.get("modified_at", ""),
                    digest=m.get("digest", "")[:12],
                    details=m.get("details", {}),
                ))
            return result
        except Exception:
            return []

    async def list_available(self) -> list[ModelInfo]:
        """List popular available models from Ollama library."""
        # Curated list of popular models with metadata
        popular = [
            ModelInfo(name="llama3.2:3b", size="2.0 GB", modified="", digest="",
                      details={"family": "llama", "parameter_size": "3B", "quantization": "Q4_K_M"},
                      description="Fast, capable general purpose"),
            ModelInfo(name="llama3.2:1b", size="1.3 GB", modified="", digest="",
                      details={"family": "llama", "parameter_size": "1B", "quantization": "Q4_K_M"},
                      description="Ultra-fast, good for simple tasks"),
            ModelInfo(name="llama3.1:8b", size="4.7 GB", modified="", digest="",
                      details={"family": "llama", "parameter_size": "8B", "quantization": "Q4_K_M"},
                      description="Stronger reasoning, larger context"),
            ModelInfo(name="llama3.1:70b", size="40 GB", modified="", digest="",
                      details={"family": "llama", "parameter_size": "70B", "quantization": "Q4_K_M"},
                      description="Maximum capability, needs lots of RAM"),
            ModelInfo(name="mistral:7b", size="4.1 GB", modified="", digest="",
                      details={"family": "mistral", "parameter_size": "7B", "quantization": "Q4_K_M"},
                      description="Strong coding, multilingual"),
            ModelInfo(name="mistral-nemo:12b", size="7.1 GB", modified="", digest="",
                      details={"family": "mistral", "parameter_size": "12B", "quantization": "Q4_K_M"},
                      description="Large context window (128k)"),
            ModelInfo(name="codellama:7b", size="3.8 GB", modified="", digest="",
                      details={"family": "codellama", "parameter_size": "7B", "quantization": "Q4_K_M"},
                      description="Code-specialized"),
            ModelInfo(name="codellama:13b", size="7.3 GB", modified="", digest="",
                      details={"family": "codellama", "parameter_size": "13B", "quantization": "Q4_K_M"},
                      description="Stronger code generation"),
            ModelInfo(name="phi3:mini", size="2.3 GB", modified="", digest="",
                      details={"family": "phi", "parameter_size": "3.8B", "quantization": "Q4_K_M"},
                      description="Microsoft small, fast, good reasoning"),
            ModelInfo(name="phi3:medium", size="7.9 GB", modified="", digest="",
                      details={"family": "phi", "parameter_size": "14B", "quantization": "Q4_K_M"},
                      description="Stronger phi variant"),
            ModelInfo(name="gemma2:2b", size="1.6 GB", modified="", digest="",
                      details={"family": "gemma", "parameter_size": "2B", "quantization": "Q4_K_M"},
                      description="Google small, fast"),
            ModelInfo(name="gemma2:9b", size="5.5 GB", modified="", digest="",
                      details={"family": "gemma", "parameter_size": "9B", "quantization": "Q4_K_M"},
                      description="Google medium, strong multilingual"),
            ModelInfo(name="llava:7b", size="4.5 GB", modified="", digest="",
                      details={"family": "llava", "parameter_size": "7B", "quantization": "Q4_K_M"},
                      description="Vision + language (images)"),
            ModelInfo(name="llava:13b", size="8 GB", modified="", digest="",
                      details={"family": "llava", "parameter_size": "13B", "quantization": "Q4_K_M"},
                      description="Stronger vision model"),
            ModelInfo(name="nemotron3:8b", size="4.7 GB", modified="", digest="",
                      details={"family": "nemotron", "parameter_size": "8B", "quantization": "Q4_K_M"},
                      description="NVIDIA Nemotron 3 Ultra - strong reasoning"),
            ModelInfo(name="qwen2.5:7b", size="4.4 GB", modified="", digest="",
                      details={"family": "qwen", "parameter_size": "7B", "quantization": "Q4_K_M"},
                      description="Alibaba Qwen 2.5 - strong multilingual"),
        ]
        return popular

    async def pull_model(self, name: str) -> dict:
        """Pull a model from Ollama library."""
        try:
            result = await self.ollama.pull_model(name)
            return {"status": "success", "model": name, "details": result}
        except Exception as e:
            return {"status": "error", "model": name, "error": str(e)}

    async def remove_model(self, name: str) -> dict:
        """Remove a local model."""
        try:
            await self.ollama.remove_model(name)
            return {"status": "success", "model": name}
        except Exception as e:
            return {"status": "error", "model": name, "error": str(e)}

    async def set_current(self, name: str) -> dict:
        """Set current model for new conversations."""
        # Verify model exists
        installed = await self.list_installed()
        if not any(m.name == name for m in installed):
            return {"status": "error", "message": f"Model {name} not installed. Pull it first."}

        self._current_model = name
        return {"status": "success", "current_model": name}

    def get_current(self) -> str | None:
        return self._current_model

    def _format_size(self, bytes_size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    async def pull_from_huggingface(self, repo_id: str, quantization: str = "Q4_K_M") -> dict:
        """Pull a GGUF model from Hugging Face Hub."""
        # This would use ollama pull hf.co/...
        model_ref = f"hf.co/{repo_id}:{quantization}"
        return await self.pull_model(model_ref)

    async def create_custom_model(self, name: str, base_model: str, system_prompt: str, temperature: float = 0.7) -> dict:
        """Create a custom Modelfile-based model."""
        modelfile = f"""FROM {base_model}
SYSTEM {system_prompt}
PARAMETER temperature {temperature}
"""
        try:
            result = await self.ollama.create_model(name, modelfile)
            return {"status": "success", "model": name, "details": result}
        except Exception as e:
            return {"status": "error", "model": name, "error": str(e)}


def create_model_manager(ollama: OllamaAdapter, data_dir: str) -> "ModelManager":
    return ModelManager(ollama, data_dir)
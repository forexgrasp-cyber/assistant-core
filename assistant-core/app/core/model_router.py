"""Universal Model Router - routes requests to best model (any provider, any modality).
Uses shared canonical model catalog from shared.model_catalog."""

from __future__ import annotations

import httpx
from shared.model_catalog import (
    Modality,
    Provider,
    ModelCapability,
    ModelRegistry,
    get_registry,
)
from shared.llm.ollama_adapter import OllamaAdapter


class OllamaProvider:
    """Ollama provider using shared OllamaAdapter."""

    def __init__(self, base_url: str = "http://localhost:11437"):
        self.base_url = base_url

    async def list_models(self) -> list[ModelCapability]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()

            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                details = m.get("details", {})

                modality = Modality.TEXT
                tags = ["local"]
                if "code" in name.lower() or "code" in details.get("family", "").lower():
                    modality = Modality.CODE
                    tags.append("code")
                elif "vision" in name.lower() or "llava" in name.lower() or "bakllava" in name.lower():
                    modality = Modality.VISION
                    tags.append("vision")
                elif "embed" in name.lower():
                    modality = Modality.EMBEDDING
                    tags.append("embeddings")

                models.append(ModelCapability(
                    model_id=f"ollama/{name}",
                    display_name=name.split(":")[0],
                    provider=Provider.OLLAMA,
                    modality=modality,
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_streaming=True,
                    description=f"Ollama local model: {name}",
                    input_cost_per_1k=0,
                    output_cost_per_1k=0,
                    is_custom=True,
                ))
            return models

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def generate(self, capability: ModelCapability, prompt: str, **kwargs):
        adapter = OllamaAdapter(base_url=self.base_url)
        return await adapter.generate(prompt, model=capability.model_id.split("/")[-1], **kwargs)

    async def stream(self, capability: ModelCapability, prompt: str, **kwargs):
        adapter = OllamaAdapter(base_url=self.base_url)
        async for chunk in adapter.stream(prompt, model=capability.model_id.split("/")[-1], **kwargs):
            yield chunk


# Backward-compat aliases
get_model_registry = get_registry


async def initialize_registry() -> ModelRegistry:
    """Initialize shared registry with Ollama provider for dynamic model fetching."""
    reg = get_registry()
    reg.ensure_initialized()
    return reg
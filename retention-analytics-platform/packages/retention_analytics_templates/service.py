"""Template service.

Renders MJML email templates with Jinja2 context variables and registers a
``templates.render`` action into the ``ServiceRegistry`` so workflows can
render a template before sending it via the engagement service.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from jinja2 import Template
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class TemplateService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._templates: dict[str, str] = {}
        self._load_templates()
        registry.register(name="templates", version="0.1.0")
        registry.register_action("templates", "render", self._render)

    def _load_templates(self) -> None:
        for path in _TEMPLATES_DIR.glob("*.mjml"):
            self._templates[path.stem] = path.read_text(encoding="utf-8")
        logger.info("templates.loaded", count=len(self._templates), names=list(self._templates))

    def list_templates(self) -> list[str]:
        return sorted(self._templates.keys())

    async def _render(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("template")
        context = payload.get("context", {})
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        html = Template(self._templates[name]).render(**context)
        logger.info("template.rendered", template=name)
        return {
            "status": "rendered",
            "template": name,
            "html": html,
        }


__all__ = ["TemplateService"]

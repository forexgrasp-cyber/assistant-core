"""Configuration loading."""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

_config = None


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "assistants.yaml"

    with open(config_path, "r") as f:
        _config = yaml.safe_load(f)

    return _config


def get_config() -> dict[str, Any]:
    """Get loaded configuration."""
    if _config is None:
        return load_config()
    return _config


def get_tenant_config(tenant_id: str) -> dict | None:
    """Get tenant configuration by ID."""
    config = get_config()
    for tenant in config.get("tenants", []):
        if tenant.get("id") == tenant_id:
            return tenant
    return None


def get_assistant_config(tenant_id: str, assistant_id: str) -> dict | None:
    """Get assistant configuration by tenant and assistant ID."""
    tenant_config = get_tenant_config(tenant_id)
    if not tenant_config:
        return None
    for assistant in tenant_config.get("assistants", []):
        if assistant.get("id") == assistant_id:
            return assistant
    return None


def get_vertical_config(vertical: str) -> dict | None:
    """Get vertical configuration."""
    config = get_config()
    return config.get("business", {}).get("verticals", {}).get(vertical)


def get_billing_tiers() -> dict:
    """Get billing tiers."""
    config = get_config()
    return config.get("billing", {}).get("tiers", {})


def get_global_settings() -> dict:
    """Get global settings."""
    config = get_config()
    return config.get("global", {})
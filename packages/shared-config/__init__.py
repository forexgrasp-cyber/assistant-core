"""
Shared configuration integration for retention-analytics-platform.

This module provides a unified configuration layer that integrates with
shared-canonical-services while allowing project-specific overrides.
"""

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
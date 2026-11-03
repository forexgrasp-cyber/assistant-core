"""Import smoke test: verify every module in the project imports cleanly.

Run as part of the pre-push gate. Unexpected import-time failures are
regressions that must be fixed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Ensure the project root is on sys.path so namespace packages (apps/, packages/)
# resolve correctly regardless of how PYTHONPATH is set.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Known importable modules (apps/ and packages/ are namespace packages,
# not filesystem-discoverable packages).
MODULES = [
    "retention_analytics_core",
    "retention_analytics_core.auth",
    "retention_analytics_core.database",
    "retention_analytics_core.entities.kernel",
    "retention_analytics_core.middleware",
    "retention_analytics_core.models",
    "retention_analytics_core.permissions",
    "retention_analytics_core.service_registry",
    "retention_analytics_core.workflows.engine",
    "retention_analytics_engagement",
    "retention_analytics_engagement.base",
    "retention_analytics_engagement.email.service",
    "retention_analytics_engagement.flows.triggers",
    "retention_analytics_engagement.push.service",
    "retention_analytics_engagement.sms.service",
    "retention_analytics_ecommerce",
    "retention_analytics_ecommerce.core.service",
    "retention_analytics_ecommerce.subscriptions.service",
    "retention_analytics_analytics_core",
    "retention_analytics_analytics_core.cohort_service",
    "retention_analytics_analytics_core.metric_service",
    "retention_analytics_reporting_engine",
    "retention_analytics_reporting_engine.report_service",
    "retention_analytics_shared_config",
    "retention_analytics_shared_types",
    "retention_analytics_vertical_packs",
    "retention_analytics_vertical_packs.ecommerce",
    "retention_analytics_vertical_packs.fintech",
    "retention_analytics_vertical_packs.healthcare",
    "retention_analytics_vertical_packs.marketing",
    "retention_analytics_vertical_packs.saas",
    "retention_analytics_templates",
    "retention_analytics_templates.service",
    "apps.api.main",
    "apps.workers.celery_app",
    "apps.workers.tasks",
    "apps.mcp_server.main",
]

failed: list[tuple[str, str]] = []
for mod in MODULES:
    try:
        importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001
        failed.append((mod, str(exc)[:200]))

print(f"Imported {len(MODULES)} modules, {len(failed)} failed")  # noqa: T201
for mod, err in failed:
    print(f"  FAIL {mod}: {err}")  # noqa: T201

sys.exit(1 if failed else 0)

"""Root conftest for the retention-analytics-platform test suite.

Consumes shared testing infrastructure from shared-canonical-services
(TESTING_STANDARDS.md §7.5 — consume, never fork). ``pytest_plugins`` must be
declared here (rootdir conftest), not in subdirectory conftests.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make shared-canonical-services importable for shared.testing.*
_ROOT = Path(__file__).resolve().parent
_SHARED = _ROOT.parent / "shared-canonical-services"
for _p in (str(_ROOT), str(_SHARED)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Only load shared testing plugins that actually exist in this checkout.
_plugins: list[str] = []
for _plug in ("shared.testing.conftest", "shared.testing.playwright.conftest"):
    try:
        __import__(_plug)
        _plugins.append(_plug)
    except ImportError:
        pass

pytest_plugins = _plugins

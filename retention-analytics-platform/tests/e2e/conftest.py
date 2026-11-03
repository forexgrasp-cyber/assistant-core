# E2E test configuration
# Shared fixtures come from the root conftest (pytest_plugins = ["shared.testing.conftest"]).

import pytest

pytestmark = pytest.mark.e2e

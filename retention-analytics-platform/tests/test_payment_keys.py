"""Tests for env-filtered payment provider listing."""

from __future__ import annotations

from retention_analytics_core.payment_keys import (
    PROVIDER_ENV_KEYS,
    configured_providers,
    is_test_key,
    provider_status_map,
)


def test_is_test_key() -> None:
    assert is_test_key("sk_test_abc123")
    assert is_test_key("pk_test_abc")
    assert not is_test_key("sk_live_abc")
    assert not is_test_key("")


def test_configured_providers_only_with_keys() -> None:
    # nothing set -> nothing configured
    assert configured_providers({}) == []
    # stripe test key in dev -> stripe listed
    env = {"STRIPE_SECRET_KEY": "sk_test_abc", "ENVIRONMENT": "development"}
    assert configured_providers(env) == ["stripe"]
    # stripe live key -> listed
    env = {"STRIPE_SECRET_KEY": "sk_live_abc"}
    assert configured_providers(env) == ["stripe"]
    # paypal keys -> paypal listed too
    env = {"STRIPE_SECRET_KEY": "sk_test_x", "PAYPAL_CLIENT_ID": "abc", "PAYPAL_CLIENT_SECRET": "def"}
    result = configured_providers(env)
    assert "stripe" in result and "paypal" in result


def test_production_excludes_test_keys() -> None:
    # In production a sk_test_ key must NOT enable the provider
    env = {"STRIPE_SECRET_KEY": "sk_test_abc", "ENVIRONMENT": "production"}
    assert configured_providers(env) == []
    env = {"STRIPE_SECRET_KEY": "sk_live_abc", "ENVIRONMENT": "production"}
    assert configured_providers(env) == ["stripe"]


def test_all_21_providers_have_env_mapping() -> None:
    assert len(PROVIDER_ENV_KEYS) >= 21
    for provider, keys in PROVIDER_ENV_KEYS.items():
        assert keys, f"{provider} has no env key mapping"


def test_provider_status_map() -> None:
    env = {"STRIPE_SECRET_KEY": "sk_test_x", "PAYPAL_CLIENT_ID": "abc"}
    m = provider_status_map(env)
    assert m["stripe"]["configured"] is True
    assert m["stripe"]["keys"]["STRIPE_SECRET_KEY"] is True
    assert m["paypal"]["configured"] is True
    assert m["adyen"]["configured"] is False

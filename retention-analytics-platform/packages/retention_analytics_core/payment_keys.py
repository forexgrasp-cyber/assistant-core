"""Payment provider credential map: which env vars configure each provider.

Only providers with at least one key set in the environment / .env are listed
as available payment options at runtime. In dev/test, Stripe test keys
(sk_test_... / pk_test_...) count as configured.
"""

from __future__ import annotations

import os

# provider -> env vars that configure it (any one set = configured)
PROVIDER_ENV_KEYS: dict[str, list[str]] = {
    "stripe": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"],
    "paypal": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"],
    "paddle": ["PADDLE_API_KEY", "PADDLE_VENDOR_ID"],
    "adyen": ["ADYEN_API_KEY", "ADYEN_MERCHANT_ACCOUNT"],
    "airwallex": ["AIRWALLEX_API_KEY", "AIRWALLEX_CLIENT_ID"],
    "creem": ["CREEM_API_KEY"],
    "dodo": ["DODO_API_KEY"],
    "fastspring": ["FASTSPRING_API_KEY", "FASTSPRING_STORE_ID"],
    "freemius": ["FREEMIUS_API_KEY", "FREEMIUS_PRODUCT_ID"],
    "fondy": ["FONDY_MERCHANT_ID", "FONDY_SECRET_KEY"],
    "liqpay": ["LIQPAY_PUBLIC_KEY", "LIQPAY_PRIVATE_KEY"],
    "wayforpay": ["WAYFORPAY_MERCHANT_ACCOUNT", "WAYFORPAY_SECRET_KEY"],
    "novapay": ["NOVAPAY_API_KEY"],
    "rozetkapay": ["ROZETKAPAY_KEY"],
    "verifone": ["VERIFONE_API_KEY", "VERIFONE_TERMINAL_ID"],
    "mono": ["MONO_PUBLIC_KEY", "MONO_SECRET_KEY"],
    "payoneer_checkout": ["PAYONEER_API_KEY"],
    "paypro_global": ["PAYPRO_API_KEY"],
    "bank_transfer": ["BANK_TRANSFER_ENABLED"],
    "cash": ["CASH_ENABLED"],
    "cryptocurrency": ["CRYPTO_WALLET_ADDRESS"],
}


def is_test_key(value: str) -> bool:
    """Stripe-style test keys (sk_test_/pk_test_) count as configured in any env."""
    return value.startswith(("sk_test_", "pk_test_", "whsec_test_"))


def configured_providers(env: dict[str, str] | None = None) -> list[str]:
    """Return only providers that have at least one credential in the environment.

    In development/test, Stripe test keys (sk_test_/pk_test_) count. In production,
    test keys do NOT count — only live keys (sk_live_/pk_live_) enable a provider.
    """
    env = env if env is not None else dict(os.environ)
    is_prod = env.get("ENVIRONMENT", "development") == "production"
    configured = []
    for provider, keys in PROVIDER_ENV_KEYS.items():
        for k in keys:
            v = env.get(k, "")
            if not v:
                continue
            if is_prod and is_test_key(v):
                continue  # test keys never enable a provider in production
            configured.append(provider)
            break
    return configured


def provider_status_map(env: dict[str, str] | None = None) -> dict[str, dict[str, bool]]:
    """Per-provider: which env keys are set, and whether it is usable now."""
    env = env if env is not None else dict(os.environ)
    out: dict[str, dict[str, bool]] = {}
    for provider, keys in PROVIDER_ENV_KEYS.items():
        set_keys = {k: bool(env.get(k)) for k in keys}
        out[provider] = {"configured": any(set_keys.values()), "keys": set_keys}
    return out


__all__ = ["PROVIDER_ENV_KEYS", "configured_providers", "provider_status_map", "is_test_key"]

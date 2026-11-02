"""
Application configuration — extends the canonical shared settings.

Inherits database/security/redis/CORS/admin-notify settings from
``shared.config.settings.Settings`` (_shared-canonical-services_), so env
names stay consistent across every project (DATABASE_URL, SECRET_KEY,
REDIS_URL, ...). Only the VA-matching-specific fields live here.
"""

from __future__ import annotations

from typing import Optional

from shared.config.settings import Settings as BaseSettings


class Settings(BaseSettings):
    """VA Matching Platform settings (canonical base + project extras)."""

    # App identity (override canonical defaults)
    app_name: str = "va-matching-platform"

    # Database defaults (project database; env DATABASE_URL wins)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching"
    DB_ECHO: bool = False

    # Marketplace economics
    PLATFORM_FEE_RATE: float = 0.20
    MONTHLY_PLATFORM_FEE: float = 200.00
    PLACEMENT_FEE_REFUND_WINDOW_DAYS: int = 14
    VETTING_MIN_SCORE: float = 0.6

    # Onboarding/delivery
    ONBOARDING_TRIAL_DAYS: int = 14
    MONTHLY_FEE_TRIAL_DAYS: int = 14

    # VA payout rails (Stripe Connect)
    CONNECT_RETURN_URL: str = "https://localhost/payout/onboarding/complete"
    CONNECT_REFRESH_URL: str = "https://localhost/payout/onboarding/refresh"

    # Email notifications (feeds canonical shared.communications EmailConfig)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@va-matching.local"
    EMAIL_FROM_NAME: str = "VA Matching Platform"

    # External sourcing APIs — OAuth credentials
    UPWORK_CLIENT_ID: Optional[str] = None
    UPWORK_CLIENT_SECRET: Optional[str] = None
    UPWORK_REDIRECT_URI: Optional[str] = None
    FIVERR_CLIENT_ID: Optional[str] = None
    FIVERR_CLIENT_SECRET: Optional[str] = None
    FIVERR_REDIRECT_URI: Optional[str] = None
    TOPTAL_CLIENT_ID: Optional[str] = None
    TOPTAL_CLIENT_SECRET: Optional[str] = None
    TOPTAL_REDIRECT_URI: Optional[str] = None

    # Payment providers — multi-provider support via UnifiedPaymentService
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLIC_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    # Gumroad
    GUMROAD_ACCESS_TOKEN: Optional[str] = None
    GUMROAD_APPLICATION_ID: Optional[str] = None
    GUMROAD_APPLICATION_SECRET: Optional[str] = None
    GUMROAD_WEBHOOK_SECRET: Optional[str] = None
    # LemonSqueezy
    LEMONSQUEEZY_API_KEY: Optional[str] = None
    LEMONSQUEEZY_STORE_ID: Optional[str] = None
    LEMONSQUEEZY_WEBHOOK_SECRET: Optional[str] = None
    # PayPal
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    PAYPAL_SANDBOX: bool = True

    # Payment provider preferences
    DEFAULT_PAYMENT_PROVIDER: str = "stripe"  # stripe, gumroad, lemonsqueezy, paypal
    SUPPORTED_PAYMENT_PROVIDERS: str = "stripe,gumroad,lemonsqueezy,paypal"


def get_settings() -> Settings:
    """Build settings; canonical base fields come from env, extras from env too."""
    return Settings()


settings = get_settings()

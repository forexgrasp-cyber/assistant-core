"""
Configuration management for retention-analytics-platform.

Integrates with shared.config from shared-canonical-services while providing
project-specific settings.
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add shared-canonical-services to path for imports
import sys
SHARED_PATH = Path(__file__).parent.parent.parent.parent / "shared-canonical-services"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from shared.config import Config as SharedConfig
    from shared.config_service import ConfigService
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False
    SharedConfig = object
    ConfigService = object


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/retention_analytics", alias="DATABASE_URL")
    pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")

    model_config = SettingsConfigDict(extra="ignore")


class RedisSettings(BaseSettings):
    """Redis configuration."""
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

    model_config = SettingsConfigDict(extra="ignore")


class ClickHouseSettings(BaseSettings):
    """ClickHouse analytics warehouse configuration."""
    host: str = Field(default="localhost", alias="CLICKHOUSE_HOST")
    port: int = Field(default=8123, alias="CLICKHOUSE_PORT")
    user: str = Field(default="default", alias="CLICKHOUSE_USER")
    password: str = Field(default="", alias="CLICKHOUSE_PASSWORD")
    database: str = Field(default="retention_analytics", alias="CLICKHOUSE_DATABASE")
    secure: bool = Field(default=False, alias="CLICKHOUSE_SECURE")

    @property
    def dsn(self) -> str:
        auth = f"{self.user}:{self.password}@" if self.password else f"{self.user}@"
        return f"clickhouse+http://{auth}{self.host}:{self.port}/{self.database}"

    model_config = SettingsConfigDict(extra="ignore")


class AuthSettings(BaseSettings):
    """Authentication configuration."""
    secret_key: str = Field(alias="AUTH_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="AUTH_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="AUTH_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="AUTH_REFRESH_TOKEN_EXPIRE_DAYS")

    # WorkOS
    workos_api_key: Optional[str] = Field(default=None, alias="WORKOS_API_KEY")
    workos_client_id: Optional[str] = Field(default=None, alias="WORKOS_CLIENT_ID")
    workos_redirect_uri: Optional[str] = Field(default=None, alias="WORKOS_REDIRECT_URI")
    workos_cookie_password: Optional[str] = Field(default=None, alias="WORKOS_COOKIE_PASSWORD")

    model_config = SettingsConfigDict(extra="ignore")


class BillingSettings(BaseSettings):
    """Billing/Stripe configuration."""
    stripe_secret_key: str = Field(alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_monthly_per_client: str = Field(alias="STRIPE_PRICE_MONTHLY_PER_CLIENT")
    stripe_price_seat: str = Field(alias="STRIPE_PRICE_SEAT")
    trial_days: int = Field(default=30, alias="STRIPE_TRIAL_DAYS")

    model_config = SettingsConfigDict(extra="ignore")


class PlatformOAuthSettings(BaseSettings):
    """OAuth credentials for all supported platforms."""
    
    # Klaviyo
    klaviyo_client_id: Optional[str] = Field(default=None, alias="KLAVIYO_CLIENT_ID")
    klaviyo_client_secret: Optional[str] = Field(default=None, alias="KLAVIYO_CLIENT_SECRET")
    klaviyo_redirect_uri: Optional[str] = Field(default=None, alias="KLAVIYO_REDIRECT_URI")

    # Attentive
    attentive_client_id: Optional[str] = Field(default=None, alias="ATTENTIVE_CLIENT_ID")
    attentive_client_secret: Optional[str] = Field(default=None, alias="ATTENTIVE_CLIENT_SECRET")
    attentive_redirect_uri: Optional[str] = Field(default=None, alias="ATTENTIVE_REDIRECT_URI")

    # Postscript
    postscript_client_id: Optional[str] = Field(default=None, alias="POSTSCRIPT_CLIENT_ID")
    postscript_client_secret: Optional[str] = Field(default=None, alias="POSTSCRIPT_CLIENT_SECRET")
    postscript_redirect_uri: Optional[str] = Field(default=None, alias="POSTSCRIPT_REDIRECT_URI")

    # Omnisend
    omnisend_client_id: Optional[str] = Field(default=None, alias="OMNISEND_CLIENT_ID")
    omnisend_client_secret: Optional[str] = Field(default=None, alias="OMNISEND_CLIENT_SECRET")
    omnisend_redirect_uri: Optional[str] = Field(default=None, alias="OMNISEND_REDIRECT_URI")

    # Sendlane
    sendlane_client_id: Optional[str] = Field(default=None, alias="SENDLANE_CLIENT_ID")
    sendlane_client_secret: Optional[str] = Field(default=None, alias="SENDLANE_CLIENT_SECRET")
    sendlane_redirect_uri: Optional[str] = Field(default=None, alias="SENDLANE_REDIRECT_URI")

    # Shopify
    shopify_api_key: Optional[str] = Field(default=None, alias="SHOPIFY_API_KEY")
    shopify_api_secret: Optional[str] = Field(default=None, alias="SHOPIFY_API_SECRET")
    shopify_redirect_uri: Optional[str] = Field(default=None, alias="SHOPIFY_REDIRECT_URI")
    shopify_scopes: str = Field(default="read_orders,read_customers,read_products,read_fulfillments", alias="SHOPIFY_SCOPES")

    # Recharge
    recharge_client_id: Optional[str] = Field(default=None, alias="RECHARGE_CLIENT_ID")
    recharge_client_secret: Optional[str] = Field(default=None, alias="RECHARGE_CLIENT_SECRET")
    recharge_redirect_uri: Optional[str] = Field(default=None, alias="RECHARGE_REDIRECT_URI")

    # Skio
    skio_client_id: Optional[str] = Field(default=None, alias="SKIO_CLIENT_ID")
    skio_client_secret: Optional[str] = Field(default=None, alias="SKIO_CLIENT_SECRET")
    skio_redirect_uri: Optional[str] = Field(default=None, alias="SKIO_REDIRECT_URI")

    # Loop
    loop_client_id: Optional[str] = Field(default=None, alias="LOOP_CLIENT_ID")
    loop_client_secret: Optional[str] = Field(default=None, alias="LOOP_CLIENT_SECRET")
    loop_redirect_uri: Optional[str] = Field(default=None, alias="LOOP_REDIRECT_URI")

    # Stay AI
    stay_ai_client_id: Optional[str] = Field(default=None, alias="STAY_AI_CLIENT_ID")
    stay_ai_client_secret: Optional[str] = Field(default=None, alias="STAY_AI_CLIENT_SECRET")
    stay_ai_redirect_uri: Optional[str] = Field(default=None, alias="STAY_AI_REDIRECT_URI")

    # Ordergroove
    ordergroove_client_id: Optional[str] = Field(default=None, alias="ORDERGROOVE_CLIENT_ID")
    ordergroove_client_secret: Optional[str] = Field(default=None, alias="ORDERGROOVE_CLIENT_SECRET")
    ordergroove_redirect_uri: Optional[str] = Field(default=None, alias="ORDERGROOVE_REDIRECT_URI")

    # Alia
    alia_client_id: Optional[str] = Field(default=None, alias="ALIA_CLIENT_ID")
    alia_client_secret: Optional[str] = Field(default=None, alias="ALIA_CLIENT_SECRET")
    alia_redirect_uri: Optional[str] = Field(default=None, alias="ALIA_REDIRECT_URI")

    # Slack
    slack_client_id: Optional[str] = Field(default=None, alias="SLACK_CLIENT_ID")
    slack_client_secret: Optional[str] = Field(default=None, alias="SLACK_CLIENT_SECRET")
    slack_signing_secret: Optional[str] = Field(default=None, alias="SLACK_SIGNING_SECRET")
    slack_redirect_uri: Optional[str] = Field(default=None, alias="SLACK_REDIRECT_URI")

    def get_platform_config(self, platform: str) -> dict:
        """Get OAuth config for a specific platform."""
        platform = platform.lower()
        mapping = {
            "klaviyo": ("klaviyo_client_id", "klaviyo_client_secret", "klaviyo_redirect_uri"),
            "attentive": ("attentive_client_id", "attentive_client_secret", "attentive_redirect_uri"),
            "postscript": ("postscript_client_id", "postscript_client_secret", "postscript_redirect_uri"),
            "omnisend": ("omnisend_client_id", "omnisend_client_secret", "omnisend_redirect_uri"),
            "sendlane": ("sendlane_client_id", "sendlane_client_secret", "sendlane_redirect_uri"),
            "shopify": ("shopify_api_key", "shopify_api_secret", "shopify_redirect_uri"),
            "recharge": ("recharge_client_id", "recharge_client_secret", "recharge_redirect_uri"),
            "skio": ("skio_client_id", "skio_client_secret", "skio_redirect_uri"),
            "loop": ("loop_client_id", "loop_client_secret", "loop_redirect_uri"),
            "stay-ai": ("stay_ai_client_id", "stay_ai_client_secret", "stay_ai_redirect_uri"),
            "ordergroove": ("ordergroove_client_id", "ordergroove_client_secret", "ordergroove_redirect_uri"),
            "alia": ("alia_client_id", "alia_client_secret", "alia_redirect_uri"),
            "slack": ("slack_client_id", "slack_client_secret", "slack_redirect_uri"),
        }
        if platform not in mapping:
            return {}
        cid, csecret, redirect = mapping[platform]
        return {
            "client_id": getattr(self, cid),
            "client_secret": getattr(self, csecret),
            "redirect_uri": getattr(self, redirect),
        }

    model_config = SettingsConfigDict(extra="ignore")


class EncryptionSettings(BaseSettings):
    """Encryption settings for credentials at rest."""
    encryption_key: str = Field(alias="ENCRYPTION_KEY")
    kms_key_id: Optional[str] = Field(default=None, alias="KMS_KEY_ID")

    model_config = SettingsConfigDict(extra="ignore")


class AlertingSettings(BaseSettings):
    """Alerting configuration (ntfy)."""
    topic: str = Field(default="retention-analytics-alerts", alias="NTFY_TOPIC")
    url: str = Field(default="https://ntfy.sh", alias="NTFY_URL")

    model_config = SettingsConfigDict(extra="ignore")


class MonitoringSettings(BaseSettings):
    """Monitoring configuration."""
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    datadog_api_key: Optional[str] = Field(default=None, alias="DATADOG_API_KEY")
    datadog_app_key: Optional[str] = Field(default=None, alias="DATADOG_APP_KEY")

    model_config = SettingsConfigDict(extra="ignore")


class AISettings(BaseSettings):
    """AI/MCP configuration."""
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    vector_db_path: str = Field(default="./data/chroma", alias="VECTOR_DB_PATH")
    enable_mcp: bool = Field(default=True, alias="ENABLE_MCP")

    model_config = SettingsConfigDict(extra="ignore")


class ReportingSettings(BaseSettings):
    """Reporting/PDF generation configuration."""
    playwright_browser_path: str = Field(default="/usr/bin/chromium", alias="PLAYWRIGHT_BROWSER_PATH")
    report_template_path: str = Field(default="./apps/api/templates/reports", alias="REPORT_TEMPLATE_PATH")

    model_config = SettingsConfigDict(extra="ignore")


class FileStorageSettings(BaseSettings):
    """File storage (S3) configuration."""
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket: str = Field(alias="S3_BUCKET")
    s3_raw_prefix: str = Field(default="raw/", alias="S3_RAW_PREFIX")
    s3_reports_prefix: str = Field(default="reports/", alias="S3_REPORTS_PREFIX")

    model_config = SettingsConfigDict(extra="ignore")


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""
    requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    model_config = SettingsConfigDict(extra="ignore")


class FeatureFlags(BaseSettings):
    """Feature flags."""
    enable_mcp: bool = Field(default=True, alias="ENABLE_MCP")
    enable_whitelabel: bool = Field(default=True, alias="ENABLE_WHITELABEL")
    enable_slack: bool = Field(default=True, alias="ENABLE_SLACK")
    enable_ai_summaries: bool = Field(default=True, alias="ENABLE_AI_SUMMARIES")

    model_config = SettingsConfigDict(extra="ignore")


class SyncSettings(BaseSettings):
    """Data sync configuration."""
    schedule_cron: str = Field(default="0 0 * * *", alias="SYNC_SCHEDULE_CRON")
    backfill_days: int = Field(default=365, alias="SYNC_BACKFILL_DAYS")
    chunk_days: int = Field(default=7, alias="SYNC_CHUNK_DAYS")
    max_retries: int = Field(default=3, alias="SYNC_MAX_RETRIES")
    retry_delay: int = Field(default=300, alias="SYNC_RETRY_DELAY")

    model_config = SettingsConfigDict(extra="ignore")


class AttributionSettings(BaseSettings):
    """Attribution engine configuration."""
    click_window_email: int = Field(default=7, alias="ATTRIBUTION_CLICK_WINDOW_EMAIL")
    click_window_sms: int = Field(default=1, alias="ATTRIBUTION_CLICK_WINDOW_SMS")
    click_window_push: int = Field(default=1, alias="ATTRIBUTION_CLICK_WINDOW_PUSH")
    open_window_email: int = Field(default=1, alias="ATTRIBUTION_OPEN_WINDOW_EMAIL")
    channel_priority: str = Field(default="email,sms,push", alias="ATTRIBUTION_CHANNEL_PRIORITY")

    @property
    def channel_priority_list(self) -> List[str]:
        return [c.strip() for c in self.channel_priority.split(",")]

    model_config = SettingsConfigDict(extra="ignore")


class AppSettings(BaseSettings):
    """Main application settings."""
    name: str = Field(default="Retention Analytics Platform", alias="APP_NAME")
    env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="APP_DEBUG")
    url: str = Field(default="http://localhost:8766", alias="APP_URL")
    api_url: str = Field(default="http://localhost:8765", alias="API_URL")
    mcp_url: str = Field(default="http://localhost:8767", alias="MCP_URL")
    tenant_header: str = Field(default="x-agency-slug", alias="TENANT_HEADER")
    default_tenant: str = Field(default="demo", alias="DEFAULT_TENANT")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    clickhouse: ClickHouseSettings = Field(default_factory=ClickHouseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    billing: BillingSettings = Field(default_factory=BillingSettings)
    platform_oauth: PlatformOAuthSettings = Field(default_factory=PlatformOAuthSettings)
    encryption: EncryptionSettings = Field(default_factory=EncryptionSettings)
    alerting: AlertingSettings = Field(default_factory=AlertingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    ai: AISettings = Field(default_factory=AISettings)
    reporting: ReportingSettings = Field(default_factory=ReportingSettings)
    file_storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    sync: SyncSettings = Field(default_factory=SyncSettings)
    attribution: AttributionSettings = Field(default_factory=AttributionSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        nested_model_default_partial_update=True,
    )

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in ("development", "staging", "production"):
            raise ValueError("APP_ENV must be development, staging, or production")
        return v

    def is_production(self) -> bool:
        return self.env == "production"

    def is_development(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> AppSettings:
    """Get cached settings instance."""
    return AppSettings()


# Initialize shared config service if available
_shared_config_service: Optional[ConfigService] = None


def get_shared_config_service() -> Optional[ConfigService]:
    """Get shared config service instance."""
    global _shared_config_service
    if not SHARED_AVAILABLE:
        return None
    if _shared_config_service is None:
        try:
            _shared_config_service = ConfigService()
        except Exception:
            pass
    return _shared_config_service


def get_shared_config() -> Optional[SharedConfig]:
    """Get shared config instance."""
    service = get_shared_config_service()
    if service:
        return service.get_config()
    return None
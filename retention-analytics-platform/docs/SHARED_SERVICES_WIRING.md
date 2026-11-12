# Shared Canonical Services Wiring Audit

Date: 2026-11-12. Question: do we consume `shared-canonical-services/shared/*` or reimplement locally?

## Verdict: canonical infrastructure IS consumed from shared.* — 29 modules

We do NOT reimplement canonical cross-cutting capabilities locally. Every
infrastructure concern delegates to the shared package:

| Capability | Consumed from | Used in |
|-----------|---------------|---------|
| Secrets management | `shared.production.secrets` | `retention_analytics_core/canonical.py` |
| Idempotency ledger | `shared.idempotency.idempotency_ledger` | `canonical.py` |
| Immutable audit log | `shared.audit.immutable_audit_log` | `canonical.py` |
| Sliding-window rate limit | `shared.rate_limit.sliding_window` | `middleware.py` |
| Metrics collector | `shared.production.metrics` | `middleware.py`, `canonical.py` |
| Health checker | `shared.production.health` | `canonical.py` |
| Retry handler | `shared.production.retry` | `canonical.py` |
| Config service | `shared.config_service` | `canonical.py` |
| Tenant-isolated persistence | `shared.database.persistence_service` | `repository.py` |
| Multi-tenancy context | `shared.multitenancy.context` | core |
| Observability context | `shared.observability.context` | `middleware.py` |
| Resilient HTTP client | `shared.http_client.resilient_http_client` | core |
| Base service | `shared.base.base_service` | `service_base.py` |
| Feature flags | `shared.feature_flags.service` + `.store` | `platform_services.py` |
| Quota / metering / entitlements | `shared.billing.quota_integration_service`, `.metering`, `.entitlements_service` | `platform_services.py` |
| Sessions | `shared.auth.session_service` | `platform_services.py` |
| User profile | `shared.profile` | `platform_services.py` |
| Notifications | `shared.notifications.service` | `platform_services.py` |
| Webhook DLQ | `shared.webhooks.webhook_dlq_service` | `platform_services.py` |
| Payments registry | `shared.payments.registry`, `shared.payments.base` | `platform_services.py`, `ecommerce/payments` |
| Organizations / RBAC / invitations | `shared.organizations` | `platform_services.py` |
| Support tickets | `shared.support` | `platform_services.py` |
| Product feedback | `shared.product_feedback` | `platform_services.py` |
| Monetization | `shared.monetization` | `platform_services.py` |
| Email marketing | `shared.email_marketing` | `platform_services.py` |
| Email outbox | `shared.email_outbox` | engagement |

## What is intentionally LOCAL (platform-specific, not canonical infra)

These are product features of THIS platform, not cross-cutting infrastructure,
so they live in our packages by design (the same way Baremetrics owns its own
Recover feature rather than buying it):

- Workflow engine, service registry, campaigns, flows, segments (`retention_analytics_core`)
- Growth/AI/CS-ops/advanced services (`retention_analytics_growth`, `_ai`, `_cs_ops`, `_advanced`, `_ux`)
- Engagement (email/sms/push send), ecommerce, analytics metrics, reporting (`retention_analytics_engagement`, `_ecommerce`, `_analytics_core`, `_reporting_engine`)

## Available-but-not-consumed shared packages (relevant to our domain)

Of 357 top-level `shared.*` packages, these exist and could be adopted later:
`shared.helpdesk` (agent workflows on top of `shared.support`), `shared.cron`,
`shared.saved_reports`, `shared.workflow_builder`, `shared.reporting`,
`shared.gdpr`, `shared.sso`, `shared.customer_portal`, `shared.analytics`.
Note: `shared.demo` and parts of `shared.docs` have no importable source in this
checkout (only .pyc / markdown remain), so help + demo are built as platform
services here.

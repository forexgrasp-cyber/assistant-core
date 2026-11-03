# Vertical Packs

Pluggable domain packs with entities, workflows, and reports. Zero vertical
logic lives in core — each pack is self-contained and registers its own
workflows into the platform.

## Packs

| Pack | Solves | Key Workflows |
|------|--------|---------------|
| marketing | Lead nurture, campaign win-back | lead-nurture, campaign-win-back |
| ecommerce | Cart abandonment, post-purchase | cart-abandonment, post-purchase |
| saas | Onboarding, churn prevention, dunning | onboarding, churn-prevention |
| fintech | KYC onboarding, fraud alert | kyc-onboarding, fraud-alert |
| healthcare | Appointment reminder, re-engagement | appointment-reminder, patient-re-engagement |

Each pack registers its entity schemas into the EntityKernel and its workflow
definitions into the WorkflowEngine, so they're reachable from the API and
frontend just like any other service.

## Usage

```python
from retention_analytics_vertical_packs.marketing import pack as marketing
from retention_analytics_vertical_packs.saas import pack as saas

marketing.register(registry, engine, kernel)
saas.register(registry, engine, kernel)
```

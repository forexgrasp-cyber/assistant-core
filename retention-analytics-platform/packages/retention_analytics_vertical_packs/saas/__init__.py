"""SaaS vertical pack.

Solves: onboarding, trial-to-paid conversion, churn prevention, dunning.

Workflows:
- onboarding: trial started → welcome email → feature tutorial → conversion email
- churn-prevention: churn risk → dunning → win-back email
- trial-to-paid: trial ending → conversion email → discount offer
"""

from __future__ import annotations

from retention_analytics_core.entities.kernel import EntityField, EntitySchema
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep
from retention_analytics_shared_types import EventType

from retention_analytics_vertical_packs import TENANT_ID, VerticalPack

pack = VerticalPack(
    id="saas",
    name="SaaS",
    description="Subscriptions, plans, dunning, activation",
    schemas=[
        EntitySchema(
            id="subscription",
            name="Subscription",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="plan", type="string", required=True),
                EntityField(name="status", type="string"),
                EntityField(name="mrr", type="number"),
                EntityField(name="expires_at", type="datetime"),
            ],
        ),
        EntitySchema(
            id="plan",
            name="Plan",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="name", type="string", required=True),
                EntityField(name="price", type="number"),
                EntityField(name="interval", type="string"),
            ],
        ),
    ],
    workflows=[
        WorkflowDefinition(
            id="saas.onboarding",
            name="SaaS Onboarding",
            tenant_id=TENANT_ID,
            trigger_event=EventType.SUBSCRIPTION_CREATED.value,
            steps=[
                WorkflowStep(
                    id="send_welcome_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.customer_email}}", "subject": "Welcome aboard", "body": "Get started here."},
                ),
                WorkflowStep(
                    id="send_feature_tutorial",
                    service="email",
                    action="send",
                    input={"to": "{{event.customer_email}}", "subject": "Feature tutorial", "body": "Here's how to use it."},
                    depends_on=["send_welcome_email"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="saas.churn-prevention",
            name="SaaS Churn Prevention",
            tenant_id=TENANT_ID,
            trigger_event=EventType.SUBSCRIPTION_PAST_DUE.value,
            steps=[
                WorkflowStep(
                    id="dunning",
                    service="subscriptions",
                    action="dunning",
                    input={"subscription_id": "{{event.subscription_id}}", "customer_email": "{{event.customer_email}}"},
                ),
                WorkflowStep(
                    id="send_winback_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.customer_email}}", "subject": "Your subscription is past due", "body": "Reactivate today."},
                    depends_on=["dunning"],
                ),
            ],
        ),
    ],
    reports=[
        {"id": "saas.mrr", "name": "Monthly Recurring Revenue", "format": "pdf"},
        {"id": "saas.churn-rate", "name": "Churn Rate", "format": "csv"},
    ],
)

__all__ = ["pack"]

"""Seed workflow definitions for the retention platform.

These are the production retention workflows wired at start-up. Each workflow
chains real platform services (render -> send -> measure), so running one
produces durable side effects rather than a log line.

The tenant used here is the platform seed tenant; a tenant-scoped run uses
the tenant of the authenticated caller.
"""

from __future__ import annotations

from retention_analytics_core.tenancy import DEFAULT_TENANT
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep

__all__ = ["SEED_TENANT_ID", "build_workflows", "workflow_event_bindings"]

SEED_TENANT_ID = DEFAULT_TENANT


def build_workflows() -> list[WorkflowDefinition]:
    """Return the platform's retention workflow definitions."""
    return [
        WorkflowDefinition(
            id="churn-prevention",
            name="Churn Prevention",
            tenant_id=SEED_TENANT_ID,
            trigger_event="client.churn_risk",
            steps=[
                WorkflowStep(
                    id="render_winback",
                    service="templates",
                    action="render",
                    input={"template": "churn-prevention", "context": {}},
                ),
                WorkflowStep(
                    id="send_winback",
                    service="email",
                    action="send",
                    input={
                        "to": "{email}",
                        "subject": "We miss you - here is what changed",
                        "body": "We would love to keep working with you.",
                    },
                    depends_on=["render_winback"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="cart-abandonment",
            name="Cart Abandonment Recovery",
            tenant_id=SEED_TENANT_ID,
            trigger_event="order.abandoned_cart",
            steps=[
                WorkflowStep(
                    id="abandon_cart",
                    service="ecommerce.core",
                    action="abandon_cart",
                    input={"customer_email": "{email}", "cart_id": "{cart_id}"},
                ),
                WorkflowStep(
                    id="render_recovery",
                    service="templates",
                    action="render",
                    input={"template": "cart-abandonment", "context": {}},
                    depends_on=["abandon_cart"],
                ),
                WorkflowStep(
                    id="send_recovery",
                    service="email",
                    action="send",
                    input={
                        "to": "{email}",
                        "subject": "Your cart is waiting",
                        "body": "Come back and finish your order.",
                    },
                    depends_on=["render_recovery"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="welcome",
            name="Welcome Series",
            tenant_id=SEED_TENANT_ID,
            trigger_event="client.created",
            steps=[
                WorkflowStep(
                    id="render_welcome",
                    service="templates",
                    action="render",
                    input={"template": "welcome", "context": {}},
                ),
                WorkflowStep(
                    id="send_welcome",
                    service="email",
                    action="send",
                    input={
                        "to": "{email}",
                        "subject": "Welcome aboard",
                        "body": "Here is how to get the most out of the platform.",
                    },
                    depends_on=["render_welcome"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="win-back",
            name="Win Back",
            tenant_id=SEED_TENANT_ID,
            trigger_event="subscription.cancelled",
            steps=[
                WorkflowStep(
                    id="render_winback_offer",
                    service="templates",
                    action="render",
                    input={"template": "win-back", "context": {}},
                ),
                WorkflowStep(
                    id="send_winback_offer",
                    service="email",
                    action="send",
                    input={
                        "to": "{email}",
                        "subject": "We would like to win you back",
                        "body": "Here is an offer to come back.",
                    },
                    depends_on=["render_winback_offer"],
                ),
                WorkflowStep(
                    id="compute_retention",
                    service="analytics.metric",
                    action="compute_retention",
                    input={},
                    depends_on=["send_winback_offer"],
                ),
            ],
        ),
    ]


def workflow_event_bindings() -> dict[str, list[str]]:
    """Map platform events to the workflows they trigger."""
    return {
        "client.churn_risk": ["churn-prevention"],
        "order.abandoned_cart": ["cart-abandonment"],
        "client.created": ["welcome"],
        "subscription.cancelled": ["win-back"],
    }

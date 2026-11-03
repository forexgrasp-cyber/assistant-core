"""Marketing vertical pack.

Solves: lead nurture, campaign win-back, audience re-engagement.

Workflows:
- lead-nurture: lead created → send nurture email → wait → send follow-up → score lead
- campaign-win-back: inactive customer → send win-back email → send win-back SMS
"""

from __future__ import annotations

from retention_analytics_core.entities.kernel import EntityField, EntitySchema
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep
from retention_analytics_shared_types import EventType

from retention_analytics_vertical_packs import TENANT_ID, VerticalPack

pack = VerticalPack(
    id="marketing",
    name="Marketing",
    description="Campaigns, audiences, lead scoring, nurture and win-back",
    schemas=[
        EntitySchema(
            id="campaign",
            name="Campaign",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="name", type="string", required=True),
                EntityField(name="channel", type="string"),
                EntityField(name="status", type="string"),
                EntityField(name="audience_size", type="number"),
            ],
        ),
        EntitySchema(
            id="lead",
            name="Lead",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="email", type="string", required=True),
                EntityField(name="score", type="number"),
                EntityField(name="status", type="string"),
                EntityField(name="source", type="string"),
            ],
        ),
    ],
    workflows=[
        WorkflowDefinition(
            id="marketing.lead-nurture",
            name="Lead Nurture",
            tenant_id=TENANT_ID,
            trigger_event=EventType.CLIENT_CREATED.value,
            steps=[
                WorkflowStep(
                    id="send_welcome_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.client_email}}", "subject": "Welcome", "body": "Thanks for joining."},
                ),
                WorkflowStep(
                    id="score_lead",
                    service="analytics.metric",
                    action="compute_roster",
                    input={"tenant_id": TENANT_ID},
                    depends_on=["send_welcome_email"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="marketing.campaign-win-back",
            name="Campaign Win-Back",
            tenant_id=TENANT_ID,
            trigger_event=EventType.CLIENT_CHURN_RISK.value,
            steps=[
                WorkflowStep(
                    id="send_winback_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.client_email}}", "subject": "We miss you", "body": "Come back for 20% off."},
                ),
                WorkflowStep(
                    id="send_winback_sms",
                    service="sms",
                    action="send",
                    input={"to": "{{event.client_phone}}", "body": "We miss you! 20% off your next purchase."},
                    depends_on=["send_winback_email"],
                ),
            ],
        ),
    ],
    reports=[
        {"id": "marketing.campaign-performance", "name": "Campaign Performance", "format": "pdf"},
        {"id": "marketing.lead-conversion", "name": "Lead Conversion Report", "format": "csv"},
    ],
)

__all__ = ["pack"]

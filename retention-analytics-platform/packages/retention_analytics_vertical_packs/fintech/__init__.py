"""Fintech vertical pack.

Solves: KYC onboarding, fraud alert, bill-pay reminder.

Workflows:
- kyc-onboarding: account created → KYC request → document upload → verification
- fraud-alert: suspicious transaction → alert email → SMS
- bill-pay-reminder: bill due → reminder email → SMS reminder
"""

from __future__ import annotations

from retention_analytics_core.entities.kernel import EntityField, EntitySchema
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep
from retention_analytics_shared_types import EventType

from retention_analytics_vertical_packs import TENANT_ID, VerticalPack

pack = VerticalPack(
    id="fintech",
    name="Fintech",
    description="Wallets, transactions, KYC, fraud",
    schemas=[
        EntitySchema(
            id="account",
            name="Account",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="account_number", type="string", required=True),
                EntityField(name="balance", type="number"),
                EntityField(name="kyc_status", type="string"),
            ],
        ),
        EntitySchema(
            id="transaction",
            name="Transaction",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="amount", type="number"),
                EntityField(name="type", type="string"),
                EntityField(name="status", type="string"),
                EntityField(name="account_id", type="string"),
            ],
        ),
    ],
    workflows=[
        WorkflowDefinition(
            id="fintech.kyc-onboarding",
            name="KYC Onboarding",
            tenant_id=TENANT_ID,
            trigger_event=EventType.CLIENT_CREATED.value,
            steps=[
                WorkflowStep(
                    id="send_kyc_request",
                    service="email",
                    action="send",
                    input={"to": "{{event.client_email}}", "subject": "Verify your identity", "body": "Please upload your ID."},
                ),
            ],
        ),
        WorkflowDefinition(
            id="fintech.fraud-alert",
            name="Fraud Alert",
            tenant_id=TENANT_ID,
            steps=[
                WorkflowStep(
                    id="send_fraud_alert_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.customer_email}}", "subject": "Suspicious activity", "body": "Review this transaction."},
                ),
                WorkflowStep(
                    id="send_fraud_alert_sms",
                    service="sms",
                    action="send",
                    input={"to": "{{event.customer_phone}}", "body": "Suspicious activity detected on your account."},
                    depends_on=["send_fraud_alert_email"],
                ),
            ],
        ),
    ],
    reports=[
        {"id": "fintech.transaction-volume", "name": "Transaction Volume", "format": "pdf"},
        {"id": "fintech.fraud-rate", "name": "Fraud Rate", "format": "csv"},
    ],
)

__all__ = ["pack"]

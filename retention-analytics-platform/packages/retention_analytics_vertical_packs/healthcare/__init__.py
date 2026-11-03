"""Healthcare vertical pack.

Solves: appointment reminder, patient re-engagement, compliance follow-up.

Workflows:
- appointment-reminder: appointment booked → reminder email → SMS reminder
- patient-re-engagement: no-show → win-back email
- compliance-follow-up: lab result → follow-up email
"""

from __future__ import annotations

from retention_analytics_core.entities.kernel import EntityField, EntitySchema
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep

from retention_analytics_vertical_packs import TENANT_ID, VerticalPack

pack = VerticalPack(
    id="healthcare",
    name="Healthcare",
    description="Patients, appointments, compliance",
    schemas=[
        EntitySchema(
            id="patient",
            name="Patient",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="first_name", type="string", required=True),
                EntityField(name="last_name", type="string", required=True),
                EntityField(name="email", type="string"),
                EntityField(name="phone", type="string"),
            ],
        ),
        EntitySchema(
            id="appointment",
            name="Appointment",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="patient_id", type="string"),
                EntityField(name="provider", type="string"),
                EntityField(name="scheduled_at", type="datetime"),
                EntityField(name="status", type="string"),
            ],
        ),
    ],
    workflows=[
        WorkflowDefinition(
            id="healthcare.appointment-reminder",
            name="Appointment Reminder",
            tenant_id=TENANT_ID,
            steps=[
                WorkflowStep(
                    id="send_reminder_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.patient_email}}", "subject": "Appointment reminder", "body": "Your appointment is tomorrow."},
                ),
                WorkflowStep(
                    id="send_reminder_sms",
                    service="sms",
                    action="send",
                    input={"to": "{{event.patient_phone}}", "body": "Reminder: your appointment is tomorrow."},
                    depends_on=["send_reminder_email"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="healthcare.patient-re-engagement",
            name="Patient Re-Engagement",
            tenant_id=TENANT_ID,
            steps=[
                WorkflowStep(
                    id="send_winback_email",
                    service="email",
                    action="send",
                    input={"to": "{{event.patient_email}}", "subject": "We'd love to see you again", "body": "Schedule your next visit."},
                ),
            ],
        ),
    ],
    reports=[
        {"id": "healthcare.appointment-adherence", "name": "Appointment Adherence", "format": "pdf"},
        {"id": "healthcare.patient-retention", "name": "Patient Retention", "format": "csv"},
    ],
)

__all__ = ["pack"]

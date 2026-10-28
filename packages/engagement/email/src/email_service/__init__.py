"""
In-house Email Marketing Service.

Provides campaign management, template rendering, sending via multiple providers,
and deliverability tracking.
"""

from .service import EmailService
from .models import (
    EmailCampaign,
    EmailCampaignCreate,
    EmailCampaignUpdate,
    EmailTemplate,
    EmailTemplateCreate,
    EmailMessage,
    SendResult,
    CampaignStats,
)
from .senders.base import EmailSender, SendResult as SenderResult
from .senders.ses import SESSender
from .senders.sendgrid import SendGridSender
from .templates.renderer import TemplateRenderer

__all__ = [
    "EmailService",
    "EmailCampaign",
    "EmailCampaignCreate",
    "EmailCampaignUpdate",
    "EmailTemplate",
    "EmailTemplateCreate",
    "EmailMessage",
    "SendResult",
    "CampaignStats",
    "EmailSender",
    "SenderResult",
    "SESSender",
    "SendGridSender",
    "TemplateRenderer",
]

__version__ = "0.1.0"
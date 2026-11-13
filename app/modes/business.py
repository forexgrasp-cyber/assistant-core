"""Business Mode - Receptionist for local businesses."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.voice import VoiceManager
from app.billing import StripeBilling

router = APIRouter(prefix="/business", tags=["business"])

# Vertical configurations
VERTICAL_CONFIGS = {
    "dental": {
        "name": "Dental",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp", "widget"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
    "contractor": {
        "name": "Contractor",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
    "hvac": {
        "name": "HVAC",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
    "plumbing": {
        "name": "Plumbing",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
    "legal": {
        "name": "Legal",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
    "medical": {
        "name": "Medical",
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp"],
        "pricing_tiers": ["starter", "pro", "enterprise"],
    },
}


@router.get("/verticals")
async def list_verticals():
    """List available business verticals."""
    return {"verticals": VERTICAL_CONFIGS}


@router.get("/verticals/{vertical}")
async def get_vertical(vertical: str):
    """Get vertical configuration."""
    if vertical not in VERTICAL_CONFIGS:
        return {"error": "Unknown vertical"}, 404
    return VERTICAL_CONFIGS[vertical]


@router.get("/pricing")
async def get_pricing():
    """Get pricing tiers."""
    from app.config import get_config
    config = get_config()
    return config.get("billing", {}).get("tiers", {})


# Widget embed endpoint
@router.get("/widget/{assistant_id}")
async def get_widget(assistant_id: str):
    """Get widget embed code for website."""
    return {
        "assistant_id": assistant_id,
        "embed_code": f'<script src="https://assistant.example.com/widget.js" data-assistant="{assistant_id}"></script>',
        "config": {
            "position": "bottom-right",
            "theme": "light",
            "greeting": "Hi! How can I help?",
        },
    }


# Webhook endpoints for Twilio
from fastapi import Form, Header, Request
from fastapi.responses import Response
from shared.ai_voice.twilio import twiml_say
from shared.missed_lead.service import get_missed_lead_service
from shared.missed_lead.webhooks import RetellWebhookAdapter, VapiWebhookAdapter, BlandWebhookAdapter
from shared.missed_lead.responder import WhatsAppLeadResponder
from shared.missed_lead.trade import LOCKSMITH_PROFILE
from shared.booking.service import BookingService

_missed_lead_services: dict = {}
_booking_services: dict = {}


def _get_missed_lead_service(tenant_id: str):
    if tenant_id not in _missed_lead_services:
        booking_svc = BookingService(
            db_path="./data/receptionist.db",
            tenant_id=tenant_id,
        )
        whatsapp_responder = None
        # Would initialize from env
        missed_lead_svc = get_missed_lead_service(
            tenant_id=tenant_id,
            profile=LOCKSMITH_PROFILE,
            booking_service=booking_svc,
            responder=whatsapp_responder,
            dry_run=False,
        )
        _missed_lead_services[tenant_id] = missed_lead_svc
    return _missed_lead_services[tenant_id]


@router.post("/{tenant_id}/webhooks/retell/call")
async def retell_webhook(tenant_id: str, payload: dict, request: Request):
    svc = _get_missed_lead_service(tenant_id)
    adapter = RetellWebhookAdapter()
    return await adapter.handle(payload, svc)


@router.post("/{tenant_id}/webhooks/vapi/call")
async def vapi_webhook(tenant_id: str, payload: dict, request: Request):
    svc = _get_missed_lead_service(tenant_id)
    adapter = VapiWebhookAdapter()
    return await adapter.handle(payload, svc)


@router.post("/{tenant_id}/webhooks/bland/call")
async def bland_webhook(tenant_id: str, payload: dict, request: Request):
    svc = _get_missed_lead_service(tenant_id)
    adapter = BlandWebhookAdapter()
    return await adapter.handle(payload, svc)


@router.post("/{tenant_id}/webhooks/whatsapp/message")
async def whatsapp_webhook(tenant_id: str, payload: dict, request: Request):
    svc = _get_missed_lead_service(tenant_id)
    if not svc or not svc._responder:
        return {"error": "WhatsApp not configured"}, 503

    message = await svc._responder.parse_inbound(payload, dict(request.headers))
    caller = getattr(message, "customer_contact", "") or getattr(message, "customer_id", "")
    text = getattr(message, "content", "")

    if caller and text:
        result = await svc.handle_reply(
            caller_number=caller,
            text=text,
            provider_message_id=getattr(message, "message_id", None),
        )
        return {"ok": result.success, "lead_id": result.data.id if result.data else None}
    return {"ok": False}
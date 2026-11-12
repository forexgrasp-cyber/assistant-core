"""User pain-point catalog: maps real end-user pains to the workflows that fix them.

Each pain is what YOUR client's customer feels. Each workflow is the automated
response. Exposed via GET /api/v1/pains so users see full coverage.
"""

from __future__ import annotations

# pain_id -> {pain, category, workflow(s), event trigger, what the customer gets}
PAIN_CATALOG: dict[str, dict] = {
    # --- Billing & payments ---
    "payment_failed": {"pain": "Card declined — service about to stop, embarrassing", "category": "billing", "workflows": ["dunning-campaign"], "event": "payment.failed", "customer_gets": "Retry schedule + email/SMS to update card + payment wall"},
    "price_increase": {"pain": "Sticker shock — price went up without warning", "category": "billing", "workflows": ["price-change-notice"], "event": "billing.price_changed", "customer_gets": "Advance notice + grandfather option + FAQ"},
    "invoice_needed": {"pain": "Need a receipt for expense report", "category": "billing", "workflows": ["invoice-delivery"], "event": "billing.invoice_created", "customer_gets": "Invoice PDF emailed + portal link"},
    "quota_near_limit": {"pain": "Worried service will throttle mid-month", "category": "billing", "workflows": ["quota-warning"], "event": "usage.quota_near_limit", "customer_gets": "Warning at 80% + upgrade path, no surprise cutoff"},

    # --- Cancellation & commitment ---
    "wants_to_cancel": {"pain": "About to cancel — feels unheard, wants a better deal", "category": "retention", "workflows": ["cancel-flow"], "event": "cancel.flow_started", "customer_gets": "Exit survey + pause option + personalized save offer"},
    "downgrading": {"pain": "Losing features they rely on", "category": "retention", "workflows": ["downgrade-save"], "event": "subscription.downgraded", "customer_gets": "What they lose + discount to stay"},
    "renewal_coming": {"pain": "Surprise charge / losing access at renewal", "category": "retention", "workflows": ["renewal-reminder"], "event": "subscription.renewal_due", "customer_gets": "Reminder at 30/14/7 days + plan review + upsell"},
    "paused_subscription": {"pain": "Paused but forgot to come back", "category": "retention", "workflows": ["subscription-pause"], "event": "subscription.paused", "customer_gets": "Confirmation + resume date + reactivation nudge before resume"},

    # --- Onboarding & activation ---
    "never_logged_in": {"pain": "Signed up but never started — wasted signup", "category": "onboarding", "workflows": ["never-logged-in"], "event": "onboarding.no_login", "customer_gets": "Re-onboarding email + 1-click start + personal outreach"},
    "stuck_in_setup": {"pain": "Can't complete a setup step — blocked", "category": "onboarding", "workflows": ["stuck-onboarding"], "event": "onboarding.stuck", "customer_gets": "Step-specific help + video + live chat offer"},
    "trial_ending": {"pain": "Trial ending — will lose work/setup", "category": "onboarding", "workflows": ["trial-conversion"], "event": "trial.ending", "customer_gets": "Convert offer + in-app banner + keep-data promise"},
    "feature_unused": {"pain": "Paying for a feature they never figured out", "category": "onboarding", "workflows": ["feature-adoption"], "event": "feature.unused", "customer_gets": "Tutorial email + in-app walkthrough"},

    # --- Service lifecycle (oil change, beauty, fitness, maintenance) ---
    "service_due": {"pain": "Car/treatment/membership due — will forget until it breaks", "category": "service", "workflows": ["service-due-reminder"], "event": "service.due_soon", "customer_gets": "Email + SMS with due date + booking link"},
    "service_overdue": {"pain": "Overdue service — safety/performance risk", "category": "service", "workflows": ["service-overdue"], "event": "service.overdue", "customer_gets": "Escalation email + team alert"},

    # --- Product experience ---
    "hit_a_bug": {"pain": "App errored — frustrated, work interrupted", "category": "product", "workflows": ["error-apology"], "event": "app.error_occurred", "customer_gets": "Apology + status + ETA + workaround"},
    "locked_out": {"pain": "Can't log in — locked out of own account", "category": "product", "workflows": ["login-lockout"], "event": "auth.login_failed", "customer_gets": "Reset link + security note + 2FA prompt"},
    "suspicious_login": {"pain": "Fear their account was breached", "category": "product", "workflows": ["security-alert"], "event": "security.suspicious_login", "customer_gets": "Alert + session review + 2FA enable"},
    "usage_dropped": {"pain": "Stopped using it — feels like wasted money", "category": "product", "workflows": ["usage-drop-alert"], "event": "usage.dropped", "customer_gets": "Team alert + win-back email with what's new"},
    "opened_support_ticket": {"pain": "Something's wrong and they're waiting, unsure", "category": "product", "workflows": ["support-ack"], "event": "support.ticket_opened", "customer_gets": "Immediate ack + SLA + assigned agent name"},
    "ticket_resolved": {"pain": "Was it actually fixed? Will it break again?", "category": "product", "workflows": ["support-resolved-followup"], "event": "support.ticket_resolved", "customer_gets": "CSAT survey + reopen option + fix summary"},
    "seat_invite_inactive": {"pain": "Team member invited but never joined — wasted seat", "category": "product", "workflows": ["invite-activation"], "event": "team.invite_sent", "customer_gets": "Reminder to invitee + admin nudge to resend/replace"},

    # --- Shopping ---
    "cart_abandoned": {"pain": "Left items in cart — distracted or price-hesitant", "category": "commerce", "workflows": ["cart-abandonment"], "event": "order.abandoned_cart", "customer_gets": "Recovery email + SMS + incentive"},
    "item_back_in_stock": {"pain": "Wanted item was sold out", "category": "commerce", "workflows": ["back-in-stock"], "event": "inventory.back_in_stock", "customer_gets": "Notification + reserved slot"},
    "price_dropped": {"pain": "Paid more than current price", "category": "commerce", "workflows": ["price-drop-alert"], "event": "pricing.price_dropped", "customer_gets": "Price-drop notice + difference refund"},

    # --- Churn & loyalty ---
    "at_churn_risk": {"pain": "Quietly dissatisfied — about to leave", "category": "retention", "workflows": ["churn-prevention", "health-score-alert"], "event": "client.churn_risk / health.score_low", "customer_gets": "Win-back email + team alert + check-in"},
    "already_cancelled": {"pain": "Left — feels the product wasn't worth it", "category": "retention", "workflows": ["win-back"], "event": "subscription.cancelled", "customer_gets": "Personalized offer + what's changed"},
    "low_effort_score": {"pain": "Told us it was hard — feels unheard", "category": "retention", "workflows": ["low-effort-score"], "event": "ces.low", "customer_gets": "Team alert + 'what would help' email"},
    "happy_customer": {"pain": "None — opportunity to grow via referral", "category": "growth", "workflows": ["referral-ask", "annual-upsell", "expansion-opportunity", "cross-sell"], "event": "referral.eligible / upsell.annual_eligible / account.seat_overage / cross_sell.eligible", "customer_gets": "Referral reward, annual discount, expansion offer, cross-sell"},
}

PAIN_CATEGORIES = ["billing", "retention", "onboarding", "service", "product", "commerce", "growth"]


def pain_catalog() -> dict:
    """Return the catalog grouped by category."""
    by_cat: dict[str, list] = {c: [] for c in PAIN_CATEGORIES}
    for pid, p in PAIN_CATALOG.items():
        by_cat.setdefault(p["category"], []).append({"id": pid, **p})
    return {
        "categories": PAIN_CATEGORIES,
        "pains": PAIN_CATALOG,
        "by_category": by_cat,
        "total": len(PAIN_CATALOG),
    }


__all__ = ["PAIN_CATALOG", "PAIN_CATEGORIES", "pain_catalog"]

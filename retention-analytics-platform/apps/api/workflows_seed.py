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
    """Return all workflow definitions: core retention + competitor-parity growth workflows."""
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
    ] + _competitor_workflows()


def _competitor_workflows() -> list[WorkflowDefinition]:
    """Competitor-parity workflows (Baremetrics, Churnkey, ChurnZero, Vitally)."""
    T = SEED_TENANT_ID
    wfs: list[WorkflowDefinition] = []

    def wf(wid: str, name: str, trigger: str, steps: list[WorkflowStep]) -> WorkflowDefinition:
        return WorkflowDefinition(id=wid, name=name, tenant_id=T, trigger_event=trigger, steps=steps)

    def step(sid: str, svc: str, action: str, inp: dict | None = None, deps: list[str] | None = None) -> WorkflowStep:
        return WorkflowStep(id=sid, service=svc, action=action, input=inp or {}, depends_on=deps or [])

    # 1. Dunning / payment failure recovery (Baremetrics Recover, Churnkey Payment Recovery)
    wfs.append(wf("dunning-campaign", "Dunning & Payment Recovery", "payment.failed", [
        step("start_dunning", "dunning", "start_campaign", {"subscription_id": "{subscription_id}", "customer_email": "{email}", "amount_due": "{amount_due}"}),
        step("schedule_retry_1", "dunning", "schedule_retry", {"campaign_id": "{campaign_id}", "attempt": 1}, ["start_dunning"]),
        step("notify_email_1", "email", "send", {"to": "{email}", "subject": "Payment failed - update your card", "body": "Your payment failed. Update your card to avoid interruption."}, ["start_dunning"]),
        step("notify_sms", "sms", "send", {"to": "{phone}", "body": "Payment failed. Update your card: {update_url}"}, ["schedule_retry_1"]),
    ]))

    # 2. Cancel flow with exit survey (Baremetrics Cancellation Insights, Churnkey Cancel Flows)
    wfs.append(wf("cancel-flow", "Cancel Flow + Exit Survey", "cancel.flow_started", [
        step("send_exit_survey", "surveys", "send_csat", {"client_id": "{client_id}", "customer_email": "{email}", "question": "Why are you cancelling?"}),
        step("offer_pause", "subscriptions", "pause", {"subscription_id": "{subscription_id}"}),
        step("render_save_offer", "templates", "render", {"template": "cancel-save", "context": {"reason": "{reason}"}}, ["send_exit_survey"]),
        step("send_save_offer", "email", "send", {"to": "{email}", "subject": "Before you go - a better offer", "body": "Based on your feedback, here is a personalized offer."}, ["render_save_offer"]),
    ]))

    # 3. Subscription pause (Churnkey Subscription Pauses)
    wfs.append(wf("subscription-pause", "Subscription Pause", "subscription.paused", [
        step("pause_sub", "subscriptions", "pause", {"subscription_id": "{subscription_id}", "resume_at": "{resume_at}"}),
        step("send_confirm", "email", "send", {"to": "{email}", "subject": "Subscription paused", "body": "Your subscription is paused until {resume_at}."}, ["pause_sub"]),
    ]))

    # 4. Annual upsell (Churnkey Annual Upsells)
    wfs.append(wf("annual-upsell", "Annual Plan Upsell", "upsell.annual_eligible", [
        step("render_upsell", "templates", "render", {"template": "annual-upsell", "context": {}}),
        step("send_upsell", "email", "send", {"to": "{email}", "subject": "Switch to annual and save 20%", "body": "Go annual and save 2 months."}, ["render_upsell"]),
    ]))

    # 5. Expansion / seat overage (ChurnZero Beacon expansion detection)
    wfs.append(wf("expansion-opportunity", "Expansion Opportunity", "account.seat_overage", [
        step("compute_health", "health.scoring", "compute", {"client_id": "{client_id}", "usage_score": 90}),
        step("send_expansion", "email", "send", {"to": "{email}", "subject": "You are growing - add seats", "body": "You are at {seat_usage}% of licensed seats. Add seats to keep everyone productive."}, ["compute_health"]),
    ]))

    # 6. Reactivation campaign (Churnkey Customer Return Campaigns)
    wfs.append(wf("reactivation", "Customer Reactivation", "client.reactivated", [
        step("send_welcome_back", "email", "send", {"to": "{email}", "subject": "Welcome back!", "body": "Here is what is new since you left."}),
        step("offer_return_deal", "templates", "render", {"template": "return-deal", "context": {}}),
    ]))

    # 7. NPS survey pipeline (ChurnZero Surveys, Vitally NPS)
    wfs.append(wf("nps-survey", "NPS Survey", "survey.nps_due", [
        step("send_nps", "surveys", "send_nps", {"client_id": "{client_id}", "customer_email": "{email}"}),
        step("compute_nps", "surveys", "compute_nps", {"tenant_id": "{tenant_id}"}, ["send_nps"]),
    ]))

    # 8. Health score alert (ChurnZero ChurnScores, Vitally Health Scores)
    wfs.append(wf("health-score-alert", "Health Score Alert", "health.score_low", [
        step("compute_health", "health.scoring", "compute", {"client_id": "{client_id}", "usage_score": "{usage_score}", "support_score": "{support_score}", "payment_score": "{payment_score}"}),
        step("alert_csm", "notifications", "send", {"title": "Health score low", "body": "Client {client_id} health dropped to {score}", "type": "alert"}, ["compute_health"]),
        step("send_checkin", "email", "send", {"to": "{email}", "subject": "How can we help?", "body": "We noticed things might not be going great. Let us know how we can help."}, ["compute_health"]),
    ]))

    # 9. Feature adoption (ChurnZero product adoption)
    wfs.append(wf("feature-adoption", "Feature Adoption Nudge", "feature.unused", [
        step("send_tutorial", "email", "send", {"to": "{email}", "subject": "Get more from {feature_name}", "body": "Here is a 3-minute guide to {feature_name}."}),
        step("inapp_walkthrough", "inapp.messaging", "start_walkthrough", {"client_id": "{client_id}", "steps": ["Highlight {feature_name}", "Show example", "CTA to use it"]}, ["send_tutorial"]),
    ]))

    # 10. Renewal reminder (ChurnZero Renewal Hub)
    wfs.append(wf("renewal-reminder", "Renewal Reminder", "subscription.renewal_due", [
        step("send_reminder", "email", "send", {"to": "{email}", "subject": "Your renewal is in {days_left} days", "body": "Renews on {renewal_date}. Review your plan."}),
        step("upsell_at_renewal", "templates", "render", {"template": "renewal-upsell", "context": {}}, ["send_reminder"]),
    ]))

    # 11. Trial conversion (Baremetrics Trial Insights)
    wfs.append(wf("trial-conversion", "Trial Conversion", "trial.ending", [
        step("send_convert_offer", "email", "send", {"to": "{email}", "subject": "Your trial ends in {days_left} days", "body": "Convert now and keep your data. Special offer inside."}),
        step("inapp_banner", "inapp.messaging", "send_banner", {"client_id": "{client_id}", "title": "Trial ending soon", "body": "Convert to keep your setup.", "cta": {"label": "Convert", "url": "{convert_url}"}}, ["send_convert_offer"]),
    ]))

    # 12. Downgrade save (Churnkey cancel flows - downgrade path)
    wfs.append(wf("downgrade-save", "Downgrade Save", "subscription.downgraded", [
        step("send_save", "email", "send", {"to": "{email}", "subject": "We hate to see you downgrade", "body": "Here is what you lose on the lower plan and how to get it back cheaper."}),
        step("offer_discount", "templates", "render", {"template": "downgrade-discount", "context": {"old_plan": "{old_plan}", "new_plan": "{new_plan}"}}),
    ]))

    # 13. Referral ask (Vitally collaboration)
    wfs.append(wf("referral-ask", "Referral Program", "referral.eligible", [
        step("send_referral", "email", "send", {"to": "{email}", "subject": "Know someone who needs us? Earn $50", "body": "Refer a friend and you both get $50 credit."}),
    ]))

    # 14. Onboarding milestone check-in (ChurnZero Launchpad, Vitally Projects)
    wfs.append(wf("onboarding-milestone", "Onboarding Milestone", "onboarding.milestone", [
        step("send_checkin", "email", "send", {"to": "{email}", "subject": "Day {day} check-in", "body": "How is setup going? Reply and we will help."}),
        step("health_check", "health.scoring", "compute", {"client_id": "{client_id}", "engagement_score": "{engagement_score}"}, ["send_checkin"]),
    ]))

    # 15. Usage drop alert (ChurnZero real-time alerts)
    wfs.append(wf("usage-drop-alert", "Usage Drop Alert", "usage.dropped", [
        step("compute_health", "health.scoring", "compute", {"client_id": "{client_id}", "usage_score": 20}),
        step("alert_team", "notifications", "send", {"title": "Usage dropped", "body": "Client {client_id} usage down {drop_pct}% in {window}", "type": "alert"}, ["compute_health"]),
        step("send_winback", "email", "send", {"to": "{email}", "subject": "We noticed you have been quiet", "body": "Come back - here is what is new."}, ["compute_health"]),
    ]))

    # 16. Service due soon - reminder (universal: oil change, beauty treatment, fitness class, maintenance)
    wfs.append(wf("service-due-reminder", "Service Due Reminder", "service.due_soon", [
        step("send_reminder", "email", "send", {
            "to": "{email}",
            "subject": "Your {service_name} is due on {next_due_date}",
            "body": "Hi {name}, your {service_name} is coming up on {next_due_date}. Book now to keep everything running smoothly.",
        }),
        step("send_sms_reminder", "sms", "send", {
            "to": "{phone}",
            "body": "Reminder: your {service_name} is due {days_until_due} days from now. Book: {booking_url}",
        }, ["send_reminder"]),
    ]))

    # 17. Service overdue - escalation
    wfs.append(wf("service-overdue", "Service Overdue Escalation", "service.overdue", [
        step("send_overdue", "email", "send", {
            "to": "{email}",
            "subject": "Your {service_name} is overdue",
            "body": "Your {service_name} was due on {next_due_date}. Please book to avoid interruption.",
        }),
        step("escalate_team", "notifications", "send", {
            "title": "Service overdue",
            "body": "{name} has {service_name} overdue since {next_due_date}",
            "type": "alert",
        }, ["send_overdue"]),
    ]))

    # 18. Cross-sell (Churnkey dynamic offers)
    wfs.append(wf("cross-sell", "Cross-Sell Offer", "cross_sell.eligible", [
        step("get_cross_sell", "catalog", "recommend_cross_sell", {"customer": "{customer}"}),
        step("send_cross_sell", "email", "send", {
            "to": "{email}",
            "subject": "You might also like {product_name}",
            "body": "Based on what you use, {product_name} is a great fit. Here is {discount_pct}% off.",
        }, ["get_cross_sell"]),
    ]))

    # 19. Drip sequence trigger (multi-touch win-back)
    wfs.append(wf("drip-sequence", "Drip Sequence", "sequence.enrolled", [
        step("send_step_1", "email", "send", {"to": "{email}", "subject": "{step_subject}", "body": "{step_body}"}),
        step("schedule_next", "automation.sequences", "advance", {"enrollment_id": "{enrollment_id}"}, ["send_step_1"]),
    ]))

    # 20. Customer effort score trigger (ChurnZero CES)
    wfs.append(wf("low-effort-score", "Low Customer Effort Score", "ces.low", [
        step("compute_health", "health.scoring", "compute", {"client_id": "{client_id}", "support_score": 30}),
        step("alert_team", "notifications", "send", {"title": "Low CES", "body": "Client {client_id} reported high effort", "type": "alert"}, ["compute_health"]),
        step("send_checkin", "email", "send", {"to": "{email}", "subject": "How can we make this easier?", "body": "You told us this was hard. What would help?"}, ["compute_health"]),
    ]))

    # ---- Pain-point workflows (fix real user pains) ----

    # 21. Login lockout — locked out of own account
    wfs.append(wf("login-lockout", "Login Lockout Recovery", "auth.login_failed", [
        step("send_reset", "email", "send", {"to": "{email}", "subject": "Reset your password", "body": "You had several failed logins. Reset here: {reset_url}. If this wasn't you, secure your account: {security_url}"}),
        step("alert_security", "notifications", "send", {"title": "Repeated login failures", "body": "{email} had {attempts} failed logins from {ip}", "type": "security"}, ["send_reset"]),
    ]))

    # 22. Bug/error apology
    wfs.append(wf("error-apology", "Error Apology + Fix ETA", "app.error_occurred", [
        step("send_apology", "email", "send", {"to": "{email}", "subject": "Sorry — we hit an error", "body": "We saw the error you hit ({error}). Status: {status_url}. ETA: {eta}. Workaround: {workaround}"}),
        step("alert_team", "notifications", "send", {"title": "App error", "body": "{email} hit {error} on {page}", "type": "bug"}, ["send_apology"]),
    ]))

    # 23. Support ticket acknowledgment
    wfs.append(wf("support-ack", "Support Ticket Acknowledgment", "support.ticket_opened", [
        step("send_ack", "email", "send", {"to": "{email}", "subject": "We got your request #{ticket_id}", "body": "Assigned to {agent}. SLA: {sla}. Track: {ticket_url}"}),
        step("log_touchpoint", "customers.360", "log_touchpoint", {"customer_id": "{client_id}", "type": "support", "summary": "Ticket #{ticket_id} opened"}, ["send_ack"]),
    ]))

    # 24. Support resolved follow-up
    wfs.append(wf("support-resolved-followup", "Support Resolved Follow-up", "support.ticket_resolved", [
        step("send_csat", "surveys", "send_csat", {"client_id": "{client_id}", "customer_email": "{email}", "question": "Did ticket #{ticket_id} fix your issue? (1-5)"}),
        step("send_summary", "email", "send", {"to": "{email}", "subject": "Ticket #{ticket_id} resolved", "body": "Fix: {resolution}. Reopen anytime: {ticket_url}"}, ["send_csat"]),
    ]))

    # 25. Price change advance notice
    wfs.append(wf("price-change-notice", "Price Change Notice", "billing.price_changed", [
        step("send_notice", "email", "send", {"to": "{email}", "subject": "Change to your plan on {effective_date}", "body": "Your plan changes from ${old_price} to ${new_price} on {effective_date}. Grandfathered: {grandfathered}. FAQ: {faq_url}"}),
        step("offer_grandfather", "catalog", "add_offer", {"name": "Grandfather", "type": "discount", "discount_pct": 0, "conditions": {"price_change": True}}, ["send_notice"]),
    ]))

    # 26. Invoice delivery
    wfs.append(wf("invoice-delivery", "Invoice Delivery", "billing.invoice_created", [
        step("send_invoice", "email", "send", {"to": "{email}", "subject": "Invoice #{invoice_id} — ${amount}", "body": "PDF attached / portal: {invoice_url}. Paid via {payment_method}."}),
    ]))

    # 27. Quota warning (80% usage)
    wfs.append(wf("quota-warning", "Quota Warning", "usage.quota_near_limit", [
        step("send_warning", "email", "send", {"to": "{email}", "subject": "You're at {usage_pct}% of your {resource} quota", "body": "Upgrade to avoid throttling: {upgrade_url}"}),
        step("inapp_banner", "inapp.messaging", "send_banner", {"client_id": "{client_id}", "title": "Quota almost reached", "body": "{usage_pct}% of {resource} used"}, ["send_warning"]),
    ]))

    # 28. Never logged in after signup
    wfs.append(wf("never-logged-in", "Never Logged In Re-onboarding", "onboarding.no_login", [
        step("send_reonboard", "email", "send", {"to": "{email}", "subject": "Your account is ready — 1 click to start", "body": "Start here: {login_url}. Need help? Reply to this email."}),
        step("alert_csm", "notifications", "send", {"title": "Never logged in", "body": "{email} signed up {days_ago}d ago, never logged in", "type": "alert"}, ["send_reonboard"]),
    ]))

    # 29. Stuck in onboarding step
    wfs.append(wf("stuck-onboarding", "Stuck in Setup Help", "onboarding.stuck", [
        step("send_step_help", "email", "send", {"to": "{email}", "subject": "Stuck on '{step}'? Here's the fix", "body": "Video: {video_url}. Live chat: {chat_url}"}),
        step("inapp_walkthrough", "inapp.messaging", "start_walkthrough", {"client_id": "{client_id}", "steps": ["Re-show {step}", "Skip for now"]}, ["send_step_help"]),
    ]))

    # 30. Back in stock
    wfs.append(wf("back-in-stock", "Back In Stock Alert", "inventory.back_in_stock", [
        step("send_restock", "email", "send", {"to": "{email}", "subject": "{product_name} is back in stock", "body": "Reserve yours before it sells out again: {product_url}"}),
        step("send_sms", "sms", "send", {"to": "{phone}", "body": "{product_name} is back! {product_url}"}, ["send_restock"]),
    ]))

    # 31. Price drop on purchased item
    wfs.append(wf("price-drop-alert", "Price Drop Refund", "pricing.price_dropped", [
        step("send_refund_notice", "email", "send", {"to": "{email}", "subject": "{product_name} dropped to ${new_price} — we refunded ${difference}", "body": "Refund issued to your original payment method."}),
    ]))

    # 32. Suspicious login security alert
    wfs.append(wf("security-alert", "Suspicious Login Alert", "security.suspicious_login", [
        step("send_alert", "email", "send", {"to": "{email}", "subject": "New login from {location} ({device})", "body": "Was this you? If not, secure now: {security_url}. Review sessions: {sessions_url}"}),
        step("send_sms_alert", "sms", "send", {"to": "{phone}", "body": "New login to your account from {location}. Not you? {security_url}"}, ["send_alert"]),
    ]))

    # 33. Invited team member never activated
    wfs.append(wf("invite-activation", "Invite Activation Nudge", "team.invite_sent", [
        step("remind_invitee", "email", "send", {"to": "{invitee_email}", "subject": "{inviter} invited you to {workspace}", "body": "Join here: {invite_url}"}),
        step("nudge_admin", "notifications", "send", {"title": "Invite not accepted", "body": "{invitee_email} hasn't accepted the invite to {workspace} (sent {days_ago}d ago)", "type": "alert"}, ["remind_invitee"]),
    ]))

    return wfs


def workflow_event_bindings() -> dict[str, list[str]]:
    """Map platform events to the workflows they trigger."""
    bindings = {
        "client.churn_risk": ["churn-prevention"],
        "order.abandoned_cart": ["cart-abandonment"],
        "client.created": ["welcome"],
        "subscription.cancelled": ["win-back"],
        # Competitor-parity bindings
        "payment.failed": ["dunning-campaign"],
        "cancel.flow_started": ["cancel-flow"],
        "subscription.paused": ["subscription-pause"],
        "upsell.annual_eligible": ["annual-upsell"],
        "account.seat_overage": ["expansion-opportunity"],
        "client.reactivated": ["reactivation"],
        "survey.nps_due": ["nps-survey"],
        "health.score_low": ["health-score-alert"],
        "feature.unused": ["feature-adoption"],
        "subscription.renewal_due": ["renewal-reminder"],
        "trial.ending": ["trial-conversion"],
        "subscription.downgraded": ["downgrade-save"],
        "referral.eligible": ["referral-ask"],
        "onboarding.milestone": ["onboarding-milestone"],
        "usage.dropped": ["usage-drop-alert"],
        # Universal service-lifecycle bindings
        "service.due_soon": ["service-due-reminder"],
        "service.overdue": ["service-overdue"],
        "cross_sell.eligible": ["cross-sell"],
        "sequence.enrolled": ["drip-sequence"],
        "ces.low": ["low-effort-score"],
        # Pain-point bindings
        "auth.login_failed": ["login-lockout"],
        "app.error_occurred": ["error-apology"],
        "support.ticket_opened": ["support-ack"],
        "support.ticket_resolved": ["support-resolved-followup"],
        "billing.price_changed": ["price-change-notice"],
        "billing.invoice_created": ["invoice-delivery"],
        "usage.quota_near_limit": ["quota-warning"],
        "onboarding.no_login": ["never-logged-in"],
        "onboarding.stuck": ["stuck-onboarding"],
        "inventory.back_in_stock": ["back-in-stock"],
        "pricing.price_dropped": ["price-drop-alert"],
        "security.suspicious_login": ["security-alert"],
        "team.invite_sent": ["invite-activation"],
    }
    return bindings

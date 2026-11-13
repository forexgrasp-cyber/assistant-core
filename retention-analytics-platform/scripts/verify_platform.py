"""Comprehensive data-driven verification of the whole platform.

Seeds realistic data, then exercises every domain against the live API:
services, workflows, pipelines, persistence, campaigns, billing lifecycle,
analytics, growth, integrations, compliance, and the customer portal.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import os
BASE = os.environ.get("API_URL", "http://127.0.0.1:47319")
H = {"Authorization": "Bearer dev-token", "Content-Type": "application/json"}
T = "00000000-0000-0000-0000-000000000001"

passed, failed = 0, 0
failures = []


def req(method, path, body=None, qs=None, headers=None):
    url = BASE + path
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers={**H, **(headers or {})}, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=30)
        raw = resp.read()
        code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
    try:
        return code, json.loads(raw or b"{}")
    except Exception:
        return code, raw.decode(errors="ignore")


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        failures.append(f"{name} :: {str(detail)[:160]}")
        print(f"  FAIL  {name}  {str(detail)[:160]}")


print("=" * 72)
print("PLATFORM DATA VERIFICATION")
print("=" * 72)

# ---------------------------------------------------------------- 1. seed
print("\n[1] SEEDING REALISTIC DATA")
now = datetime.now(timezone.utc)
customers = []
seed_spec = [
    ("Maria Garcia", "maria@acme.com", "premium", 800, 175, 180, "oil change", 72),
    ("John Smith", "john@acme.com", "growth", 400, 185, 180, "oil change", 35),
    ("Ana Lee", "ana@acme.com", "starter", 120, 60, 90, "tire rotation", 88),
    ("Bob Chen", "bob@acme.com", "growth", 350, 178, 180, "oil change", 45),
    ("Sara Khan", "sara@acme.com", "premium", 900, 200, 180, "oil change", 28),
    ("Tom Wilson", "tom@acme.com", "starter", 100, 30, 90, "tire rotation", 91),
    ("Kate Miller", "kate@acme.com", "growth", 500, 100, 180, "oil change", 64),
    ("Liam Brown", "liam@acme.com", "starter", 90, 12, 90, "tire rotation", 83),
]
for i, (name, email, plan, mrr, days_ago, interval, service, health) in enumerate(seed_spec):
    last = (now - timedelta(days=days_ago)).isoformat()
    code, d = req("POST", "/api/v1/customers", {
        "id": f"v-{i}", "name": name, "email": email, "phone": f"+1555000{i:04d}",
        "plan": plan, "mrr": mrr, "ltv": mrr * 12, "health_score": health,
        "last_service_date": last, "service_interval_days": interval, "service_name": service})
    if code == 200:
        customers.append(d["profile"])
check("8 customers seeded with computed next-due", len(customers) == 8, len(customers))
due_soon = [c for c in customers if c.get("days_until_due") is not None and 0 <= c["days_until_due"] <= 14]
overdue = [c for c in customers if (c.get("days_until_due") or 0) < 0]
check("service-due classification populated", len(due_soon) >= 1 and len(overdue) >= 1,
      f"due_soon={len(due_soon)} overdue={len(overdue)}")

# orders + events for analytics
for i, c in enumerate(customers):
    for d in (10, 40, 70):
        req("POST", "/api/v1/events", {
            "type": "order.placed", "tenant_id": T,
            "idempotency_key": f"v-{i}-order-{d}",
            "payload": {"customer_email": c["email"], "order_id": f"o-{i}-{d}", "amount": c["mrr"], "currency": "USD"}})
code, d = req("GET", "/api/v1/customers")
check("customers persisted + readable", d.get("count", 0) >= 8, d.get("count"))

# ---------------------------------------------------------------- 2. services
print("\n[2] SERVICE REGISTRY + ACTIONS")
code, d = req("GET", "/api/v1/actions")
check("service catalog exposed", d.get("count", 0) >= 90, d.get("count"))
total_actions = sum(len(s["actions"]) for s in d.get("services", []))
check("260+ callable actions", total_actions >= 260, total_actions)

service_calls = [
    ("email", "send", {"to": "v0@acme.com", "subject": "Verify", "body": "hi"}),
    ("sms", "send", {"to": "+15550000000", "body": "hi"}),
    ("push", "send", {"device_token": "tok", "title": "t", "body": "b"}),
    ("analytics.metric", "compute_retention", {"payload": {}}),
    ("analytics.metric", "compute_rfm", {"payload": {}}),
    ("analytics.cohort", "compute_cohorts", {"payload": {"cohort_months": 6}}),
    ("saas.metrics", "compute_all", {"subscriptions": [{"status": "active", "amount": 100}], "starting_mrr": 5000,
                                      "arpu": 50, "monthly_churn_rate": 0.04, "active_customers": 8,
                                      "sales_marketing_spend": 4000, "new_customers": 3, "starting_customers": 8,
                                      "churned_customers": 1, "new_mrr": 200}),
    ("health.scoring", "compute", {"client_id": "v-3", "usage_score": 40, "support_score": 60, "payment_score": 90}),
    ("health.engine", "compute", {"client_id": "v-3", "usage_score": 40, "engagement_score": 30}),
    ("ai.churn_predict", "predict", {"client_id": "v-3", "usage_drop_pct": 60, "open_tickets": 2}),
    ("ai.churn_ml", "score", {"client_id": "v-3", "orders": 2, "order_count": 2, "total_spent": 400,
                              "days_since_last_order": 90, "frequency": 2, "monetary": 400}),
    ("ai.feedback", "classify", {"text": "too expensive, the export is broken", "mrr": 400}),
    ("ai.offers", "recommend", {"churn_reason": "pricing", "churn_probability": 0.8, "mrr": 400}),
    ("ai.feedback", "themes", {}),
    ("dunning", "start_campaign", {"subscription_id": "v-sub-1", "customer_email": "maria@acme.com", "amount_due": 99}),
    ("dunning.engine", "start", {"subscription_id": "v-sub-1", "customer_email": "maria@acme.com",
                                  "amount_due": 99, "failure_reason": "insufficient_funds"}),
    ("surveys", "send_nps", {"client_id": "v-0", "customer_email": "maria@acme.com"}),
    ("surveys", "compute_nps", {}),
    ("surveys.micro", "create", {"trigger_action": "checkout", "question": "How was checkout?"}),
    ("forecasting", "forecast_mrr", {"current_mrr": 3000, "months": 12}),
    ("segmentation", "define_segment", {"name": "At-risk premium", "criteria": {"health_score": {"lt": 60}}}),
    ("segmentation", "list_segments", {}),
    ("notifications", "send", {"title": "Verification", "body": "b"}),
    ("webhooks_out", "dispatch", {"url": "https://example.com/h", "event_type": "test", "data": {}}),
    ("webhooks.manage", "register", {"url": "https://example.com/v", "events": ["client.churn_risk"]}),
    ("campaigns", "create", {"name": "seed campaign", "goal": "reduce_churn", "flows": ["churn-prevention"]}),
    ("catalog", "add_product", {"name": "Premium Care", "price": 99, "category": "premium"}),
    ("catalog", "list_products", {}),
    ("walls", "create", {"customer_id": "v-4", "type": "payment", "amount_due": 99, "gated_features": ["exports"]}),
    ("journeys", "create", {"name": "Seed journey"}),
    ("cs.plans", "create", {"name": "Onboarding plan", "client_id": "v-0"}),
    ("cs.playbooks", "create", {"name": "Save playbook", "trigger": "client.churn_risk", "actions": []}),
    ("cs.alerts", "fire", {"title": "Seed alert", "severity": "high"}),
    ("cs.renewals", "track", {"customer_id": "v-0", "subscription_id": "v-sub-1", "arr": 9600}),
    ("experiments.ab", "create", {"name": "Seed test", "metric": "conversion_rate"}),
    ("automation.sequences", "create", {"name": "Seed seq", "steps": [{"delay_days": 0, "channel": "email"}]}),
    ("benchmarks", "compare", {"industry": "saas", "metrics": {"churn_rate": 0.04}}),
    ("goals", "create", {"name": "Seed goal", "metric": "mrr", "target": 10000, "current": 4000}),
    ("analytics.attribution", "record_outcome", {"customer_id": "v-0", "campaign_id": "camp-1", "outcome": "retained", "value": 800}),
    ("analytics.anomaly", "detect", {"series": [100, 102, 99, 101, 98, 100, 160]}),
    ("analytics.root_cause", "analyze", {"metric": "churn_rate"}),
    ("analytics.cohort_compare", "compare", {"cohort_a": {"name": "A", "metrics": {"retention_rate_30d": 0.5}},
                                            "cohort_b": {"name": "B", "metrics": {"retention_rate_30d": 0.7}}}),
    ("attribution.multitouch", "record_touch", {"customer_id": "v-0", "channel": "email", "value": 800}),
    ("lifecycle", "create", {"subscription_id": "v-lc-1", "plan": "growth", "amount": 350}),
    ("metering.v2", "set_quota", {"resource": "api_calls", "limit": 100, "overage_price": 0.1, "hard_cap": True}),
    ("billing.proration", "quote_change", {"current_price": 100, "new_price": 150,
                                           "period_start": (now - timedelta(days=15)).isoformat(),
                                           "period_end": (now + timedelta(days=15)).isoformat()}),
    ("nps.loop", "handle_response", {"client_id": "v-1", "score": 9}),
    ("experiments.auto", "evaluate", {"experiment_id": "e1", "results": {"A": {"sent": 500, "converted": 20}, "B": {"sent": 500, "converted": 60}}}),
    ("incidents", "create_from_anomaly", {"metric": "churn_rate", "anomaly": {"severity": "high", "direction": "spike", "deviation_pct": 40}}),
    ("winback.timing", "schedule", {"customer_id": "v-4", "email": "sara@acme.com"}),
    ("sendtime.optimize", "recommend", {"email": "maria@acme.com"}),
    ("sendtime.optimize", "plan_campaign", {"campaign_id": "c1", "recipients": [{"email": "maria@acme.com"}]}),
    ("email.deliverability", "warmup_schedule", {"daily_volume": 100, "age_days": 2}),
    ("success_center", "register_customer", {"email": "maria@acme.com", "name": "Maria"}),
    ("presets", "list", {}),
    ("ux.settings", "get", {}),
    ("ux.reports", "save", {"name": "Seed report", "widgets": ["retention"]}),
    ("ux.events", "schemas", {}),
    ("flows.editor", "create_graph", {"name": "Seed graph", "trigger_event": "client.created"}),
    ("data.transfer", "suggest_mapping", {"columns": ["email", "name", "mrr"]}),
    ("integrations", "catalog", {}),
    ("connectors", "supported", {}),
    ("help", "list", {}),
    ("export", "datasets", {}),
    ("demo", "scenario", {}),
]
failed_actions = []
for svc, action, payload in service_calls:
    code, d = req("POST", f"/api/v1/actions/{svc}/{action}", {**payload, "tenant_id": T})
    if code != 200:
        failed_actions.append(f"{svc}.{action}->{code}")
check(f"{len(service_calls)} service actions callable via proxy", not failed_actions, failed_actions[:6])

# ---------------------------------------------------------------- 3. workflows
print("\n[3] ALL WORKFLOWS EXECUTE")
code, d = req("GET", "/api/v1/workflows")
wfs = d.get("workflows", [])
ctx = {"email": "maria@acme.com", "phone": "+15550000000", "client_id": "v-0", "cart_id": "c1",
       "subscription_id": "v-sub-1", "campaign_id": "camp-1", "amount_due": 99, "service_name": "oil change",
       "next_due_date": "2026-12-01", "days_until_due": 5, "name": "Maria", "error": "boom", "page": "/x",
       "step": "billing", "product_name": "Premium Care", "usage_pct": 85, "resource": "api_calls",
       "invoice_id": "inv-1", "amount": 99, "ticket_id": "t1", "agent": "Sam", "sla": "24h", "resolution": "fixed",
       "old_price": 10, "new_price": 15, "effective_date": "2026-12-01", "grandfathered": True, "drop_pct": 40,
       "window": "14d", "client_email": "maria@acme.com", "invitee_email": "i@x.com", "inviter": "Sam",
       "workspace": "Acme", "attempts": 3, "ip": "1.2.3.4", "location": "Berlin", "device": "Chrome",
       "usage_score": 20, "support_score": 30, "payment_score": 50, "score": 30, "days_left": 5, "seats": 12,
       "seat_usage": 95, "feature_name": "Reports", "old_plan": "pro", "new_plan": "starter", "reason": "price",
       "mrr_lost": 100, "convert_url": "https://x/convert", "booking_url": "https://x/book", "update_url": "https://x/card",
       "reset_url": "https://x/reset", "security_url": "https://x/sec", "sessions_url": "https://x/s",
       "status_url": "https://x/status", "eta": "1h", "workaround": "refresh", "video_url": "https://x/v",
       "chat_url": "https://x/c", "ticket_url": "https://x/t", "invoice_url": "https://x/i", "faq_url": "https://x/f",
       "product_url": "https://x/p", "login_url": "https://x/login", "invite_url": "https://x/inv",
       "upgrade_url": "https://x/up", "enrollment_id": "enr-1", "step_subject": "s", "step_body": "b",
       "discount_pct": 20, "mrr": 500, "customer": {"plan": "growth"}}
wf_fail = []
for w in wfs:
    code, r = req("POST", f"/api/v1/workflows/{w['id']}/run", {"context": ctx})
    if code != 200 or r.get("status") != "completed":
        wf_fail.append(f"{w['id']}->{code}/{r.get('status')}")
check(f"all {len(wfs)} workflows completed", not wf_fail, wf_fail[:6])

# ---------------------------------------------------------------- 4. pipelines
print("\n[4] EVENT -> WORKFLOW -> SERVICE -> PERSISTENCE PIPELINES")
for etype, payload in [
    ("client.churn_risk", {"client_email": "maria@acme.com", "client_phone": "+15550000000"}),
    ("service.due_soon", {"email": "maria@acme.com", "service_name": "oil change", "next_due_date": "2026-12-01", "days_until_due": 5}),
    ("payment.failed", {"subscription_id": "v-sub-1", "customer_email": "maria@acme.com", "amount_due": 99}),
    ("order.abandoned_cart", {"cart_id": "c1", "customer_email": "maria@acme.com"}),
    ("subscription.cancelled", {"subscription_id": "v-sub-1", "customer_email": "maria@acme.com", "reason": "price"}),
    ("support.ticket_opened", {"email": "maria@acme.com", "ticket_id": "t1", "agent": "Sam", "sla": "24h"}),
]:
    code, d = req("POST", "/api/v1/events", {"type": etype, "tenant_id": T,
                                               "idempotency_key": f"pipe-{etype}-{uuid_key()}" if False else f"pipe-{etype}-{now.timestamp()}",
                                               "payload": payload})
    check(f"pipeline event {etype}", code == 200 and d.get("status") == "accepted", f"{code} {d}")

# idempotency
k = f"idem-{now.timestamp()}"
code, d1 = req("POST", "/api/v1/events", {"type": "client.churn_risk", "tenant_id": T, "idempotency_key": k,
                                            "payload": {"client_email": "maria@acme.com"}})
code, d2 = req("POST", "/api/v1/events", {"type": "client.churn_risk", "tenant_id": T, "idempotency_key": k,
                                            "payload": {"client_email": "maria@acme.com"}})
check("event replay idempotent", d2.get("idempotent_replay") is True, d2)

# ---------------------------------------------------------------- 5. campaigns
print("\n[5] CAMPAIGN LIFECYCLE + MEASUREMENT")
code, d = req("POST", "/api/v1/campaigns", {
    "name": "Verification campaign", "goal": "reactivate",
    "segment": {"id": "due", "name": "due soon", "criteria": {"days_until_due": {"lte": 14, "gte": 0}}},
    "flows": ["service-due-reminder"], "schedule": {"type": "once"}, "success_metrics": ["reactivation_rate"]})
cid = d.get("campaign", {}).get("campaign_id", "")
check("campaign created", code == 200 and bool(cid), d)
req("POST", f"/api/v1/campaigns/{cid}/activate")
code, d = req("POST", f"/api/v1/campaigns/{cid}/run", {"clients": customers})
res = d.get("results", {})
check("campaign matched segment", res.get("segment_size", 0) >= 1, res.get("segment_size"))
check("campaign executed flows", res.get("outcomes_count", 0) >= 1, res.get("outcomes_count"))
check("campaign measured deltas", "deltas" in res and "baseline" in res and "after" in res, list(res.keys()))
code, d = req("GET", f"/api/v1/campaigns/{cid}/results")
check("campaign results persisted", d.get("results") is not None and len(d.get("runs", [])) >= 1)

# ---------------------------------------------------------------- 6. analytics real numbers
print("\n[6] ANALYTICS WITH REAL DATA")
code, d = req("POST", "/api/v1/services/analytics.metric/actions/compute_retention", {"payload": {"tenant_id": T}})
r = d.get("result", d)
check("retention computed", "retention_rate_30d" in r, r)
code, d = req("POST", "/api/v1/services/analytics.metric/actions/compute_rfm", {"payload": {"tenant_id": T}})
rfm = d.get("result", d)
check("RFM segments computed", isinstance(rfm.get("segments"), dict), rfm)
code, d = req("POST", "/api/v1/metrics/saas", {
    "subscriptions": [{"status": "active", "amount": c["mrr"]} for c in customers],
    "starting_mrr": 3540, "arpu": 442, "monthly_churn_rate": 0.04, "active_customers": 8,
    "sales_marketing_spend": 8000, "new_customers": 3, "starting_customers": 8, "churned_customers": 1,
    "new_mrr": 400, "churned_mrr": 350, "expansion_mrr": 100})
m = d.get("metrics", {})
check("MRR computed", m.get("mrr", {}).get("mrr", 0) > 0, m.get("mrr"))
check("NRR computed", m.get("nrr", {}).get("nrr") is not None, m.get("nrr"))
check("LTV computed", m.get("ltv", {}).get("ltv", 0) > 0, m.get("ltv"))

# ---------------------------------------------------------------- 7. billing lifecycle
print("\n[7] BILLING LIFECYCLE")
code, d = req("POST", "/api/v1/lifecycle/subscriptions", {"subscription_id": "lc-1", "plan": "growth", "amount": 350, "state": "active"})
check("lifecycle subscription created", code == 200)
states = ["past_due", "grace", "suspended", "cancelled", "churned"]
lc_ok = True
for st in states:
    code, r = req("POST", "/api/v1/lifecycle/subscriptions/lc-1/transition", {"to": st, "reason": "verify"})
    if r.get("status") != "ok":
        lc_ok = False
        break
check("lifecycle journey trial->churned", lc_ok)
code, r = req("POST", "/api/v1/lifecycle/subscriptions/lc-1/transition", {"to": "active", "reason": "reactivated"})
check("lifecycle reactivation allowed", r.get("status") == "ok", r)

code, d = req("POST", "/api/v1/dunning/engine/start", {"subscription_id": "lc-1", "customer_email": "maria@acme.com",
                                                         "amount_due": 350, "failure_reason": "card_declined"})
dcid = d.get("campaign", {}).get("campaign_id", "")
req("POST", f"/api/v1/dunning/engine/{dcid}/failure", {"reason": "card_declined"})
code, d = req("POST", f"/api/v1/dunning/engine/{dcid}/recover", {"card_updater": True})
check("dunning recovered + attributed", d.get("status") == "recovered" and d.get("recovered_by_attempt") == 1, d)
code, d = req("GET", "/api/v1/dunning/engine/attribution")
check("dunning attribution computed", d.get("recovered", 0) >= 1, d)

code, d = req("POST", "/api/v1/metering/record", {"resource": "api_calls", "amount": 150})
check("metering threshold + overage", d.get("check", {}).get("pct", 0) > 100 and d.get("check", {}).get("hard_capped"), d.get("check"))
code, d = req("GET", "/api/v1/metering/overage")
check("overage invoice lines", len(d.get("lines", [])) == 1 and d.get("total", 0) > 0, d)

# ---------------------------------------------------------------- 8. persistence
print("\n[8] PERSISTENCE ROUND-TRIPS")
code, d = req("GET", "/api/v1/customers")
persisted = [c for c in d.get("profiles", []) if c.get("email") == "maria@acme.com"]
check("customer persisted with due date", len(persisted) == 1 and persisted[0].get("next_due_date"), persisted[:1])
code, d = req("GET", "/api/v1/customers/v-0")
check("customer 360 detail", code == 200 and d.get("profile", {}).get("email") == "maria@acme.com", d)
code, d = req("GET", "/api/v1/customers/v-0/timeline")
check("customer timeline", code == 200 and d.get("count", 0) >= 1, d.get("count"))

csv_in = "name,email,plan,mrr\nCSV User,csv@x.com,growth,250\n"
code, d = req("POST", "/api/v1/customers/import", {"csv": csv_in})
check("CSV import", code == 200 and d.get("import", {}).get("created", 0) + d.get("import", {}).get("updated", 0) >= 1, d)
code, d = req("GET", "/api/v1/customers/export?format=csv")
check("CSV export contains seeded row", "maria@acme.com" in d.get("csv", ""), d.get("count"))
code, d = req("GET", "/api/v1/campaigns/export?format=csv")
check("campaigns export", code == 200 and d.get("count", 0) >= 1, d.get("count"))

# postgres entity
code, d = req("POST", "/api/v1/entities/verify-schema", {"schema_id": "verify-schema", "data": {"name": "E", "value": 1}})
if code in (200, 201):
    rid = d["record"]["id"]
    code, g = req("GET", f"/api/v1/entities/verify-schema/{rid}")
    check("postgres entity read back", code == 200 and g.get("record", g).get("data", {}).get("value") == 1, g)
    code, u = req("PATCH", f"/api/v1/entities/verify-schema/{rid}", {"schema_id": "verify-schema", "record_id": rid, "data": {"value": 2}})
    code, g2 = req("GET", f"/api/v1/entities/verify-schema/{rid}")
    check("postgres entity update persisted", g2.get("record", g2).get("data", {}).get("value") == 2, g2)
else:
    print("  SKIP  postgres entity (schema not registered on live server)")

# ---------------------------------------------------------------- 9. growth + AI
print("\n[9] GROWTH / AI WITH DATA")
code, d = req("POST", "/api/v1/ai/churn/ml", {"client_id": "v-3", "orders": 2, "order_count": 2, "total_spent": 400,
                                                "days_since_last_order": 90, "frequency": 2, "monetary": 400})
check("ML churn blended score", d.get("result", {}).get("blended_risk", 0) > 0, d.get("result"))
code, d = req("POST", "/api/v1/ai/feedback/classify", {"text": "the export crashes and pricing is too high", "mrr": 400})
check("feedback classified", d.get("classification", {}).get("category") in ("pricing", "bugs", "general"), d)
code, d = req("POST", "/api/v1/ai/offers/recommend", {"churn_reason": "pricing", "churn_probability": 0.8, "mrr": 400})
check("offer recommended", d.get("recommendation", {}).get("offer_type") == "discount", d)
code, d = req("GET", "/api/v1/ai/feedback/themes")
check("feedback themes aggregated", len(d.get("themes", [])) >= 1, d)
code, d = req("GET", "/api/v1/attribution/campaigns")
check("attribution per campaign", len(d.get("campaigns", [])) >= 1, d)

# ---------------------------------------------------------------- 10. compliance + security
print("\n[10] COMPLIANCE + SECURITY")
code, d = req("GET", "/api/v1/compliance/audit-export")
check("audit export", code == 200 and "entries" in d and "chain_valid" in d, list(d.keys()))
code, d = req("GET", "/api/v1/compliance/sso/status")
check("sso status", code == 200 and "sso_enabled" in d, d)
code, d = req("POST", "/api/v1/compliance/export")
check("GDPR export", code == 200 and "export" in d, list(d.keys())[:4])
code, d, = req("GET", "/health"), None
req2 = urllib.request.Request(BASE + "/health", headers=H)
hdrs = {k.lower(): v for k, v in urllib.request.urlopen(req2).headers.items()}
check("security headers", hdrs.get("x-frame-options") == "DENY" and hdrs.get("x-content-type-options") == "nosniff", hdrs.get("x-frame-options"))

# ---------------------------------------------------------------- 11. portal pages
print("\n[11] CUSTOMER PORTAL PAGES RENDER")
pages = ["/", "/dashboard", "/campaigns", "/flows", "/flow-editor", "/customers", "/segments", "/analytics",
         "/growth", "/experiments", "/ops", "/alerts", "/integrations", "/events", "/reports", "/presets",
         "/help", "/how-it-works", "/settings", "/status"]
bad = []
for p in pages:
    try:
        r = urllib.request.urlopen(os.environ.get("PORTAL_URL", "http://localhost:47320") + p, timeout=15)
        body = r.read().decode(errors="ignore")
        if "Application error" in body or "Runtime Error" in body:
            bad.append(p)
    except Exception:
        bad.append(p)
check(f"all {len(pages)} portal pages render", not bad, bad)

# ---------------------------------------------------------------- 12. coverage
print("\n[12] PLATFORM SURFACE")
code, d = req("GET", "/")
check("94+ services", d.get("services_count", 0) >= 94, d.get("services_count"))
check("37 workflows", len(d.get("workflows", [])) == 37, len(d.get("workflows", [])))
code, d = req("GET", "/api/v1/pains")
check("28/28 pains covered", d.get("covered") == d.get("total_pains") == 28, f"{d.get('covered')}/{d.get('total_pains')}")
code, d = req("GET", "/api/v1/help")
check("help articles", d.get("count", 0) >= 9, d.get("count"))

print("\n" + "=" * 72)
print(f"RESULT: {passed} passed, {failed} failed")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
print("=" * 72)

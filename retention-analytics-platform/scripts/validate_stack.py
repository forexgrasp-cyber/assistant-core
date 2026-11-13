"""Full-stack live validation: hits every endpoint group against the running API.

Usage:
    python scripts/validate_stack.py                      # http://127.0.0.1:47319
    API_URL=http://localhost python scripts/validate_stack.py

Exits 0 if all checks pass, 1 otherwise. Run after `docker compose up` or
against the dev server to prove the whole stack works end to end.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("API_URL", "http://127.0.0.1:47319")
H = {"Authorization": "Bearer " + os.environ.get("API_TOKEN", "dev-token"), "Content-Type": "application/json"}
TENANT = "00000000-0000-0000-0000-000000000001"

passed = 0
failed = 0


def req(method: str, path: str, body: dict | None = None, qs: dict | None = None, expect: int | None = None):
    url = BASE + path
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=H, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        code = resp.status
        raw = resp.read()
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = raw.decode(errors="ignore")  # e.g. /metrics is plain text
        headers = dict(resp.headers)
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read()
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            payload = raw.decode(errors="ignore")
        headers = dict(e.headers)
    ok = (expect is None and code < 400) or (expect is not None and code == expect)
    return ok, code, payload, headers


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


print(f"=== Stack validation against {BASE} ===\n")

# --- Core ---
ok, code, d, hdrs = req("GET", "/")
check("GET / root", ok and d.get("services_count", 0) >= 70, f"{code} {str(d)[:100]}")
ok, code, d, _ = req("GET", "/health")
check("GET /health", ok and d.get("status") == "ok")
ok, code, d, _ = req("GET", "/health/ready")
check("GET /health/ready", ok)
ok, code, txt, hdrs = req("GET", "/metrics")
check("GET /metrics has data", code == 200 and len(str(txt)) > 50)
ok, code, d, hdrs = req("GET", "/health")
hdr_map = {k.lower(): v for k, v in hdrs.items()}
check("security headers (X-Frame-Options)", hdr_map.get("x-frame-options") == "DENY", str(hdr_map.get("x-frame-options")))

# --- Service surface ---
ok, code, d, _ = req("GET", "/api/v1/services")
check("GET /services 70+", ok and d.get("count", 0) >= 70, str(d.get("count")))
ok, code, d, _ = req("GET", "/api/v1/actions")
check("GET /actions catalog", ok and sum(len(s["actions"]) for s in d.get("services", [])) >= 250)

# --- Workflows ---
ok, code, d, _ = req("GET", "/api/v1/workflows")
check("GET /workflows 37", ok and len(d.get("workflows", [])) >= 37, str(len(d.get("workflows", []))))
ok, code, d, _ = req("POST", "/api/v1/workflows/service-due-reminder/run", {"context": {"email": "v@x.com", "phone": "+1", "name": "V", "service_name": "oil change", "next_due_date": "2026-12-01", "days_until_due": 5}})
check("run workflow service-due-reminder", ok and d.get("status") == "completed", str(d)[:150])

# --- Events ---
ok, code, d, _ = req("POST", "/api/v1/events", {"type": "service.due_soon", "tenant_id": TENANT, "idempotency_key": f"val-{uuid.uuid4().hex}", "payload": {"email": "v@x.com", "service_name": "oil change", "next_due_date": "2026-12-01", "days_until_due": 5, "phone": "+1"}})
check("POST /events", ok and d.get("status") == "accepted", str(d)[:100])
ok, code, d, _ = req("GET", "/api/v1/events/schemas")
check("GET /events/schemas", ok and "client.created" in d.get("schemas", {}))

# --- Customers + service due ---
ok, code, d, _ = req("POST", "/api/v1/customers", {"id": f"val-{uuid.uuid4().hex[:6]}", "name": "Val", "email": "val@x.com", "last_service_date": "2026-06-01", "service_interval_days": 180, "service_name": "oil change", "mrr": 100})
check("POST /customers computes due", ok and d["profile"].get("days_until_due") is not None, str(d)[:150])
ok, code, d, _ = req("GET", "/api/v1/service-due", qs={"within_days": 400})
check("GET /service-due scan", ok and "scanned" in d)
ok, code, d, _ = req("GET", "/api/v1/customers")
check("GET /customers list", ok and d.get("count", 0) >= 1)

# --- Campaigns lifecycle ---
ok, code, d, _ = req("POST", "/api/v1/campaigns", {"name": f"val-{uuid.uuid4().hex[:6]}", "goal": "reactivate", "segment": {"id": "all", "name": "All", "criteria": {}}, "flows": ["service-due-reminder"], "success_metrics": ["reactivation_rate"]})
cid = d.get("campaign", {}).get("campaign_id", "")
check("create campaign", ok and bool(cid), str(d)[:150])
ok, _, d, _ = req("POST", f"/api/v1/campaigns/{cid}/activate")
check("activate campaign", ok and d.get("status") == "active")
ok, _, d, _ = req("POST", f"/api/v1/campaigns/{cid}/run", {"clients": [{"id": "c1", "client_email": "a@x.com", "days_until_due": 3}]})
check("run campaign measures", ok and "results" in d and "deltas" in d["results"])
ok, _, d, _ = req("GET", "/api/v1/campaigns")
check("list campaigns", ok and d.get("count", 0) >= 1)

# --- Analytics + SaaS metrics ---
ok, code, d, _ = req("POST", "/api/v1/metrics/saas", {"subscriptions": [{"status": "active", "amount": 100}], "starting_mrr": 1000, "churned_mrr": 50, "expansion_mrr": 60, "arpu": 50, "monthly_churn_rate": 0.05, "active_customers": 20, "sales_marketing_spend": 1000, "new_customers": 10, "starting_customers": 20, "churned_customers": 1, "new_mrr": 100})
check("POST /metrics/saas computes MRR", ok and d.get("metrics", {}).get("mrr", {}).get("mrr") == 100, str(d)[:150])

# --- Pains + help + demo ---
ok, code, d, _ = req("GET", "/api/v1/pains")
check("GET /pains all covered", ok and d.get("covered") == d.get("total_pains"), f"{d.get('covered')}/{d.get('total_pains')}")
ok, code, d, _ = req("GET", "/api/v1/help")
check("GET /help articles", ok and d.get("count", 0) >= 9)
ok, code, d, _ = req("POST", "/api/v1/demo/run")
check("POST /demo/run full loop", ok and d.get("summary", {}).get("customers_seeded") == 6, str(d)[:150])

# --- Reports ---
ok, code, d, _ = req("POST", "/api/v1/reports/saved", {"name": f"val-{uuid.uuid4().hex[:6]}", "widgets": ["retention"], "filters": {"time_range": "30d"}})
rid = d.get("report", {}).get("report_id", "")
check("save report", ok and bool(rid))
ok, _, d, _ = req("POST", f"/api/v1/reports/saved/{rid}/run")
check("run saved report", ok and d.get("status") == "ok")

# --- Growth/AI/CS ---
ok, code, d, _ = req("POST", "/api/v1/ai/churn/predict", qs={"client_id": "c1", "usage_drop_pct": 80, "open_tickets": 3, "payment_failures": 2, "logins_last_30d": 1, "nps_score": 3})
check("AI churn predict", ok and d.get("prediction", {}).get("risk_level") in ("high", "critical"), str(d)[:150])
ok, code, d, _ = req("GET", "/api/v1/cs/command-center")
check("command center", ok and "overview" in d)
ok, code, d, _ = req("GET", "/api/v1/benchmarks")
check("benchmarks", ok and len(d.get("industries", {})) >= 7)
ok, code, d, _ = req("GET", "/api/v1/presets")
check("presets catalog", ok and len(d.get("presets", [])) >= 6)

# --- Compliance ---
ok, code, d, _ = req("GET", "/api/v1/compliance/audit-export")
check("audit export", ok and "entries" in d)
ok, code, d, _ = req("GET", "/api/v1/compliance/sso/status")
check("sso status", ok and "sso_enabled" in d)

# --- Payments (provider-agnostic) ---
ok, code, d, _ = req("GET", "/api/v1/payments/providers")
# Providers are env-filtered: only those with keys in .env are offered.
# Assert the filter is consistent with the supported catalogue.
supported = d.get("all_supported", [])
offered = d.get("providers", [])
check("payment catalogue complete", ok and len(supported) >= 20, len(supported))
check("offered providers are configured ones", set(offered).issubset(set(supported)), str(offered))
ok, code, d, _ = req("POST", "/api/v1/webhooks/payments/stripe", {"id": f"val-{uuid.uuid4().hex[:8]}", "type": "payment_intent.succeeded"})
check("payment webhook accepted", ok and d.get("status") == "accepted")

# --- Settings ---
ok, code, d, _ = req("GET", "/api/v1/settings")
check("settings defaults", ok and d.get("settings", {}).get("notifications", {}).get("email") is True)

print(f"\n=== {passed} passed, {failed} failed ===")
sys.exit(1 if failed else 0)

"""Verify all 7 closed Hiro gaps live."""
import os
import urllib.request, urllib.parse, json
from datetime import datetime, timedelta, timezone

BASE = "http://127.0.0.1:47319"
H = {"Authorization": "Bearer " + os.environ.get("API_TOKEN", "dev-token"), "Content-Type": "application/json"}
T = "00000000-0000-0000-0000-000000000001"
now = datetime.now(timezone.utc)

def req(m, p, b=None, qs=None, headers=None):
    url = BASE + p
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    data = json.dumps(b).encode() if b is not None else None
    r = urllib.request.Request(url, data=data, headers={**H, **(headers or {})}, method=m)
    return json.loads(urllib.request.urlopen(r, timeout=30).read())

passed = failed = 0
def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS  {name}")
    else:
        failed += 1; print(f"  FAIL  {name}  {str(detail)[:140]}")

def days_ago(d):
    return (now - timedelta(days=d)).isoformat()

print("=== 7 HIRO GAPS CLOSED — LIVE VERIFICATION ===\n")

# setup: agency client + orders
req("POST", "/api/v1/agency/clients", {"agency_id": "ag", "tenant_id": T, "name": "Trendi Apparel",
    "monthly_target": 465000, "primary_color": "#4f46e5"})
orders = [
    ("alice@x.com", 100, [{"name": "Sampler Trio", "units": 1, "revenue": 100}], False, "", 90),
    ("alice@x.com", 60, [{"name": "House Blend", "units": 1, "revenue": 60}], True, "House Blend", 50),
    ("alice@x.com", 60, [{"name": "House Blend", "units": 1, "revenue": 60}], True, "House Blend", 30),
    ("bob@x.com", 50, [{"name": "Cold Brew Pack", "units": 1, "revenue": 50}], False, "", 240),
    ("bob@x.com", 70, [{"name": "Cold Brew Pack", "units": 1, "revenue": 70}], False, "", 40),
    ("cara@x.com", 80, [{"name": "Single Origin Box", "units": 1, "revenue": 80}], False, "", 80),
    ("cara@x.com", 55, [{"name": "Single Origin Box", "units": 1, "revenue": 55}], True, "Single Origin Box", 39),
]
for email, amount, products, is_sub, sub_product, ago in orders:
    req("POST", "/api/v1/commerce/orders", {
        "customer_email": email, "amount": amount, "products": products,
        "is_subscription": is_sub, "subscription_product": sub_product,
        "campaign_id": "camp-1" if email == "alice@x.com" and ago == 30 else "",
        "placed_at": days_ago(ago)})

# GAP 1: time between orders
r = req("GET", "/api/v1/commerce/time-between-orders")
check("gap1 time-between-orders computed", r["all_reorders"] >= 3 and r["median_gap_days"] > 0, r)
check("gap1 attributed vs organic split", r["after_campaign"]["reorders"] >= 1 and r["on_their_own"]["reorders"] >= 1, r)
check("gap1 reorder buckets", len(r["buckets"]) == 7, r["buckets"])

# GAP 2: product paths
r = req("GET", "/api/v1/commerce/product-paths")
check("gap2 product paths built", len(r["paths"]) >= 1 and r["customers"] >= 3, r)
check("gap2 retention by product", len(r["by_product"]) >= 3, r["by_product"])
r2 = req("GET", "/api/v1/commerce/product-paths", qs={"keyword": "cold"})
check("gap2 keyword filter", {p["product"] for p in r2["by_product"]} == {"Cold Brew Pack"}, r2["by_product"])

# GAP 3: sub LTV / one-time->sub / trends
r = req("GET", "/api/v1/commerce/subscription-ltv")
check("gap3 subscription LTV by product", r["total_subscription_starts"] >= 3 and len(r["by_product"]) >= 2, r)
check("gap3 LTV at 1/3/6/12m", all(len(p["ltv"]) == 4 for p in r["by_product"]), r["by_product"][:1])
r = req("GET", "/api/v1/commerce/one-time-to-subscriber")
check("gap3 one-time->subscriber conversion", r["converted"] >= 1 and r["conversion_rate"] > 0, r)
check("gap3 avg days to subscribe", r["avg_days_to_subscribe"] is not None, r)
r = req("GET", "/api/v1/commerce/product-trends")
check("gap3 product trends (starts/growing/cancels/addon)", all(k in r for k in ("most_new_starts", "fastest_growing", "most_cancels", "top_add_on")), list(r.keys()))

# GAP 4: RFM movement
r = req("GET", "/api/v1/commerce/rfm-movement")
check("gap4 RFM movement segments", len(r["segments"]) == 5 and all("net_change" in s for s in r["segments"]), r)
check("gap4 biggest moves + attribution", "biggest_moves" in r and "attributed_share" in r, list(r.keys()))

# GAP 5: report deck
r = req("GET", "/api/v1/agency/roster?agency_id=ag")
cid = r["clients"][0]["client_id"]
r = req("POST", "/api/v1/agency/deck", {"client_id": cid, "agency_id": "ag", "period": "September"})
deck = r["deck"]
check("gap5 deck has 5 slides", len(deck["slides"]) == 5, len(deck.get("slides", [])))
r = req("POST", "/api/v1/agency/deck/render", {"deck": deck})
check("gap5 deck renders print-ready HTML", "page-break-after" in r["html"] and "Trendi Apparel" in r["html"], r.get("slides"))

# GAP 6: role views
r = req("GET", "/api/v1/agency/view", qs={"role": "leadership", "agency_id": "ag"})
check("gap6 leadership view", r["role"] == "leadership" and "behind_goal" in r["headline"], list(r.keys()))
r = req("GET", "/api/v1/agency/view", qs={"role": "account_manager", "agency_id": "ag", "client_id": cid})
check("gap6 account-manager view", r["role"] == "account_manager" and r["client"]["name"] == "Trendi Apparel", r.get("client", {}))
r = req("GET", "/api/v1/agency/view", qs={"role": "copywriter", "tenant_id": T})
check("gap6 copywriter view", r["role"] == "copywriter" and "best_slot" in r["headline"], list(r.keys()))

# GAP 7: NL Q&A
r = req("POST", "/api/v1/agency/ask", {"agency_id": "ag", "question": "Which clients are behind their revenue goal this month?"})
check("gap7 NL answer: behind goal", r["intent"] == "clients_behind" and "behind goal" in r["answer"].lower(), r)
r = req("POST", "/api/v1/agency/ask", {"agency_id": "ag", "question": "what is our total revenue?"})
check("gap7 NL answer: revenue", r["intent"] == "revenue_overview" and "$" in r["answer"], r)
r = req("POST", "/api/v1/agency/ask", {"agency_id": "ag", "question": "any churn risk on our clients?"})
check("gap7 NL answer: churn risk", r["intent"] == "churn_risk", r)
r = req("GET", "/api/v1/agency/questions")
check("gap7 question suggestions", len(r["questions"]) >= 5, len(r.get("questions", [])))

print(f"\n=== {passed} passed, {failed} failed ===")

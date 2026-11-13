# Hiro Analytics — competitor analysis & how we beat it

Research: hiroanalytics.com (fetched 2026-11-12). Hiro = **"Retention analytics for agencies"** —
a direct competitor in our space, but with a narrower wedge: **read-only analytics for agencies**
running email/SMS/subscription programs for ecommerce brands.

## Their positioning vs ours

| | Hiro | Snapford Retention |
|---|---|---|
| Audience | Retention **agencies** (multi-client roster) | Any subscription business — and agencies (roster layer) |
| Depth | **Reports on** Klaviyo/Shopify/Recharge data | Same platforms **plus** 95 services that **execute** retention |
| Action | "Here is what happened" | "Here is what happened **and here is what we did about it, measured before/after**" |
| Automation | None (analytics only) | 37 workflows, campaigns, auto-approach, dunning, win-back |
| Delivery | Dashboards, PDF decks, Slack digests, MCP | Same **plus** white-label share links, MCP, REST API, scheduled digests |

**Our wedge:** Hiro can tell an agency which client is behind goal. We can tell them *and* automatically run the campaign, then prove the delta. Their "pacing behind goal" flag becomes our auto-approach trigger.

## Feature-by-feature

| Hiro feature | Their screen | Our implementation | Status |
|---|---|---|---|
| Client roster, per-client revenue, pacing vs goal, behind-goal flags | "All clients" table, goal pacing | `agency` service — roster with MTD revenue, pacing %, status (`behind_goal`, `revenue_down`, `deliverability`, `churn_risk`), MRR at risk | **Parity** |
| Connectors: Klaviyo, Attentive, Postscript, Omnisend, Sendlane | Integrations table | `connectors.agency` — all 12 agency platforms + Stripe/Mailchimp/Braze, env-gated real pulls | **Parity+** |
| Shopify (products, orders, revenue, AOV, first-time vs returning) | Store column | Shopify connector normalising products/orders/revenue/AOV/new-vs-returning | **Parity** |
| Subscription platforms: Recharge, Skio, Loop, Stay AI, Ordergroove | Subscriptions column | Same 5 connectors + our subscription lifecycle engine (trial→churn, dunning escalation) | **Parity+** |
| Popups: Alia | Popups column | Alia connector | **Parity** |
| Campaign deep dive: creative + subject next to open/click/revenue, products, new vs returning, A/B, send by send | "Campaign Deep Dive" | `analytics.performance.campaign_deep_dive` — identical shape | **Parity** |
| Flow map: triggers, splits, delays, numbers + creative per message, compare flows | "Flow Map" | `analytics.performance.flow_map` (per-message metrics) + `flows.editor` canvas (drag/connect/publish) | **Parity+** (we can also edit and run flows) |
| Message timing: weekday × hour heatmap, static vs recipient-local separately, subjects by open rate | "Message Timing" | `analytics.performance.message_timing` — identical, incl. the static/local split | **Parity** |
| Attribution: per-client rules, email/SMS/push side by side, share of store revenue | "Attribution" | 5 models (first/last/linear/time-decay/position) + per-campaign value saved; rules configurable per client | **Parity+** |
| Deliverability: score + history, bounce/spam/unsub by inbox provider, offenders ranked | "Deliverability" | `analytics.performance.deliverability` — score, provider rates, biggest offender, history | **Parity** (+ shared warmup/DNS tooling) |
| Repeat purchase 1/3/6/12m, days to 2nd order, attributed vs unattributed | "Repeat Purchase" | Cohorts + retention metrics + attribution | **Parity** |
| RFM segments with movement + campaigns behind them + push to Klaviyo | "RFM movement" | `analytics.commerce.rfm_movement` + `connectors.segment_push` (Klaviyo/Attentive/Omnisend/Sendlane/Postscript) | **Parity** |
| Time between orders (after campaign vs on their own) | "Time Between Orders" | `analytics.commerce.time_between_orders` — median gap, attributed vs organic, 7 buckets | **Parity** |
| Product paths (1st to 2nd to 3rd purchase) | "Product Purchase Paths" | `analytics.commerce.product_paths` + keyword filter | **Parity** |
| Subscription LTV by product, one-time to subscriber | "Subscriptions" | `analytics.commerce.subscription_ltv` + `.one_time_to_subscriber` + `.product_trends` | **Parity** |
| White-label client dashboards under agency brand | `reports.youragency.com/trendi` | `agency.share_dashboard` → tokenised `/share/{token}` page with client branding | **Parity** |
| Branded PDF report decks | "Report decks" | `agency.deck` — 5-slide branded deck, print-to-PDF HTML with agency colours | **Parity** |
| Scheduled Slack updates per client | "Slack updates" | `agency.schedule_digest` + Slack connector + bot commands | **Parity** |
| Role views: account manager / leadership / copywriter | "For your whole team" | `agency.roles` — three role views, switchable in `/ask` | **Parity** |
| "Ask Hiro" MCP/Claude/ChatGPT per client | Claude/ChatGPT/MCP | `agency.qa` (NL per-client Q&A over live roster) + MCP server + REST API | **Parity** |
| Action: none | — | **Campaigns, flows, auto-approach, dunning, win-back, NPS loops** | **We win** |
| Retention automation (dunning, cancel flows, win-back, NPS) | Not offered | 37 workflows covering 28 user pains | **We win** |

## Where we beat them

1. **Action, not just reporting.** Every "here is what happened" screen feeds an action:
   behind-goal → auto-approach campaign; churn risk → save offer flow; overdue service →
   recovery campaign; bounce rate → deliverability fix.
2. **Broader data model.** 95 services / 263 actions / 37 workflows vs their 5 dashboards.
   We cover the whole lifecycle (billing state machine, dunning escalation, metering/overage,
   proration, health decay, renewals risk, NPS loops), not just marketing analytics.
3. **Automation + measurement in one loop.** Hiro's value stops at attribution. Ours closes:
   segment → campaign → run → before/after delta → saved report → refined segment.
4. **Not limited to ecommerce marketing.** Their connectors are Klaviyo/Shopify-shaped.
   Ours work on any record fields — oil change, gym membership, prescriptions, maintenance.
5. **One account across clients.** Same SSO, same platform, per-client branding and goals.

## Where they still beat us — CLOSED 2026-11-13

| Their edge (was our gap) | Our implementation now | Status |
|---|---|---|
| Time between orders (after campaign vs on their own) | `analytics.commerce.time_between_orders` — median gap, attributed vs organic split, 7 reorder buckets | **Closed** |
| Product purchase paths (1st to 2nd to 3rd) | `analytics.commerce.product_paths` — paths, retention by product, keyword filter | **Closed** |
| Subscription LTV by product at 1/3/6/12m + one-time to subscriber | `analytics.commerce.subscription_ltv` + `.one_time_to_subscriber` — conversion %, avg days to subscribe, best first product | **Closed** |
| Product trends (most starts, fastest growing, most cancels, top add-on) | `analytics.commerce.product_trends` | **Closed** |
| RFM movement over time | `analytics.commerce.rfm_movement` — segment counts, net change, biggest moves with campaign attribution | **Closed** |
| Branded PDF report decks | `agency.deck` — 5-slide branded deck, print-to-PDF HTML with agency colours | **Closed** |
| Role views (leadership / account manager / copywriter) | `agency.roles` — three role-specific views | **Closed** |
| "Ask Hiro" natural-language per-client Q&A | `agency.qa` — intent parsing over live roster data ("which clients are behind?") | **Closed** |

**Parity achieved on every screen they sell.** We still add what they do not have:
action (campaigns/flows/auto-approach), 72 services / 263 actions / 37 workflows,
full billing lifecycle, and universal (non-ecommerce) applicability.

## Where we beat them

1. **Action, not just reporting.** Every "here is what happened" screen feeds an action:
   behind-goal -> auto-approach campaign; churn risk -> save offer flow; overdue service ->
   recovery campaign; bounce rate -> deliverability fix.
2. **Broader data model.** 72 services / 263 actions / 37 workflows vs their 5 dashboards.
   We cover the whole lifecycle (billing state machine, dunning escalation, metering/overage,
   proration, health decay, renewals risk, NPS loops), not just marketing analytics.
3. **Automation + measurement in one loop.** Hiro's value stops at attribution. Ours closes:
   segment -> campaign -> run -> before/after delta -> saved report -> refined segment.
4. **Not limited to ecommerce marketing.** Their connectors are Klaviyo/Shopify-shaped.
   Ours work on any record fields — oil change, gym membership, prescriptions, maintenance.
5. **One account across clients.** Same SSO, same platform, per-client branding and goals.

## Verification

`scripts/verify_platform.py` (51 checks) + `scripts/verify_hiro_gaps.py` (22 checks) +
`tests/test_agency_performance.py` (8) + `tests/test_hiro_gaps_closed.py` (7) — all passing.
Live: 23/23 portal pages render; **22/22 Hiro-parity checks pass**.

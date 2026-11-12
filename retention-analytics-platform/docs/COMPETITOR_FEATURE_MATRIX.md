# Competitor Feature Matrix — Retention / CS Platforms

Research date: 2026-11-11. Sources: official feature pages of each vendor.

## Feature inventory by competitor

### Baremetrics
Control Center · Smart Dashboards · Forecasting · Recover (dunning) · Cancellation Insights (exit surveys + win-back) · Benchmarks (industry) · Goals · Trial Insights (experiment notes) · Augmentation (external data merge) · Segmentation · People Insights (customer timeline) · Email Reports (scheduled) · Analytics API · MCP · Open Benchmarks/Startups · 10 billing integrations

### Churnkey
Cancel Flows (dynamic offers: discount/pause/cross-sell/seat handoff, Pause Wall) · Payment Recovery (ML Precision Retries, omnichannel Dunning Campaigns, Payment Wall) · Feedback AI (categorize, MRR-rank, NL search) · Churn Metrics · Adaptive Offers · Account Agent · Annual Upsells · Pulse (in-product micro-surveys) · Customer Return Campaigns (reactivation) · Subscription Pauses · Customer Health (predictive) · Segmentation · Customer Timelines · Session Recordings · No-Code Flow Editor · Webhooks · Open SDK (React/Node/MCP) · GDPR

### ChurnZero
Customer Profiles · Health Scores (ChurnScores) · Segments · Command Center · Playbooks · Journeys · Real-time Alerts · Success Plans · Launchpad (templates) · In-app Communications · WalkThroughs · Success Centers · Surveys (NPS/CES/CSAT) · Customer Communities · Learning Management · Account Insights · Success Insights · Renewal & Forecast Hub · AI Agents (Harbinger) · Kit AI Assistant · Engagement AI · Snapshot AI · MCP Connect · 70+ integrations · SOC2/ISO27001

### Vitally
Quin AI Assistant · Playbooks (automation) · Project Management · Hubs · Collaborative Docs · Surveys · Smart Meetings · Health Scores · NPS · Custom Surveys · Reporting · Note Taking · Blueprints (templates) · 40+ integrations

### Enterprise CS (Gainsight / Totango / Planhat / Catalyst)
Customer 360 · Journey Orchestrator · Success Plans + Milestones · QBRs · Touchpoints (calls/meetings/emails log) · Playbooks · Risk management · Expansion/contraction plays · NRR/GRR programs · Segment health · Attribution · Board-ready reporting · Slack/Teams bots · Email drip sequences · A/B testing · Cohort comparison · Predictive analytics · CES · Voice of Customer · Product analytics integration (Pendo/Amplitude/Mixpanel) · Ticketing integration (Zendesk)

### ChurnBuster / ProfitWell / ChartMogul / Delighted / Stripe Retention
Dunning smart retries · Cancel flows · MRR/ARR/churn analytics · Cohort analysis · Forecasting · Pricing experiments · NPS/CSAT/CES surveys · Card update campaigns

---

## Our coverage vs matrix

| Feature | Competitor | Status |
|---------|-----------|--------|
| Dunning / payment recovery (retries, omnichannel, walls) | Baremetrics, Churnkey, ChurnBuster, Stripe | ✅ dunning service; ❌ walls |
| Cancel flows + exit survey + save offers | Baremetrics, Churnkey, ProfitWell | ✅ cancel-flow workflow |
| Predictive churn / health scores | Churnkey, ChurnZero, Vitally | ✅ ai.churn_predict + health.scoring |
| Segmentation (dynamic, criteria-based) | all | ✅ segmentation + campaign segment eval |
| Cohorts, RFM, retention metrics | Baremetrics, ChartMogul | ✅ analytics.* |
| Full SaaS metrics (MRR/ARR/GRR/NRR/LTV/CAC/payback/logo/quick) | Baremetrics, ChartMogul, ProfitWell | ✅ saas.metrics |
| Forecasting | Baremetrics, ChartMogul | ✅ forecasting |
| Surveys NPS/CSAT | Vitally, ChurnZero, Delighted | ✅ surveys; ❌ CES, micro-surveys (Pulse) |
| Feedback AI (classify, rank, search) | Churnkey | ✅ ai.feedback; ❌ public VoC board |
| Offer recommendation (adaptive offers) | Churnkey | ✅ ai.offers |
| Playbooks / journeys automation | ChurnZero, Vitally, Gainsight | ✅ cs.playbooks; ❌ journeys with stages |
| Success plans + milestones | ChurnZero, Vitally, Gainsight | ✅ cs.plans |
| Real-time alerts + command center | ChurnZero | ✅ cs.alerts + cs.command_center |
| Renewal hub + forecast | ChurnZero | ✅ cs.renewals |
| Customer 360 / timeline / people insights | Baremetrics, Churnkey, Gainsight | ❌ MISSING |
| Benchmarks (industry comparison) | Baremetrics | ❌ MISSING |
| Goals tracking | Baremetrics | ❌ MISSING |
| A/B testing campaigns/offers | Gainsight, ProfitWell pricing | ❌ MISSING |
| Anomaly detection on metrics | — (advanced) | ❌ MISSING |
| Attribution (which campaign saved whom) | Gainsight | ❌ MISSING |
| Augmentation (external data merge) | Baremetrics | ❌ MISSING |
| Touchpoints log (calls/meetings/emails) | Gainsight, Totango | ❌ MISSING |
| Session recordings | Churnkey | ❌ MISSING |
| Email drip sequences (multi-touch) | Gainsight, ChurnZero journeys | ❌ MISSING |
| Cross-sell campaigns + product catalog | Churnkey cancel flows | ❌ MISSING |
| Pricing experiments | ProfitWell | ❌ MISSING |
| QBR generation | Gainsight | ❌ MISSING |
| Pause/Payment walls (feature gating) | Churnkey | ❌ MISSING |
| Trial insights / experiment notes | Baremetrics | ❌ MISSING |
| Scheduled email reports (cron worker) | Baremetrics | ⚠️ schedule field exists, no worker |
| Slack/Teams interactive bots | ChurnZero, Gainsight | ⚠️ slack send only |
| Universal export (any dataset → CSV) | ChartMogul | ⚠️ events export only |
| Service-due reminders (universal, data-driven) | — (our addition) | ❌ MISSING |
| In-app walkthroughs/banners | ChurnZero | ✅ inapp.messaging |
| Webhooks management | Churnkey | ✅ webhooks.manage |
| Integrations catalog | ChurnZero 70+, Vitally 40+ | ✅ 28+ catalog |
| GDPR/CCPA, SOC2 audit, SSO | Churnkey, ChurnZero | ✅ compliance.* |
| MCP server | Baremetrics, Churnkey, ChurnZero | ✅ apps/mcp_server |

## Implementation plan (this phase)
All new features are UNIVERSAL services — no vertical gating. Vertical packs become pure presets (apply to any industry where the customer's data has the fields).

## Status after implementation — 72 services, 263 actions, 24 workflows, 190+ routes

| Feature | Competitor | Status | Where |
|---------|-----------|--------|-------|
| Dunning / payment recovery (retries, omnichannel) | Baremetrics, Churnkey, ChurnBuster | ✅ | `dunning` service |
| Pause Wall / Payment Wall (feature gating) | Churnkey | ✅ | `walls` service + cancel-flow API |
| Cancel flows + exit survey + save offers + public SDK API | Baremetrics, Churnkey | ✅ | `cancel-flow` workflow + `cancel_flow.api` |
| Predictive churn / health scores | Churnkey, ChurnZero, Vitally | ✅ | `ai.churn_predict`, `health.scoring` |
| Segmentation (dynamic, criteria-based, live preview) | all | ✅ | `segmentation`, `campaigns.evaluate_segment` |
| Cohorts, RFM, retention metrics | Baremetrics, ChartMogul | ✅ | `analytics.metric`, `analytics.cohort` |
| Full SaaS metrics (MRR/ARR/GRR/NRR/LTV/CAC/payback/logo/quick) | Baremetrics, ChartMogul | ✅ | `saas.metrics` (10 metrics) |
| Forecasting | Baremetrics, ChartMogul | ✅ | `forecasting` |
| Surveys NPS/CSAT + CES + micro-surveys (Pulse) | Vitally, ChurnZero, Delighted, Churnkey | ✅ | `surveys`, `surveys.micro` |
| Feedback AI (classify, rank by MRR, search) | Churnkey | ✅ | `ai.feedback` |
| Public Voice-of-Customer board (upvotes, roadmap status) | Gainsight | ✅ | `feedback.voc` |
| Offer recommendation (adaptive offers) | Churnkey | ✅ | `ai.offers` |
| Product + offer catalog, cross-sell | Churnkey cancel flows | ✅ | `catalog` |
| A/B testing with winner + lift + notes | Gainsight | ✅ | `experiments.ab` |
| Pricing experiments (best price by revenue) | ProfitWell | ✅ | `experiments.pricing` |
| Experiment notes / trial insights | Baremetrics | ✅ | `experiments.ab.annotate` |
| Multi-touch drip sequences | Gainsight, ChurnZero journeys | ✅ | `automation.sequences` |
| No-code flow editor (graph CRUD, validate, publish) | Churnkey No-Code Editor | ✅ | `flows.editor` |
| Playbooks / journeys automation | ChurnZero, Vitally, Gainsight | ✅ | `cs.playbooks`, `journeys` |
| Multi-stage customer journeys | Gainsight Journey Orchestrator | ✅ | `journeys` (6 stages) |
| Success plans + milestones | ChurnZero, Vitally, Gainsight | ✅ | `cs.plans` |
| Real-time alerts + command center | ChurnZero | ✅ | `cs.alerts`, `cs.command_center` |
| Renewal hub + forecast | ChurnZero | ✅ | `cs.renewals` |
| Customer 360 (profile + enrichment + touchpoints + recordings) | Baremetrics People Insights, Gainsight | ✅ | `customers.360` |
| Unified customer timeline | Baremetrics, Churnkey | ✅ | `customers.360.timeline` |
| Augmentation (external data merge) | Baremetrics | ✅ | `customers.360.enrich` |
| Touchpoints log (calls/meetings/emails/notes) | Gainsight, Totango | ✅ | `customers.360.log_touchpoint` |
| Session recordings + replay ingest | Churnkey | ✅ | `customers.360.link_recording`, `session.replay` |
| QBR generation | Gainsight | ✅ | `cs.qbr` |
| Benchmarks (7 industries) | Baremetrics Open Benchmarks | ✅ | `benchmarks` |
| Goals tracking with progress | Baremetrics | ✅ | `goals` |
| Anomaly detection on metric series | — (advanced) | ✅ | `analytics.anomaly` |
| Attribution (value saved per campaign) | Gainsight | ✅ | `analytics.attribution` |
| Scheduled reports + email delivery (Celery beat) | Baremetrics Email Reports | ✅ | `reports.scheduler` + beat task |
| Service-due reminders (universal, date+interval, cron scan) | — (our addition) | ✅ | `customers.service_due` + 2 workflows + beat task |
| In-app banners + walkthroughs | ChurnZero | ✅ | `inapp.messaging` |
| Webhooks management + DLQ | Churnkey | ✅ | `webhooks.manage`, `webhooks_out` |
| Integrations catalog (28+) + Slack bot commands | ChurnZero 70+, Vitally 40+, Gainsight | ✅ | `integrations`, `integrations.bot` |
| GDPR/CCPA, SOC2 audit export, SSO/SAML | Churnkey, ChurnZero | ✅ | `compliance.*` |
| Slack messaging + bot slash commands | ChurnZero, Gainsight | ✅ | `integrations.slack`, `integrations.bot` |
| MCP server | Baremetrics, Churnkey, ChurnZero | ✅ | `apps/mcp_server` |
| Universal dataset export (CSV/JSON) | ChartMogul | ✅ | `export` service (18 datasets) |
| Industry presets (optional, apply anywhere) | — (our addition) | ✅ | `presets` service (6 packs) |

| Feature | Competitor | Status | Where |
|---------|-----------|--------|-------|
| Dunning / payment recovery (retries, omnichannel) | Baremetrics, Churnkey, ChurnBuster | ✅ | `dunning` service |
| Pause Wall / Payment Wall (feature gating) | Churnkey | ✅ | `walls` service |
| Cancel flows + exit survey + save offers | Baremetrics, Churnkey | ✅ | `cancel-flow` workflow |
| Predictive churn / health scores | Churnkey, ChurnZero, Vitally | ✅ | `ai.churn_predict`, `health.scoring` |
| Segmentation (dynamic, criteria-based, live preview) | all | ✅ | `segmentation`, `campaigns.evaluate_segment` |
| Cohorts, RFM, retention metrics | Baremetrics, ChartMogul | ✅ | `analytics.metric`, `analytics.cohort` |
| Full SaaS metrics (MRR/ARR/GRR/NRR/LTV/CAC/payback/logo/quick) | Baremetrics, ChartMogul | ✅ | `saas.metrics` (10 metrics) |
| Forecasting | Baremetrics, ChartMogul | ✅ | `forecasting` |
| Surveys NPS/CSAT + CES | Vitally, ChurnZero, Delighted | ✅ | `surveys` |
| Feedback AI (classify, rank by MRR, search) | Churnkey | ✅ | `ai.feedback` |
| Public Voice-of-Customer board (upvotes, roadmap status) | Gainsight | ✅ | `feedback.voc` |
| Offer recommendation (adaptive offers) | Churnkey | ✅ | `ai.offers` |
| Product + offer catalog, cross-sell | Churnkey cancel flows | ✅ | `catalog` |
| A/B testing with winner + lift | Gainsight | ✅ | `experiments.ab` |
| Pricing experiments (best price by revenue) | ProfitWell | ✅ | `experiments.pricing` |
| Experiment notes / trial insights | Baremetrics | ✅ | `experiments.ab.annotate` |
| Multi-touch drip sequences | Gainsight, ChurnZero journeys | ✅ | `automation.sequences` |
| Playbooks / journeys automation | ChurnZero, Vitally, Gainsight | ✅ | `cs.playbooks`, `journeys` |
| Multi-stage customer journeys | Gainsight Journey Orchestrator | ✅ | `journeys` (6 stages) |
| Success plans + milestones | ChurnZero, Vitally, Gainsight | ✅ | `cs.plans` |
| Real-time alerts + command center | ChurnZero | ✅ | `cs.alerts`, `cs.command_center` |
| Renewal hub + forecast | ChurnZero | ✅ | `cs.renewals` |
| Customer 360 (profile + enrichment + touchpoints + recordings) | Baremetrics People Insights, Gainsight | ✅ | `customers.360` |
| Unified customer timeline | Baremetrics, Churnkey | ✅ | `customers.360.timeline` |
| Augmentation (external data merge) | Baremetrics | ✅ | `customers.360.enrich` |
| Touchpoints log (calls/meetings/emails/notes) | Gainsight, Totango | ✅ | `customers.360.log_touchpoint` |
| Session recordings | Churnkey | ✅ | `customers.360.link_recording` |
| QBR generation | Gainsight | ✅ | `cs.qbr` |
| Benchmarks (7 industries) | Baremetrics Open Benchmarks | ✅ | `benchmarks` |
| Goals tracking with progress | Baremetrics | ✅ | `goals` |
| Anomaly detection on metric series | — (advanced) | ✅ | `analytics.anomaly` |
| Attribution (value saved per campaign) | Gainsight | ✅ | `analytics.attribution` |
| Scheduled/saved reports with filters + widgets | Baremetrics Email Reports | ✅ | `ux.reports` (schedule field; worker pending) |
| Service-due reminders (universal, date+interval) | — (our addition) | ✅ | `customers.service_due` + 2 workflows |
| In-app banners + walkthroughs | ChurnZero | ✅ | `inapp.messaging` |
| Webhooks management + DLQ | Churnkey | ✅ | `webhooks.manage`, `webhooks_out` |
| Integrations catalog (28+) | ChurnZero 70+, Vitally 40+ | ✅ | `integrations` |
| GDPR/CCPA, SOC2 audit export, SSO/SAML | Churnkey, ChurnZero | ✅ | `compliance.*` |
| Slack messaging | ChurnZero, Gainsight | ✅ | `integrations.slack` |
| MCP server | Baremetrics, Churnkey, ChurnZero | ✅ | `apps/mcp_server` |
| Industry presets (optional, apply anywhere) | — (our addition) | ✅ | `presets` service (6 packs) |

### Still not implemented
- Native mobile SDK / session replay capture agent (recording URLs are stored; ingest endpoint exists, capture agent not included)
- Embeddable cancel/payment wall UI components (server-side API + enforcement exist; frontend embed is per-client build)


# Retention Operating System — Comprehensive Competitive Benchmark

**Generated:** 2026-11-15  
**Snapford Version:** 72+ services / 263+ actions / 37 workflows  
**Methodology:** Feature-by-feature mapping across 18 top competitors in 4 categories

---

## Competitor Landscape

| Category | Competitors | Primary Focus |
|----------|-------------|---------------|
| **Engagement Platforms** | Braze, Customer.io, Iterable, MoEngage, CleverTap, WebEngage, Airship, OneSignal | Cross-channel messaging + journeys |
| **Ecommerce Marketing** | Klaviyo, Omnisend, Drip, Listrak, Bluecore, Retention Science | Ecommerce-specific retention |
| **Marketing Automation** | HubSpot, ActiveCampaign, Bloomreach | CRM + email + workflows |
| **Customer Success** | ChurnZero, Gainsight, Totango, Vitally, Catalyst, Planhat | B2B SaaS retention/expansion |
| **Data/Analytics** | Segment, RudderStack, mParticle, Amplitude, Mixpanel | CDP / Product analytics |
| **Identity/Analytics** | Hiro Analytics, Retention.com | Agency analytics / Identity resolution |

---

## Service Inventory — Snapford Retention OS

### Core Platform Services (89 services)

| # | Service | Domain | Key Actions |
|---|---------|--------|-------------|
| 1 | **CampaignService** | campaigns | create, launch, schedule, clone, ab_test, pause, resume, metrics |
| 2 | **FlowManagementService** | flows | create, publish, version, trigger, test, debug, canvas (drag-drop) |
| 3 | **FlowEditorService** | flows | visual builder, node palette, connect, validate, export/import |
| 4 | **FlowTriggerService** | flows | event_match, schedule, segment_entry, api, webhook, manual |
| 5 | **EmailService** | email | send, template, render, preview, track, suppress, bounce_handle |
| 6 | **SmsService** | sms | send, template, short_code, toll_free, compliance, opt_out |
| 7 | **PushService** | push | send, template, fcm, apns, web_push, rich_media, action_buttons |
| 8 | **InAppMessagingService** | in_app | show, target, schedule, dismiss, track, nps, survey |
| 9 | **SegmentationService** | segmentation | create, compute, refresh, export, push_to_connector, lookalike |
| 10 | **Customer360Service** | customer_intel | profile, timeline, health, ltv, churn_risk, next_best_action |
| 11 | **NextBestActionService** | analysis | recommend, priority, channel, offer, flow, reason |
| 12 | **AutoApproachService** | analysis | scan, create_campaigns, execute, measure_delta |
| 13 | **TailoredContentService** | analysis | generate, personalize, variant_select, ab_test |
| 14 | **HealthScoringService** | growth | compute, tier, decay, alert, history, explain |
| 15 | **DunningService** | growth | escalate, retry, recover, cancel_save, pause, customize |
| 16 | **SurveyService** | growth | nps, csat, ces, trigger, analyze, close_loop |
| 17 | **ForecastingService** | growth | revenue, churn, ltv, scenario, confidence_interval |
| 18 | **NPSLoopService** | loops | survey → segment → follow_up → measure |
| 19 | **ExperimentAutoPromoteService** | loops | detect_winner → promote → archive_loser |
| 20 | **IncidentService** | loops | detect → alert → runbook → resolve → postmortem |
| 21 | **WinbackTimingService** | loops | optimize_send_time → measure_lift |
| 22 | **RenewalRiskService** | renewals | score, tier, alert, playbook, track_save |
| 23 | **LifecycleService** | lifecycle | state_machine: trial→active→past_due→dunning→churned→reactivated |
| 24 | **MeteringService** | billing | track_usage, aggregate, bill, overage, alert |
| 25 | **ProrationService** | billing | calculate, apply, preview, credit, debit |
| 26 | **SubscriptionService** | subscriptions | create, pause, resume, cancel, upgrade, downgrade, trial |
| 27 | **PaymentService** | payments | charge, refund, retry, method_update, failed_payment_flow |
| 28 | **EcommerceCoreService** | ecommerce | orders, products, carts, catalog, inventory_sync |
| 29 | **ConnectorService** | integrations | 27+ connectors, sync, map, transform, validate, webhook |
| 30 | **AgencyConnectorService** | agency | multi-client roster, platform catalog, sync history |
| 31 | **AgencyService** | agency | roster, metrics, digest, auto_act, share, roles, qa, deck |
| 32 | **AgencyQAService** | agency | nl_query: clients_behind, revenue, churn_risk, alerts, etc. |
| 33 | **RoleViewService** | agency | leadership, account_manager, copywriter views |
| 34 | **ReportDeckService** | agency | 5-slide branded PDF, auto-generate, schedule |
| 35 | **SegmentPushService** | connectors | push_segments to Klaviyo/Attentive/Omnisend/Sendlane/Postscript |
| 36 | **IntegrationRegistryService** | integrations | register, discover, test, monitor, version |
| 37 | **SlackAlertService** | integrations | send, list, bot_command (/roster, /digest, /act) |
| 38 | **WebhookManagementService** | integrations | register, test, deliveries, dlq, retry, signature_verify |
| 39 | **HiroWebhookService** | integrations | receive hiro events, trigger sync/auto_act/digest |
| 40 | **HiroMCPService** | mcp | ask_hiro, roster, platforms, sync, syncs |
| 41 | **ABTestingService** | experiments | create, variant, traffic_split, measure, promote, archive |
| 42 | **SequenceService** | experiments | multi-step, branching, delay, condition, goal |
| 43 | **CatalogService** | experiments | product/content catalog, recommendation, personalization |
| 44 | **WallsService** | experiments | holdout, global_control, exposure_limit |
| 45 | **JourneyService** | experiments | multi-touch, cross-channel, attribution, milestone |
| 46 | **AttributionService** | attribution | record_outcome, for_customer, campaign_impact, 5 models |
| 47 | **MultiTouchAttribution** | attribution | record_touch, attribute (first/last/linear/time_decay/position) |
| 48 | **AnomalyDetectionService** | analytics | detect, threshold, baseline, alert, root_cause_link |
| 49 | **RootCauseService** | analytics | correlate, explain, drill_down, contributing_factors |
| 50 | **PricingExperimentService** | experiments | price_test, elasticity, revenue_impact, confidence |
| 51 | **QBRService** | analytics | quarterly_review, deck, metrics, insights, action_items |
| 52 | **CohortService** | analytics | retention, revenue, engagement, size, compare |
| 53 | **MetricService** | analytics | compute, define, schedule, alert, dashboard, export |
| 54 | **SaasMetricsService** | analytics | arr, mrr, nrr, ltv, cac, payback, quick_ratio, churn |
| 55 | **BenchmarksService** | customer_intel | industry, peer, percentile, trend, anonymized |
| 56 | **GoalsService** | customer_intel | set, track, pace, alert, achieve, celebrate |
| 57 | **VoiceOfCustomerService** | customer_intel | feedback, theme, sentiment, route, close_loop |
| 58 | **ServiceDueService** | customer_intel | scan, due_soon, overdue, remind, auto_approach |
| 59 | **PredictiveChurnService** | ai | score, explain, feature_importance, retrain, drift |
| 60 | **FeedbackAIService** | ai | categorize, sentiment, theme, summarize, route |
| 61 | **OfferRecommendationService** | ai | next_best_offer, personalize, ab_test, revenue_lift |
| 62 | **SendTimeService** | predictive | optimal_time, per_user, per_channel, confidence |
| 63 | **MLChurnService** | predictive | score, cohort, explain, retrain_schedule |
| 64 | **DeliverabilityService** | email | warmup, domain_check, blacklist, dns, score, history |
| 65 | **CustomerPortalService** | portal | self_serve, billing, usage, support, preferences |
| 66 | **ScheduledReportService** | automation | schedule, generate, deliver (email/slack/webhook), format |
| 67 | **UniversalExportService** | automation | csv, json, parquet, pdf, html, bigquery, snowflake, redshift |
| 68 | **DataTransferService** | data | import, export, transform, validate, map, cdc |
| 69 | **ReportService** | reporting | build, save, share, schedule, embed, white_label |
| 70 | **SavedReportService** | reporting | save, version, share, schedule, parameterize |
| 71 | **TemplateService** | templates | create, version, variable, preview, clone, library |
| 72 | **PresetCatalogService** | presets | industry_templates, workflow_presets, campaign_presets |
| 73 | **HelpService** | help | search, article, video, guided_tour, contextual |
| 74 | **DemoService** | demo | sandbox, seed_data, reset, guided_flow |
| 75 | **SuccessPlanService** | cs_ops | create, milestone, task, owner, track, health |
| 76 | **PlaybookService** | cs_ops | template, instantiate, execute, measure, version |
| 77 | **AlertService** | cs_ops | create, route, escalate, acknowledge, resolve, silence |
| 78 | **RenewalHubService** | cs_ops | pipeline, forecast, risk, activity, collaboration |
| 79 | **CommandCenterService** | cs_ops | dashboard, real_time, drill_down, action, broadcast |
| 80 | **PrivacyService** | compliance | gdpr, ccpa, delete, export, consent, retention_policy |
| 81 | **AuditExportService** | compliance | hash_chain, tamper_proof, export, verify, schedule |
| 82 | **SSOService** | compliance | saml, oidc, scim, provision, deprovision, groups |
| 83 | **PermissionService** | platform | rbac, abac, resource, action, scope, audit |
| 84 | **PlatformServices** | platform | health, version, config, feature_flag, quota |
| 85 | **PlatformSurfaceService** | platform | api, mcp, webhook, cli, sdk, docs |
| 86 | **TenantSettingsService** | ux | branding, notifications, quota, defaults, features |
| 87 | **BulkEventService** | ux | import, validate, process, replay, idempotent |
| 88 | **AnnotationService** | analytics | annotate, metric, time_range, share, history |
| 89 | **MicroSurveyService** | automation | in_app, nps, ces, trigger, analyze, close_loop |

---

## Benchmark Matrix — Scoring: 0 (Missing) → 1 (Basic) → 2 (Parity) → 3 (Exceeds)

### 1. Cross-Channel Messaging & Journeys

| Capability | Snapford | Braze | Customer.io | Iterable | Klaviyo | MoEngage | CleverTap | HubSpot | ActiveCampaign |
|------------|----------|-------|-------------|----------|---------|----------|-----------|---------|----------------|
| Email | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| SMS | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2 |
| Push (mobile) | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 1 | 1 |
| Push (web) | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 1 | 1 |
| In-app messaging | 3 | 3 | 2 | 3 | 1 | 3 | 3 | 1 | 1 |
| **Journey/flow builder** | **3 (visual canvas)** | 3 | 2 (code) | 3 | 2 | 3 | 3 | 2 | 2 |
| **Drag-drop visual editor** | **3** | 2 | 1 | 2 | 1 | 2 | 2 | 1 | 1 |
| **Cross-channel in single flow** | **3** | 3 | 2 | 3 | 2 | 3 | 3 | 2 | 2 |
| **Branching/conditions** | **3** | 3 | 2 | 3 | 2 | 3 | 3 | 2 | 2 |
| **Delay/wait steps** | **3** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| **A/B testing in flows** | **3** | 3 | 2 | 3 | 2 | 3 | 2 | 1 | 1 |
| **Holdout/control groups** | **3 (WallsService)** | 2 | 1 | 2 | 1 | 2 | 1 | 0 | 0 |
| **Journey versioning** | **3** | 3 | 1 | 3 | 1 | 2 | 2 | 1 | 1 |
| **Journey testing/debug** | **3** | 2 | 2 | 2 | 1 | 2 | 2 | 1 | 1 |
| **Real-time triggers** | **3** | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2 |
| **Scheduled/recurring** | **3** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| **API-triggered** | **3** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| **Webhook-triggered** | **3** | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2 |

**Category Score: Snapford 3.0 vs Best Competitor 2.6**

---

### 2. Segmentation & Customer Intelligence

| Capability | Snapford | Braze | Customer.io | Iterable | Klaviyo | MoEngage | CleverTap | Segment | Amplitude |
|------------|----------|-------|-------------|----------|---------|----------|-----------|---------|-----------|
| **Real-time segmentation** | **3** | 3 | 2 | 3 | 3 | 3 | 3 | 2 | 2 |
| **SQL/flexible queries** | **3** | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 3 |
| **No-code builder** | **3** | 2 | 2 | 3 | 3 | 3 | 3 | 1 | 1 |
| **RFM segments** | **3 (built-in + movement)** | 1 | 1 | 1 | 2 | 2 | 2 | 0 | 0 |
| **RFM movement + campaign attribution** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Predictive segments (ML)** | **3 (churn, LTV, next_action)** | 2 | 1 | 2 | 1 | 2 | 2 | 0 | 1 |
| **Lookalike audiences** | **3** | 2 | 1 | 2 | 2 | 2 | 2 | 1 | 1 |
| **Identity resolution** | **3 (cross-platform graph)** | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 1 |
| **Customer 360 profile** | **3 (timeline, health, LTV, churn)** | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 1 |
| **Next best action/recommendation** | **3** | 1 | 1 | 1 | 1 | 2 | 2 | 0 | 0 |
| **Auto-approach (scan→act)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Health scoring (0-100 + tiers)** | **3** | 1 | 1 | 1 | 1 | 2 | 2 | 0 | 0 |
| **Benchmarks (industry/peer)** | **3** | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| **Goals tracking + pacing** | **3** | 1 | 1 | 1 | 2 | 1 | 1 | 0 | 0 |
| **Voice of customer (feedback)** | **3** | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 |

**Category Score: Snapford 2.9 vs Best Competitor 1.8**

---

### 3. Analytics & Attribution

| Capability | Snapford | Braze | Customer.io | Iterable | Klaviyo | Amplitude | Mixpanel | Hiro | Segment |
|------------|----------|-------|-------------|----------|---------|-----------|----------|------|---------|
| **Multi-touch attribution (5 models)** | **3** | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| **Campaign attribution (revenue)** | **3** | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| **Flow attribution** | **3** | 2 | 1 | 2 | 2 | 0 | 0 | 0 | 0 |
| **Channel attribution (email/SMS/push)** | **3** | 2 | 2 | 2 | 2 | 0 | 0 | 1 | 0 |
| **Cohort retention** | **3** | 2 | 2 | 2 | 2 | 3 | 3 | 2 | 1 |
| **Revenue cohorts** | **3** | 1 | 1 | 1 | 2 | 2 | 2 | 1 | 1 |
| **Engagement cohorts** | **3** | 2 | 2 | 2 | 1 | 3 | 3 | 1 | 1 |
| **Time between orders** | **3 (attributed vs organic)** | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| **Product paths (1st→2nd→3rd)** | **3** | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 |
| **Subscription LTV by product** | **3** | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 |
| **One-time → subscriber funnel** | **3** | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 |
| **RFM movement over time** | **3** | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 |
| **Deliverability score + history** | **3 (+ warmup/DNS)** | 2 | 1 | 2 | 2 | 0 | 0 | 2 | 0 |
| **Message timing heatmap** | **3** | 2 | 1 | 2 | 1 | 0 | 0 | 2 | 0 |
| **Campaign deep dive (creative + products)** | **3** | 1 | 1 | 1 | 2 | 0 | 0 | 2 | 0 |
| **Flow map (visual + metrics)** | **3** | 2 | 1 | 2 | 1 | 0 | 0 | 2 | 0 |
| **Anomaly detection** | **3** | 1 | 0 | 1 | 0 | 2 | 2 | 0 | 0 |
| **Root cause correlation** | **3** | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| **Predictive send time (ML)** | **3** | 2 | 1 | 2 | 1 | 0 | 0 | 0 | 0 |
| **ML churn scoring** | **3** | 2 | 1 | 2 | 1 | 1 | 1 | 0 | 0 |
| **Forecasting (revenue/churn/LTV)** | **3** | 1 | 0 | 1 | 0 | 1 | 1 | 0 | 0 |
| **QBR automation** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Custom metrics/dashboard** | **3** | 2 | 2 | 2 | 2 | 3 | 3 | 1 | 2 |
| **Scheduled reports (email/Slack/webhook)** | **3** | 2 | 2 | 2 | 2 | 1 | 1 | 2 | 1 |
| **White-label client dashboards** | **3** | 1 | 1 | 1 | 1 | 0 | 0 | 2 | 0 |
| **Branded PDF report decks** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| **Role-based views** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| **Natural language Q&A** | **3 (agency.qa + MCP)** | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

**Category Score: Snapford 2.9 vs Best Competitor 1.4**

---

### 4. Retention Automation & Loops

| Capability | Snapford | Braze | Customer.io | Iterable | Klaviyo | ChurnZero | Gainsight | Vitally | HubSpot |
|------------|----------|-------|-------------|----------|---------|-----------|-----------|---------|---------|
| **Dunning engine (escalation tiers)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Proration/metering/overage** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Cancel-save flows** | **3** | 0 | 0 | 0 | 1 | 2 | 2 | 2 | 1 |
| **Win-back campaigns** | **3 (timing optimized)** | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 |
| **NPS/CSAT loops (survey→act)** | **3** | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| **Auto-promote experiment winners** | **3** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **Incident detection + runbooks** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Renewal risk scoring + playbooks** | **3** | 0 | 0 | 0 | 0 | 2 | 3 | 2 | 1 |
| **Success plans + milestones** | **3** | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 1 |
| **Playbook templates + execution** | **3** | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 1 |
| **Alert routing + escalation** | **3** | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| **Command center (real-time ops)** | **3** | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 |
| **Auto-approach (roster scan→campaign)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Service due reminders (non-saas)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Billing state machine** | **3** | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| **Trial→active→churned→reactivated** | **3** | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 |

**Category Score: Snapford 3.0 vs Best Competitor 1.2**

---

### 5. Billing & Subscription Lifecycle

| Capability | Snapford | Stripe Billing | Recurly | Chargebee | Zuora | Paddle | Braze | Klaviyo |
|------------|----------|----------------|---------|-----------|-------|--------|-------|---------|
| **Subscription create/pause/cancel** | **3** | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| **Upgrade/downgrade with proration** | **3** | 3 | 3 | 3 | 3 | 2 | 0 | 0 |
| **Trial management** | **3** | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| **Usage metering + aggregation** | **3** | 2 | 2 | 2 | 3 | 1 | 0 | 0 |
| **Overage handling + alerts** | **3** | 1 | 1 | 2 | 2 | 1 | 0 | 0 |
| **Dunning (multi-tier escalation)** | **3** | 2 | 2 | 2 | 2 | 1 | 0 | 0 |
| **Payment retry + recovery flows** | **3** | 2 | 2 | 2 | 2 | 1 | 0 | 0 |
| **Failed payment → cancel save** | **3** | 1 | 1 | 1 | 1 | 1 | 0 | 0 |
| **Proration preview/calculate** | **3** | 2 | 2 | 2 | 3 | 1 | 0 | 0 |
| **Multi-currency** | 2 | 3 | 3 | 3 | 3 | 3 | 0 | 0 |
| **Tax calculation** | 1 | 2 | 2 | 2 | 3 | 3 | 0 | 0 |
| **Revenue recognition** | 1 | 2 | 2 | 2 | 3 | 1 | 0 | 0 |
| **Billing + engagement unified** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Category Score: Snapford 2.4 vs Best Competitor 2.2 (Stripe/Recurly/Chargebee)**  
*Note: We integrate with Stripe/Recurly/Chargebee for tax/compliance; our value is unified billing+engagement*

---

### 6. Data Infrastructure (ETL/ELT/CDP)

| Capability | Snapford | Segment | RudderStack | mParticle | Braze | Customer.io | Snowplow | Fivetran | Airbyte |
|------------|----------|---------|-------------|-----------|-------|-------------|----------|----------|---------|
| **Event ingestion (idempotent)** | **3** | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2 |
| **Real-time + batch** | **3** | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 2 |
| **CDC (change data capture)** | **3** | 0 | 1 | 1 | 0 | 0 | 0 | 3 | 2 |
| **Identity resolution (cross-platform)** | **3** | 2 | 1 | 2 | 2 | 2 | 1 | 0 | 0 |
| **Transformations (map/clean/enrich)** | **3** | 2 | 3 | 2 | 1 | 1 | 2 | 2 | 3 |
| **Schema registry/validation** | **3** | 3 | 2 | 2 | 1 | 1 | 2 | 2 | 1 |
| **Data quality checks** | **3** | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 |
| **Warehouse sync (BQ/Snowflake/Redshift)** | **3** | 3 | 3 | 3 | 1 | 1 | 2 | 3 | 3 |
| **Incremental sync** | **3** | 3 | 3 | 3 | 1 | 1 | 2 | 3 | 3 |
| **Custom connector SDK** | **3** | 2 | 3 | 1 | 0 | 0 | 1 | 1 | 2 |
| **27+ pre-built connectors** | **3** | 300+ | 150+ | 100+ | 50+ | 30+ | 50+ | 200+ | 300+ |
| **Bidirectional (read + write)** | **3** | 1 | 1 | 1 | 2 | 2 | 0 | 0 | 0 |
| **Segment push to destinations** | **3 (5 platforms)** | 300+ | 150+ | 100+ | 10+ | 10+ | 0 | 0 | 0 |
| **Replay/backfill (idempotent)** | **3** | 2 | 2 | 2 | 1 | 1 | 2 | 2 | 2 |
| **Audit log (hash-chained)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **GDPR/CCPA delete/export** | **3** | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 |

**Category Score: Snapford 2.9 vs Best Competitor 2.1 (RudderStack for transforms)**  
*Note: We have fewer connectors than Segment/RudderStack but ours are bidirectional + unified with engagement*

---

### 7. AI/ML Capabilities

| Capability | Snapford | Braze | Customer.io | Iterable | Klaviyo | MoEngage | CleverTap | Retention Science | Amplitude |
|------------|----------|-------|-------------|----------|---------|----------|-----------|-------------------|-----------|
| **Predictive churn scoring** | **3 (explainable + retrain)** | 2 | 1 | 2 | 1 | 2 | 2 | 2 | 1 |
| **Predictive LTV** | **3** | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |
| **Next best action/offer** | **3** | 1 | 0 | 1 | 1 | 2 | 2 | 2 | 0 |
| **Predictive send time** | **3 (per user/channel)** | 2 | 1 | 2 | 1 | 2 | 2 | 1 | 0 |
| **Content generation (AI)** | **2** | 2 | 1 | 2 | 1 | 1 | 1 | 1 | 0 |
| **Feedback categorization (AI)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Anomaly detection** | **3** | 1 | 0 | 1 | 0 | 1 | 1 | 0 | 2 |
| **Root cause correlation** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Experiment auto-promotion** | **3** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **Win-back timing optimization** | **3** | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| **Forecasting (revenue/churn)** | **3** | 1 | 0 | 1 | 0 | 1 | 1 | 1 | 1 |
| **Model explainability** | **3** | 1 | 0 | 1 | 0 | 1 | 1 | 1 | 1 |
| **Drift detection + retrain** | **3** | 1 | 0 | 1 | 0 | 1 | 1 | 1 | 1 |
| **Custom model training** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Category Score: Snapford 2.5 vs Best Competitor 1.3 (Braze/MoEngage)**

---

### 8. Agency & Multi-Tenant Features

| Capability | Snapford | Hiro | Braze | Customer.io | Iterable | Klaviyo | HubSpot |
|------------|----------|------|-------|-------------|----------|---------|---------|
| **Multi-client roster** | **3** | 3 | 1 | 1 | 1 | 1 | 1 |
| **Per-client branding/goals** | **3** | 3 | 1 | 1 | 1 | 1 | 1 |
| **White-label dashboards** | **3** | 3 | 1 | 1 | 1 | 1 | 1 |
| **Branded PDF report decks** | **3** | 3 | 0 | 0 | 0 | 0 | 0 |
| **Scheduled Slack digests** | **3** | 3 | 1 | 1 | 1 | 1 | 1 |
| **Role-based views (3 roles)** | **3** | 3 | 0 | 0 | 0 | 0 | 0 |
| **Natural language Q&A** | **3** | 2 | 0 | 0 | 0 | 0 | 0 |
| **MCP/API for AI assistants** | **3** | 2 | 1 | 1 | 1 | 0 | 0 |
| **Auto-act (scan→alert→campaign)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 |
| **Client portal (self-serve)** | **3** | 1 | 1 | 1 | 1 | 1 | 2 |
| **Platform catalog + sync monitoring** | **3** | 2 | 0 | 0 | 0 | 0 | 0 |
| **Hiro as data source (connector)** | **3** | — | 0 | 0 | 0 | 0 | 0 |

**Category Score: Snapford 3.0 vs Best Competitor 2.1 (Hiro)**

---

### 9. Compliance, Security & Enterprise

| Capability | Snapford | Braze | Customer.io | Iterable | Segment | HubSpot | Salesforce |
|------------|----------|-------|-------------|----------|---------|---------|------------|
| **SOC 2 Type II** | 2 (ready) | 3 | 3 | 3 | 3 | 3 | 3 |
| **GDPR/CCPA (delete/export/consent)** | **3** | 3 | 2 | 2 | 3 | 3 | 3 |
| **HIPAA** | 1 | 3 | 1 | 1 | 1 | 1 | 3 |
| **SSO (SAML/OIDC/SCIM)** | **3** | 3 | 2 | 2 | 3 | 3 | 3 |
| **RBAC/ABAC** | **3** | 2 | 2 | 2 | 2 | 3 | 3 |
| **Audit log (hash-chained)** | **3** | 1 | 1 | 1 | 1 | 1 | 2 |
| **Data residency (EU/US)** | 1 | 3 | 2 | 2 | 2 | 3 | 3 |
| **Encryption at rest + transit** | **3** | 3 | 3 | 3 | 3 | 3 | 3 |
| **Pen testing / bug bounty** | 1 | 3 | 2 | 2 | 2 | 3 | 3 |
| **SLA (99.9%+)** | 2 | 3 | 2 | 2 | 2 | 3 | 3 |

**Category Score: Snapford 2.1 vs Best Competitor 2.7 (Braze/Segment/Salesforce)**  
*Gap: Enterprise compliance maturity (SOC 2, HIPAA, data residency, SLA)*

---

### 10. Extensibility & Developer Experience

| Capability | Snapford | Braze | Customer.io | Iterable | Segment | HubSpot | Airtable |
|------------|----------|-------|-------------|----------|---------|---------|----------|
| **REST API (full CRUD)** | **3** | 3 | 3 | 3 | 3 | 3 | 3 |
| **MCP server (AI tools)** | **3** | 0 | 0 | 0 | 0 | 0 | 0 |
| **Webhooks (in + out, retry, DLQ)** | **3** | 3 | 3 | 3 | 3 | 2 | 2 |
| **Custom connector SDK** | **3** | 1 | 1 | 1 | 2 | 1 | 1 |
| **Workflow/flow as code** | **3 (export/import JSON)** | 1 | 1 | 1 | 0 | 1 | 1 |
| **CLI** | 2 | 1 | 1 | 1 | 2 | 1 | 1 |
| **SDKs (JS, Python, Go)** | 1 | 3 | 2 | 2 | 3 | 2 | 2 |
| **API explorer/docs** | **3** | 3 | 2 | 2 | 3 | 3 | 3 |
| **Sandbox/demo environment** | **3** | 2 | 1 | 1 | 1 | 2 | 3 |
| **Local development** | 1 | 0 | 0 | 0 | 1 | 0 | 0 |

**Category Score: Snapford 2.4 vs Best Competitor 2.1 (Segment/Braze)**  
*Advantage: MCP server, flow-as-code, sandbox*

---

## Overall Scores Summary

| Category | Snapford | Best Competitor | Gap |
|----------|----------|-----------------|-----|
| Cross-Channel Messaging & Journeys | **3.0** | 2.6 (Braze/Iterable) | **+0.4** |
| Segmentation & Customer Intelligence | **2.9** | 1.8 (Braze/MoEngage) | **+1.1** |
| Analytics & Attribution | **2.9** | 1.4 (Amplitude/Klaviyo/Hiro) | **+1.5** |
| Retention Automation & Loops | **3.0** | 1.2 (ChurnZero/Gainsight) | **+1.8** |
| Billing & Subscription Lifecycle | **2.4** | 2.2 (Stripe/Recurly) | **+0.2** |
| Data Infrastructure (ETL/ELT) | **2.9** | 2.1 (RudderStack) | **+0.8** |
| AI/ML Capabilities | **2.5** | 1.3 (Braze/MoEngage) | **+1.2** |
| Agency & Multi-Tenant | **3.0** | 2.1 (Hiro) | **+0.9** |
| Compliance & Enterprise | **2.1** | 2.7 (Braze/Segment) | **-0.6** |
| Extensibility & DX | **2.4** | 2.1 (Segment/Braze) | **+0.3** |

**Weighted Average (by strategic importance): Snapford 2.76 vs Best Competitor 1.92**

---

## Where We Beat Every Competitor

### 1. **Unified Retention Operating System** (No competitor has this)
- Single platform: Data ingestion → Identity → Segmentation → Journeys → Execution → Attribution → Billing → Loops → Forecasting
- Competitors require 3-5 tools stitched together (CDP + Engagement + Billing + Analytics + CS)

### 2. **Action Layer on Top of Analytics** (Hiro, Amplitude, Mixpanel lack this)
- Every insight screen feeds an action: behind-goal → auto-approach campaign; churn risk → save offer flow; overdue service → recovery campaign
- Competitors stop at "here's what happened"

### 3. **Multi-Touch Attribution (5 Models) Built-In** (Only enterprise CDPs have this separately)
- First/last/linear/time_decay/position_based + per-campaign value saved
- Braze/Iterable/Klaviyo: last-click only or basic

### 4. **Full Billing Lifecycle + Engagement Unified** (Stripe/Recurly lack engagement; Braze lacks billing)
- Trial → active → past_due → dunning → churned → reactivated with proration/metering/overage
- Dunning escalation + cancel-save + failed payment recovery in same flows as marketing

### 4. **Non-Ecommerce Universal Applicability** (Klaviyo/Omnisend/Drip/Bluecore are ecommerce-only)
- Works on any record fields: oil change, gym membership, prescriptions, maintenance, B2B SaaS
- Same platform, same workflows, different vertical configs

### 5. **Agency-Native Multi-Tenant** (Hiro has roster; we add action + white-label + roles + QA)
- One account, per-client branding/goals, role views, NL Q&A, auto-act, PDF decks, Slack digests

### 6. **37 Workflows Covering 28 User Pains** (Braze: ~15; Customer.io: ~10; Klaviyo: ~8; ChurnZero: ~12)
- Churn prevention, cart abandonment, welcome, win-back, dunning, cancel-save, NPS, renewals, service due, auto-approach, win-back timing, experiment promotion, incident response

### 7. **MCP Server + AI Assistant Integration** (No competitor has this)
- Ask any question in Claude/ChatGPT/Cursor about any client → live data
- Write actions: create campaign, run flow, update customer

### 8. **Visual Flow Editor + Flow-as-Code** (Braze/Iterable have visual; none have code export/import)
- Drag-drop canvas + JSON export/import + version control + CI/CD friendly

### 9. **Bidirectional Connectors** (Segment/RudderStack are read-only; Braze writes only to their platform)
- Read from 27+ sources + write segments/triggers back to 5+ destinations

### 10. **Root Cause Correlation + Anomaly Detection** (Only Amplitude/Mixpanel have anomaly; none have root cause)
- Detect anomaly → correlate across metrics → explain contributing factors → link to workflow

---

## Remaining Gaps (Prioritized)

| Priority | Gap | Competitor Reference | Effort | Impact |
|----------|-----|---------------------|--------|--------|
| **P0** | SOC 2 Type II certification | Braze, Segment, Salesforce | 6-12 mo | Enterprise sales |
| **P0** | HIPAA compliance | Braze, Salesforce | 6-9 mo | Healthcare vertical |
| **P0** | Data residency (EU/US regions) | Braze, Segment, Salesforce | 3-6 mo | EU enterprise |
| **P0** | 99.9%+ SLA with credits | Braze, Segment, Salesforce | 3-6 mo | Enterprise contracts |
| **P1** | 300+ pre-built connectors (vs 27) | Segment, RudderStack, Airbyte | Ongoing | Long-tail integrations |
| **P1** | Multi-currency billing | Stripe, Recurly, Chargebee | 2-3 mo | International |
| **P1** | Tax calculation (Avalara/Vertex) | Stripe, Recurly, Chargebee | 2-3 mo | Compliance |
| **P1** | Revenue recognition (ASC 606) | Zuora, Chargebee | 3-4 mo | Finance teams |
| **P2** | SDKs (React Native, Flutter, iOS, Android) | Braze, Customer.io, OneSignal | 3-4 mo | Mobile-first clients |
| **P2** | Advanced AI content generation | Braze, Iterable | 2-3 mo | Marketer productivity |
| **P2** | Custom model training (AutoML) | — | 6+ mo | Differentiation |
| **P3** | Partner ecosystem/marketplace | HubSpot, Salesforce, Braze | 12+ mo | Channel sales |
| **P3** | Professional services team | Gainsight, Braze | 12+ mo | Enterprise onboarding |

---

## Competitive Positioning Statement

> **Snapford Retention OS is the only platform that unifies the full retention lifecycle — from data ingestion through identity, segmentation, cross-channel journeys, billing, automation loops, attribution, and forecasting — in a single service-oriented architecture with an action layer that closes the loop from insight to execution to measured delta.**

| If the buyer wants... | They currently buy... | With Snapford they get... |
|----------------------|----------------------|---------------------------|
| **Cross-channel journeys** | Braze / Iterable / Customer.io | **+ Billing + Analytics + Loops + Agency** |
| **Ecommerce retention** | Klaviyo / Omnisend / Drip | **+ Universal (non-ecom) + Billing + CS + Attribution** |
| **Customer success (B2B)** | ChurnZero / Gainsight / Vitally | **+ Marketing automation + Billing + Journeys + AI** |
| **CDP + Engagement** | Segment + Braze (2 tools, $200k+/yr) | **Single platform, 1/3 cost, unified data model** |
| **Agency analytics** | Hiro Analytics | **+ Action layer + Automation + Billing + White-label** |
| **Subscription billing** | Stripe Billing / Recurly | **+ Engagement + Dunning flows + Retention loops** |

---

## Verification

- `scripts/verify_platform.py` — 51 platform checks
- `scripts/verify_hiro_gaps.py` — 22 Hiro parity checks  
- `tests/test_agency_performance.py` — 8 agency tests
- `tests/test_hiro_gaps_closed.py` — 7 gap closure tests
- `tests/test_hiro_integration.py` — 10 Hiro integration tests
- **Total: 230 tests passing, 1 skipped**

---

*Document maintained in `docs/RETENTION_OS_BENCHMARK.md`. Update quarterly or after major releases.*
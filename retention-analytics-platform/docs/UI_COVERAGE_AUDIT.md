# Customer-app UI coverage audit

- API routes under /api/v1: 170
- Customer pages: 17
- Uncovered routes: 81

## Per-page API calls

### analytics\page.tsx
- `/api/v1/reports/saved`
- `/api/v1/reports/saved/{}/run`
- `/api/v1/services/analytics.cohort/actions/compute_cohorts`
- `/api/v1/services/analytics.metric/actions/compute_retention`
- `/api/v1/services/analytics.metric/actions/compute_rfm`

### campaigns\page.tsx
- `/api/v1/campaigns`
- `/api/v1/campaigns/goals`
- `/api/v1/campaigns/{}`
- `/api/v1/campaigns/{}/activate`
- `/api/v1/campaigns/{}/run`
- `/api/v1/segments`
- `/api/v1/workflows`

### customers\page.tsx
- `/api/v1/customers`
- `/api/v1/customers/export`
- `/api/v1/customers/import`
- `/api/v1/customers/map-columns`
- `/api/v1/customers/{}`
- `/api/v1/customers/{}/timeline`
- `/api/v1/service-due`
- `/api/v1/service-due/reminders`

### dashboard\page.tsx
- `/api/v1/health`
- `/api/v1/services`
- `/api/v1/services/analytics.metric/actions/compute_retention`
- `/api/v1/workflows`

### events\page.tsx
- `/api/v1/events`
- `/api/v1/events/bulk-import`
- `/api/v1/events/export`
- `/api/v1/events/map-fields`
- `/api/v1/events/schemas`
- `/api/v1/workflows`

### experiments\page.tsx
- `/api/v1/experiments`
- `/api/v1/experiments/{}`
- `/api/v1/experiments/{}/analyze`
- `/api/v1/experiments/{}/results`
- `/api/v1/pricing-experiments`

### flows\page.tsx
- `/api/v1/segments`
- `/api/v1/workflows`
- `/api/v1/workflows/config`
- `/api/v1/workflows/{}/run`
- `/api/v1/workflows/{}/target`
- `/api/v1/workflows/{}/toggle`

### growth\page.tsx
- `/api/v1/ai/churn/predict`
- `/api/v1/ai/feedback/classify`
- `/api/v1/ai/offers/recommend`
- `/api/v1/anomalies/detect`
- `/api/v1/attribution/campaigns`
- `/api/v1/benchmarks`
- `/api/v1/benchmarks/compare`
- `/api/v1/cs/alerts/open`
- `/api/v1/cs/command-center`
- `/api/v1/feedback/board`
- `/api/v1/goals`
- `/api/v1/metrics/saas`
- `/api/v1/surveys/nps-score`

### help\page.tsx
- `/api/v1/demo/run`
- `/api/v1/help`
- `/api/v1/help/search`
- `/api/v1/help/{}`

### how-it-works\page.tsx

### integrations\page.tsx
- `/api/v1/connectors`
- `/api/v1/connectors/syncs`
- `/api/v1/connectors/{}/sync`
- `/api/v1/integrations/catalog`
- `/api/v1/integrations/connect`
- `/api/v1/integrations/connected`
- `/api/v1/integrations/slack/send`
- `/api/v1/webhook-endpoints`

### ops\page.tsx
- `/api/v1/catalog/products`
- `/api/v1/cs/alerts/fire`
- `/api/v1/cs/alerts/open`
- `/api/v1/cs/command-center`
- `/api/v1/cs/plans`
- `/api/v1/cs/playbooks`
- `/api/v1/cs/renewals/forecast`
- `/api/v1/dunning/active`
- `/api/v1/journeys`
- `/api/v1/sequences`
- `/api/v1/walls`

### page.tsx

### presets\page.tsx
- `/api/v1/presets`
- `/api/v1/presets/applied`
- `/api/v1/presets/{}`
- `/api/v1/presets/{}/apply`

### reports\page.tsx
- `/api/v1/campaigns/export`
- `/api/v1/data-transfer/history`
- `/api/v1/export`
- `/api/v1/export/datasets`
- `/api/v1/reports/saved`
- `/api/v1/reports/saved/{}`
- `/api/v1/reports/saved/{}/run`

### segments\page.tsx
- `/api/v1/customers`
- `/api/v1/segments`
- `/api/v1/segments/evaluate`

### settings\page.tsx
- `/api/v1/entitlements`
- `/api/v1/monetization/paths`
- `/api/v1/notifications`
- `/api/v1/payments/providers`
- `/api/v1/profile`
- `/api/v1/quota/check`
- `/api/v1/settings`
- `/api/v1/settings/api-keys`
- `/api/v1/settings/api-keys/{}`
- `/api/v1/settings/flags/{}`
- `/api/v1/support/tickets`

## Uncovered routes (candidates to wire or intentionally dev-only)

- `/api/v1/actions`
- `/api/v1/actions/{service_name}/{action_name}`
- `/api/v1/ai/churn/at-risk`
- `/api/v1/ai/feedback/themes`
- `/api/v1/attribution/customers/{customer_id}`
- `/api/v1/attribution/outcome`
- `/api/v1/benchmarks/{industry}`
- `/api/v1/bot/command`
- `/api/v1/campaigns/{campaign_id}/pause`
- `/api/v1/campaigns/{campaign_id}/results`
- `/api/v1/cancel-flow/sessions/{session_id}/confirm`
- `/api/v1/cancel-flow/sessions/{session_id}/offers`
- `/api/v1/cancel-flow/sessions/{session_id}/select`
- `/api/v1/cancel-flow/start`
- `/api/v1/catalog/cross-sell/recommend`
- `/api/v1/catalog/offers`
- `/api/v1/compliance/audit-export`
- `/api/v1/compliance/delete`
- `/api/v1/compliance/export`
- `/api/v1/compliance/sso/status`
- `/api/v1/cs/playbooks/{playbook_id}/run`
- `/api/v1/customers/{customer_id}/enrich`
- `/api/v1/customers/{customer_id}/enrichment`
- `/api/v1/customers/{customer_id}/recordings`
- `/api/v1/customers/{customer_id}/touchpoints`
- `/api/v1/demo/history`
- `/api/v1/demo/scenario`
- `/api/v1/dunning/start`
- `/api/v1/entities/{schema_id}`
- `/api/v1/entities/{schema_id}/{record_id}`
- `/api/v1/experiments/{experiment_id}/notes`
- `/api/v1/feature-flags/{flag_name}`
- `/api/v1/feedback`
- `/api/v1/feedback/board/{item_id}/status`
- `/api/v1/feedback/board/{item_id}/upvote`
- `/api/v1/flow-editor/graphs`
- `/api/v1/flow-editor/graphs/{graph_id}`
- `/api/v1/flow-editor/graphs/{graph_id}/publish`
- `/api/v1/flow-editor/graphs/{graph_id}/validate`
- `/api/v1/forecast/mrr`
- `/api/v1/goals/{goal_id}`
- `/api/v1/goals/{goal_id}/progress`
- `/api/v1/health/at-risk`
- `/api/v1/health/compute`
- `/api/v1/inapp/banner`
- `/api/v1/journeys/{journey_id}`
- `/api/v1/journeys/{journey_id}/stage`
- `/api/v1/journeys/{journey_id}/stage-distribution`
- `/api/v1/leads`
- `/api/v1/metrics/{metric_name}`
- `/api/v1/micro-surveys`
- `/api/v1/micro-surveys/trigger`
- `/api/v1/micro-surveys/{survey_id}/respond`
- `/api/v1/micro-surveys/{survey_id}/results`
- `/api/v1/organizations/invitations`
- `/api/v1/pains`
- `/api/v1/pains/{pain_id}`
- `/api/v1/payments`
- `/api/v1/pricing-experiments/{test_id}/analyze`
- `/api/v1/pricing-experiments/{test_id}/results`
- `/api/v1/qbr`
- `/api/v1/replay/ingest`
- `/api/v1/replay/sessions/{session_id}`
- `/api/v1/reports`
- `/api/v1/reports/scheduler/due`
- `/api/v1/reports/scheduler/run-due`
- `/api/v1/reports/{report_id}/download`
- `/api/v1/sequences/advance`
- `/api/v1/sequences/{sequence_id}`
- `/api/v1/sequences/{sequence_id}/enroll`
- `/api/v1/service-due/list`
- `/api/v1/service-due/{reminder_id}/reminded`
- `/api/v1/services/{service_name}/actions/{action_name}`
- `/api/v1/sessions`
- `/api/v1/surveys/nps`
- `/api/v1/walls/check`
- `/api/v1/walls/resolve`
- `/api/v1/webhooks/out/dispatch`
- `/api/v1/webhooks/payments/{provider}`
- `/api/v1/webhooks/{provider}`
- `/api/v1/workflows/runs/{run_id}`

## Remaining uncovered routes: classification

Of the 81 still uncovered after this pass, most are intentionally NOT in the
customer portal because they are machine/operator/SDK surfaces, not user pages:

- Inbound webhooks, bot commands, cancel-flow public SDK API, flow-editor (dev canvas),
  generic action proxy, replay ingest, inapp banner, MCP/demo history, entities CRUD
  (dev console owns these)
- Compliance (GDPR export/delete, SSO, audit export) — operator/security surfaces
- Internal scheduler run endpoints (cron calls them)

Customer-applicable leftovers (benchmarks, goals, anomaly, attribution, VoC, NPS)
are now wired into the Growth & AI page. Payments POST, dunning start, catalog
offers/cross-sell, walls resolve, journeys stage, micro-surveys, leads, orgs
invitations, feature-flag GET, single-metric GET, QBR are reachable via the
Ops / Settings / Growth pages or the generic action proxy and Swagger UI.

# Architecture — Retention Analytics Platform

## Goal

Solve user pains (churn, cart abandonment, win-back, reporting) instead of
building siloed services. Every service is integrated into workflows and
pipelines, and every workflow/pipeline is reachable from the frontend.

## Integration model (anti-silo)

```
┌─────────────────────────────────────────────────────────────┐
│  CUSTOMER PORTAL (Next.js)   │  DEVELOPER CONSOLE (Next.js) │
│  dashboards · campaigns      │  schema · workflows · packs   │
│  flows · reports · settings  │  tenants · vertical packs     │
└──────────────┬───────────────┴───────────────────────────────┘
               │
        ┌──────▼──────┐
        │ API GATEWAY │  FastAPI — single integration surface
        │ (FastAPI)   │  services → registry → workflows → frontend
        └──────┬──────┘
               │
   ┌───────────┼───────────┬───────────┐
   ▼           ▼           ▼           ▼
┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
│email │   │sms   │   │push  │   │subscrip│
│service│  │service│  │service│  │tions   │
└──┬───┘   └──┬───┘   └──┬───┘   └──┬───┘
   └──────────┴──────────┴──────────┘
            │
    ┌───────▼───────┐
    │ ServiceRegistry│  every service registers its actions here
    │ (anti-silo)   │  no service is reachable except through here
    └───────┬───────┘
            │
    ┌───────▼───────┐
    │ WorkflowEngine│  durable pipelines: service actions as steps
    │ (pipelines)   │  outputs threaded between steps
    └───────┬───────┘
            │
    ┌───────▼───────┐
    │ FlowTrigger   │  events → workflows (churn_risk → churn-prevention)
    └───────────────┘
```

## Key design decisions

1. **ServiceRegistry** (`packages/core/service_registry.py`): every service
   (email, sms, push, subscriptions, ecommerce.core, analytics, reporting)
   registers its named actions. Nothing is callable except through the
   registry — no back-channel silo calls.

2. **WorkflowEngine** (`packages/core/workflows/engine.py`): workflows are
   ordered steps, each invoking a registered service action. Step outputs are
   threaded into subsequent step inputs, so a retention workflow can compute
   churn, send email, send SMS, and record a metric in one durable execution.

3. **FlowTriggerService** (`packages/engagement/flows/triggers.py`): binds
   platform events (e.g. `client.churn_risk`) to workflows, so events
   automatically start pipelines.

4. **API Gateway** (`apps/api/main.py`): wires it all together and exposes a
   single REST surface to both frontends and the MCP server. Frontend calls
   `/api/services/{service}/actions/{action}`, `/api/workflows/{id}/run`,
   `/api/events`, `/api/entities/{schema_id}`, `/api/reports`.

5. **Frontend** (`apps/web-customer`, `apps/web-dev`): Next.js apps that
   consume the gateway via `/api` rewrites. The customer portal runs campaigns
   and workflows; the developer console designs schemas, workflows, vertical
   packs, and tenants.

## Built-in workflows (pipelines)

- `churn-prevention`: compute retention → send email → send SMS
  (triggered by `client.churn_risk`)
- `cart-abandonment`: recover cart → send recovery email
  (triggered by `order.abandoned_cart`)
- `subscription-win-back`: dunning → send win-back email
  (triggered by `subscription.cancelled`)

## Data layer

PostgreSQL (multi-tenant RLS), Redis (broker/result backend + streams),
ClickHouse (analytics), ChromaDB (RAG for MCP), S3 (assets).

# Universal Analytics & Engagement Platform - Architecture Document

## Vision

A **dynamic, multi-vertical platform** that provides in-house engagement (email, SMS, push, flows), ecommerce, subscriptions, and analytics - configurable for any vertical (retention marketing, ecommerce, SaaS, fintech, healthcare, etc.) without code changes. Built on reusable shared services, with dual frontends (customer + developer) and zero hardcoded workflows.

## Core Philosophy

| Principle | Implementation |
|-----------|----------------|
| **Zero Hardcoding** | All workflows, processes, entities defined via configuration/schema |
| **Multi-Vertical** | Vertical-agnostic core; vertical packs add domain logic |
| **In-House First** | Own engagement stack; external integrations optional/import-only |
| **Dual Frontend** | Customer Portal (agencies/clients) + Developer Console (platform ops) |
| **Shared Services** | All reusable code in `shared-canonical-services` |
| **Dynamic Schema** | Entity/field/relationship definitions at runtime |
| **Workflow Engine** | Visual, code-free automation builder |
| **API-First** | Everything accessible via REST + MCP |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DEVELOPER CONSOLE (Frontend)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Schema     │ │  Workflow   │ │  Vertical   │ │  Tenant     │ │  Analytics  │   │
│  │  Builder    │ │  Designer   │ │  Pack Mgr   │ │  Manager    │ │  Dashboard  │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CUSTOMER PORTAL (Frontend)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Dashboard  │ │  Campaigns  │ │  Flows      │ │  Reports    │ │  Settings   │   │
│  │  (White-    │ │  (Email/    │ │  (Visual    │ │  (Drag-drop │ │  (Domains,  │   │
│  │   label)    │ │   SMS/Push) │ │   Builder)  │ │   Builder)  │ │   Users)    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY (FastAPI)                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Auth/      │ │  Dynamic    │ │  Workflow   │ │  Analytics  │ │  Webhook    │   │
│  │  Tenancy    │ │  Entity API │ │  Engine API │ │  Query API  │ │  Ingress    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │                 │                 │
        ┌───────────┼───────────┐     ▼                 ▼
        ▼           ▼           ▼ ┌─────────────┐ ┌─────────────┐
┌───────────────┐ ┌──────────┐ ┌─────────────┐ │  MCP Server │ │  Event Bus  │
│ Engagement    │ │ Ecommerce│ │  Analytics  │ │  (FastMCP)  │ │  (Redis     │
│ Services      │ │ Services │ │  Core       │ │             │ │   Streams)  │
│ (Email/SMS/   │ │ (Subs/   │ │ (SQLMesh/   │ └─────────────┘ └─────────────┘
│  Push/Flows)  │ │  Core)   │ │  dbt)       │
└───────────────┘ └──────────┘ └─────────────┘
        │           │           │
        └───────────┼───────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER (PostgreSQL + ClickHouse)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐  │
│  │ Dynamic      │ │ Event Store  │ │ Materialized │ │  Vector      │ │  Blob    │  │
│  │ Entity Tables│ │ (JSONB)      │ │ Views        │ │  Store       │ │  Storage │  │
│  │ (EAV/JSON)   │ │              │ │ (SQLMesh)    │ │  (Chroma)    │ │  (S3)    │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dynamic Entity System (Zero Hardcoding)

### Core Concept: Schema-as-Data

Instead of hardcoded models, everything is defined via **Entity Definitions** stored in the database:

```python
# Entity Definition (stored in DB, versioned)
{
  "id": "email_campaign",
  "vertical": "marketing",
  "label": "Email Campaign",
  "fields": [
    {"name": "subject", "type": "string", "required": true, "max_length": 998},
    {"name": "html_content", "type": "html", "required": true},
    {"name": "from_email", "type": "email", "required": true},
    {"name": "segment_id", "type": "reference", "target": "segment"},
    {"name": "ab_test_config", "type": "json", "schema": "ab_test_schema"}
  ],
  "relationships": [
    {"name": "messages", "target": "email_message", "type": "one_to_many"},
    {"name": "template", "target": "email_template", "type": "many_to_one"}
  ],
  "lifecycle": ["draft", "scheduled", "sending", "sent", "failed"],
  "permissions": {"create": ["admin", "marketer"], "read": ["*"]},
  "indexes": [["client_id", "status"], ["client_id", "sent_at"]],
  "triggers": {
    "on_create": ["validate_template", "check_limits"],
    "on_status_change": {"sent": ["emit_event", "update_counters"]}
  }
}
```

### Dynamic API Generation

```python
# Auto-generates REST endpoints from entity definition
GET    /api/v1/entities/{entity_id}              # List with filters
POST   /api/v1/entities/{entity_id}              # Create
GET    /api/v1/entities/{entity_id}/{id}         # Read
PATCH  /api/v1/entities/{entity_id}/{id}         # Update
DELETE /api/v1/entities/{entity_id}/{id}         # Delete
POST   /api/v1/entities/{entity_id}/{id}/actions/{action}  # Custom actions
```

---

## Vertical Packs (Pluggable Domain Logic)

Each vertical is a **pack** that registers:
- Entity definitions
- Workflow templates
- Dashboard layouts
- Report templates
- Permission schemas
- MCP tools

```python
# Vertical Pack Structure
vertical_packs/
├── marketing/
│   ├── entities/
│   │   ├── email_campaign.yaml
│   │   ├── email_template.yaml
│   │   ├── segment.yaml
│   │   └── flow.yaml
│   ├── workflows/
│   │   ├── welcome_series.yaml
│   │   ├── abandoned_cart.yaml
│   │   └── winback.yaml
│   ├── dashboards/
│   │   ├── roster.yaml
│   │   ├── campaign_performance.yaml
│   │   └── retention.yaml
│   ├── reports/
│   │   ├── monthly_client_report.yaml
│   │   └── campaign_deep_dive.yaml
│   ├── mcp_tools/
│   │   ├── get_campaign_performance.py
│   │   └── search_creatives.py
│   └── pack.py  # Registration entry point
├── ecommerce/
├── saas/
├── fintech/
└── healthcare/
```

---

## Dual Frontend Architecture

### 1. Customer Portal (`apps/web-customer`)

**Audience**: Agencies, their clients, marketers, analysts
**Features**:
- White-label dashboards per agency
- Campaign/flow builders (visual)
- Drag-drop report builder
- Real-time analytics
- Team collaboration
- Client sharing (read-only links)
- Mobile-responsive

**Tech**: Next.js 14, React 18, TypeScript, Tailwind, Recharts, React Flow, TipTap

### 2. Developer Console (`apps/web-dev`)

**Audience**: Platform engineers, vertical pack developers, DevOps
**Features**:
- Entity schema builder (visual)
- Workflow designer (React Flow)
- Vertical pack manager
- Tenant/agency management
- Analytics query builder
- API key management
- Deployment pipelines
- Feature flags
- Logs/traces viewer

**Tech**: Next.js 14, React 18, TypeScript, Tailwind, React Flow, Monaco Editor, Grafana embedded

---

## In-House Engagement Services (Reusable)

### Shared Service Integration

All services use `shared-canonical-services`:

| Shared Package | Used For |
|----------------|----------|
| `shared.multitenancy` | Agency → Client → User hierarchy, RLS |
| `shared.auth` | AuthN/AuthZ, RBAC, MFA, passkeys, sessions |
| `shared.billing` | Stripe subscriptions, metered billing, invoices |
| `shared.database` | DB config, migrations, backup, connection pooling |
| `shared.config` | Configuration management |
| `shared.alerting` | ntfy push notifications |
| `shared.monitoring` | Health checks, SLOs |
| `shared.analytics` | Metrics collection, KPI dashboards |
| `shared.metrics` | Business metrics, analytics router |
| `shared.whitelabel` | Custom domains, SSL automation |
| `shared.rag` | Vector search for MCP/RAG |
| `shared.ai_llm` | LLM integration (OpenAI, Anthropic, local) |
| `shared.affiliate_toolkit` | Attribution tracking, touch ledger |
| `shared.rate_limiter` | API rate limiting |
| `shared.audit` | Audit logging |
| `shared.gdpr` | GDPR/CCPA compliance, DSAR |
| `shared.consent` | Consent management |
| `shared.secrets` | KMS-encrypted credential storage |
| `shared.email_builder` | MJML/components, inlining |
| `shared.email_marketing` | Campaign scheduling, preferences |
| `shared.deliverability` | Inbox placement, reputation |
| `shared.webhooks` | Ingress/egress, DLQ, retry |
| `shared.workflows` | Durable execution, n8n adapters |
| `shared.oauth` | Platform OAuth, token refresh |
| `shared.integrations` | AWS/Azure/GCP/Cloudflare clients |

---

## Dynamic Workflow Engine

### Visual Flow Builder (React Flow)

```typescript
// Node Types (extensible via vertical packs)
interface FlowNode {
  id: string;
  type: 'trigger' | 'action' | 'condition' | 'delay' | 'branch' | 'webhook';
  position: { x: number; y: number };
  data: {
    label: string;
    config: Record<string, any>;  // Dynamic config per node type
    schema: JSONSchema;           // Validation schema
  };
}

// Edge Types
interface FlowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;  // For branching (yes/no)
  targetHandle?: string;
  type: 'default' | 'conditional';
}
```

### Execution Engine (Durable, Shared)

```python
# Uses shared.workflows.durable_execution
class WorkflowEngine:
    async def execute(self, flow_def: FlowDefinition, trigger_data: dict) -> Execution:
        # 1. Validate against schema
        # 2. Create execution context
        # 3. Execute nodes with checkpointing
        # 4. Handle retries, timeouts, compensation
        # 5. Emit events for analytics
```

---

## Analytics Core (SQLMesh + Dynamic)

### Dynamic Metric Definitions

```yaml
# Metric definition (stored in DB, versioned)
metric: daily_revenue
entity: order
dimensions: [client_id, date, channel, product_category]
measures:
  - name: total_revenue
    expression: SUM(amount)
  - name: order_count
    expression: COUNT(*)
  - name: aov
    expression: SUM(amount) / COUNT(*)
filters:
  - field: status
    operator: in
    value: [completed, shipped]
time_grain: day
```

### Auto-Generated Dashboards

```yaml
# Dashboard layout (config-driven)
dashboard: marketing_roster
layout: grid
widgets:
  - id: revenue_trend
    type: line_chart
    metric: daily_revenue
    dimensions: [date]
    series: channel
  - id: top_campaigns
    type: table
    metric: campaign_performance
    sort: -attributed_revenue
    limit: 10
```

---

## MCP Server (AI-Native)

### Dynamic Tool Registration

```python
# Tools auto-registered from vertical packs
class MCPToolRegistry:
    def register_vertical_tools(self, vertical: str):
        for tool_def in vertical_pack.mcp_tools:
            self.mcp_server.add_tool(
                name=tool_def.name,
                description=tool_def.description,
                input_schema=tool_def.input_schema,
                handler=tool_def.handler
            )
```

### Example Tools (Per Vertical)

```python
# Marketing vertical
get_roster_summary(agency_id, date_range)
get_campaign_performance(client_id, campaign_id?)
get_retention_cohorts(client_id, cohort_months)
get_rfm_segments(client_id)
search_creatives(query, channel?, limit)

# Ecommerce vertical
get_order_metrics(client_id, date_range)
get_product_performance(client_id, category?)
get_cart_abandonment_rate(client_id)
get_customer_ltv(client_id, segment?)

# SaaS vertical
get_mrr_metrics(client_id, date_range)
get_churn_analysis(client_id, cohort_months)
get_expansion_revenue(client_id)
get_usage_metrics(client_id, feature?)
```

---

## Database Schema (Dynamic + Fixed)

### Fixed Core Tables

```sql
-- Multi-tenancy (fixed)
agencies, agency_users, clients, client_users

-- Dynamic entities (EAV + JSONB)
entity_definitions (id, vertical, name, version, schema_json, ui_schema_json, created_at)
entity_records (id, entity_def_id, client_id, data_jsonb, status, created_at, updated_at)
entity_relationships (id, source_entity_def_id, target_entity_def_id, type, config_json)

-- Workflows (fixed structure, dynamic definitions)
flow_definitions (id, client_id, entity_def_id, version, nodes_json, edges_json, status)
flow_executions (id, flow_definition_id, trigger_data_json, status, current_node, context_json)

-- Events (append-only)
events (id, client_id, entity_type, entity_id, event_type, payload_jsonb, timestamp)

-- Materialized views (SQLMesh managed)
mv_daily_metrics, mv_cohort_retention, mv_rfm_segments, mv_attribution
```

---

## Security & Compliance (Built-in)

| Layer | Implementation |
|-------|----------------|
| **Data Isolation** | PostgreSQL RLS policies per agency/client |
| **Encryption** | AES-256 at rest (TDE), TLS 1.3 in transit |
| **Secrets** | `shared.secrets` - KMS-encrypted, auto-rotation |
| **PII** | Automatic hashing (email/phone), tokenization |
| **Audit** | `shared.audit` - immutable event log |
| **Consent** | `shared.consent` - granular, versioned |
| **GDPR/CCPA** | `shared.gdpr` - DSAR automation, right to be forgotten |
| **SOC 2** | `shared.compliance_monitoring` - continuous evidence |
| **RBAC** | `shared.auth.rbac` - resource-level permissions |
| **API Security** | Rate limiting, JWT + mTLS, request signing |

---

## Deployment

### Development (Docker Compose)

```yaml
services:
  postgres: { image: pgvector/pgvector:pg16, ports: [5432] }
  redis: { image: redis:7-alpine, ports: [6379] }
  clickhouse: { image: clickhouse/clickhouse-server, ports: [8123, 9000] }
  chroma: { image: chromadb/chroma, ports: [8000] }
  api: { build: ./apps/api, ports: [8765], env_file: .env }
  worker: { build: ./apps/workers, env_file: .env }
  mcp: { build: ./apps/mcp-server, env_file: .env }
  web-customer: { build: ./apps/web-customer, ports: [8766] }
  web-dev: { build: ./apps/web-dev, ports: [8767] }
  mailhog: { image: mailhog/mailhog, ports: [8025, 1025] }
  minio: { image: minio/minio, ports: [9000, 9001] }
```

### Production (AWS + Terraform)

- **ECS Fargate** for API, workers, frontends
- **RDS PostgreSQL** (Multi-AZ, read replicas)
- **ElastiCache Redis** (cluster mode)
- **ClickHouse Cloud** or **Tinybird**
- **S3** for blobs, **CloudFront** CDN
- **Route 53** + **ACM** for custom domains
- **WAF** + **Shield** for DDoS
- **GitHub Actions** → **ECR** → **ECS** deployment

---

## Cost Optimization

| Strategy | Savings |
|----------|---------|
| ClickHouse for analytics (not Postgres) | 80% query cost reduction |
| SQLMesh incremental models | 90% compute reduction |
| Redis Streams for events (not Kafka) | 70% infra cost |
| Shared services across verticals | 60% dev/maintenance |
| Spot instances for workers | 50% compute |
| Multi-tenant RLS (not separate DBs) | 95% DB cost |

---

## Development Standards

### Code Quality Gates (All Must Pass)

```bash
# Pre-commit
ruff check --select ALL .
mypy --strict .
pytest --cov=90 --cov-fail-under=80

# CI
bandit -r .
pip-audit
sqlmesh test
playwright test --project=chromium
lighthouse --budget=performance=90,accessibility=100
```

### Zero-Tolerance Policies

- **No hardcoded vertical logic** in core packages
- **No direct DB access** outside repositories
- **No sync HTTP calls** in async code
- **No secrets in code** (use `shared.secrets`)
- **No untyped public APIs**
- **No untested entity definitions**
- **No breaking API changes** without versioning

---

## Project Structure

```
retention-analytics-platform/
├── apps/
│   ├── api/                 # FastAPI gateway + dynamic entity API
│   ├── workers/             # Celery workers (events, workflows, sync)
│   ├── mcp-server/          # FastMCP server
│   ├── web-customer/        # Next.js customer portal
│   └── web-dev/             # Next.js developer console
├── packages/
│   ├── core/                # Platform kernel (entities, workflows, permissions)
│   ├── engagement/          # Email, SMS, Push, Flows, Templates, Deliverability
│   ├── ecommerce/           # Subscriptions, Core (products, orders)
│   ├── analytics-core/      # SQLMesh models, metric registry
│   ├── attribution-engine/  # Attribution logic
│   ├── reporting-engine/    # PDF/HTML reports, drag-drop builder
│   ├── vertical-packs/      # Marketing, Ecommerce, SaaS, Fintech, Healthcare
│   ├── integrations/        # Optional external platform imports
│   ├── shared-types/        # TypeScript/Python shared types
│   └── shared-config/       # Config integration
├── infra/
│   ├── docker/              # Dockerfiles, compose
│   ├── terraform/           # AWS infrastructure
│   └── k8s/                 # Kubernetes manifests (optional)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── VERTICAL_PACKS.md
│   ├── WORKFLOW_ENGINE.md
│   └── DEPLOYMENT.md
└── scripts/
    ├── dev.sh               # Start dev environment
    ├── test.sh              # Run all tests
    ├── deploy.sh            # Deploy to staging/prod
    └── vertical-pack.py     # Scaffold new vertical pack
```

---

## Implementation Priority

### Phase 1: Platform Kernel (4 weeks)
- [ ] Dynamic entity system (definitions, API, permissions)
- [ ] Multi-tenancy + auth integration
- [ ] Event bus + event sourcing
- [ ] Developer console: schema builder
- [ ] Customer portal: dynamic list/detail views

### Phase 2: Engagement Services (6 weeks)
- [ ] Email service (SES/SendGrid, templates, tracking)
- [ ] SMS service (Twilio, compliance)
- [ ] Push service (FCM/APNs, web push)
- [ ] Flow engine (visual builder + durable execution)
- [ ] Template service (MJML, components, versioning)
- [ ] Deliverability service (reputation, inbox placement)

### Phase 3: Ecommerce + Subscriptions (4 weeks)
- [ ] Subscription service (plans, lifecycle, dunning)
- [ ] Ecommerce core (products, orders, cart)
- [ ] Payment integrations (Stripe, Adyen)

### Phase 4: Analytics + Reporting (4 weeks)
- [ ] SQLMesh models + dynamic metrics
- [ ] Attribution engine
- [ ] Report builder (drag-drop)
- [ ] Dashboard builder
- [ ] MCP server + vertical tools

### Phase 5: Vertical Packs + Polish (4 weeks)
- [ ] Marketing vertical pack
- [ ] Ecommerce vertical pack
- [ ] SaaS vertical pack
- [ ] White-label domains + SSL
- [ ] Load testing + optimization
- [ ] Documentation + examples

---

## Competitive Advantages

| Feature | Competition | Our Platform |
|---------|-------------|--------------|
| **In-house engagement** | ❌ (integrate only) | ✅ Full stack |
| **Dynamic workflows** | ❌ (hardcoded) | ✅ Visual, code-free |
| **Multi-vertical** | ❌ (single vertical) | ✅ Pluggable packs |
| **Dual frontend** | ❌ (one UI) | ✅ Customer + Dev |
| **MCP native** | ❌ (bolt-on) | ✅ First-class |
| **Shared services** | ❌ (rebuild each time) | ✅ Battle-tested lib |
| **Cost at scale** | $$$$$ | $ (ClickHouse, SQLMesh) |
| **Time to vertical** | 6-12 months | 2-4 weeks (pack) |

---

## References

- [shared-canonical-services](../shared-canonical-services) - Shared service library
- [forms-workflow-automation](../forms-workflow-automation) - Workflow patterns reference
- [MONETIZATION_POLICY](../shared-canonical-services/shared/affiliate/MONETIZATION_POLICY.md)
- [GEO_TARGETING](../shared-canonical-services/shared/affiliate/GEO_TARGETING.md)
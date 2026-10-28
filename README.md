# Retention Analytics Platform

A **dynamic, multi-vertical analytics & engagement platform** built on reusable shared services. Provides in-house email, SMS, push notifications, automation flows, subscriptions, ecommerce, and analytics - configurable for any vertical (marketing, ecommerce, SaaS, fintech, healthcare) without code changes.

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **In-House Engagement Stack** | Email, SMS, Push, Flows, Templates, Deliverability - no external ESP dependency |
| **In-House Ecommerce** | Subscriptions, Products, Orders, Cart Abandonment |
| **Dynamic Entity System** | Schema-as-data: entities, fields, relationships defined at runtime |
| **Visual Workflow Engine** | Drag-drop automation builder with durable execution |
| **Multi-Vertical Packs** | Pluggable domain packs (Marketing, Ecommerce, SaaS, Fintech, Healthcare) |
| **Dual Frontend** | Customer Portal (agencies) + Developer Console (platform ops) |
| **MCP Server** | AI-native: query analytics via natural language |
| **Dynamic Reporting** | Drag-drop report builder, PDF/HTML/CSV/JSON export, scheduled delivery |
| **Multi-Tenancy** | Agency → Client → User hierarchy with PostgreSQL RLS |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPER CONSOLE                             │
│  Schema Builder │ Workflow Designer │ Vertical Packs │ Tenants  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     CUSTOMER PORTAL                              │
│  Dashboards │ Campaigns │ Flows │ Reports │ Settings (White-label)│
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                     │
│  Auth/Tenancy │ Dynamic Entity API │ Workflow Engine │ Analytics │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Engagement   │    │  Ecommerce    │    │  Analytics    │
│  Services     │    │  Services     │    │  Core         │
│ (Email/SMS/   │    │ (Subs/Core)   │    │ (SQLMesh/     │
│  Push/Flows)  │    │               │    │  dbt)         │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
│  PostgreSQL (RLS) │ Redis Streams │ ClickHouse │ ChromaDB │ S3 │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Project Structure

```
retention-analytics-platform/
├── apps/
│   ├── api/              # FastAPI gateway + dynamic entity API
│   ├── workers/          # Celery workers (events, workflows, sync)
│   ├── mcp-server/       # FastMCP server for AI assistants
│   ├── web-customer/     # Next.js customer portal (agencies)
│   └── web-dev/          # Next.js developer console (platform ops)
├── packages/
│   ├── core/             # Platform kernel (entities, workflows, permissions)
│   ├── engagement/       # Email, SMS, Push, Flows, Templates, Deliverability
│   ├── ecommerce/        # Subscriptions, Core (products, orders)
│   ├── analytics-core/   # SQLMesh models, metric registry
│   ├── attribution-engine/ # Attribution logic
│   ├── reporting-engine/ # PDF/HTML reports, drag-drop builder
│   ├── vertical-packs/   # Marketing, Ecommerce, SaaS, Fintech, Healthcare
│   ├── integrations/     # Optional external platform imports
│   ├── shared-types/     # TypeScript/Python shared types
│   └── shared-config/    # Config integration
├── infra/
│   ├── docker/           # Dockerfiles, compose
│   └── terraform/        # AWS infrastructure
└── docs/
    └── ARCHITECTURE.md   # Detailed architecture documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- uv (Python package manager)

### Development Setup

```bash
# Clone and setup
cd retention-analytics-platform

# Install Python dependencies
uv sync --all-extras

# Install Node dependencies
cd apps/web-customer && npm install
cd ../web-dev && npm install

# Start development environment
docker-compose -f infra/docker/docker-compose.yml up -d

# Run API server
cd apps/api && uv run uvicorn app.main:app --reload --port 8765

# Run customer portal
cd apps/web-customer && npm run dev

# Run developer console
cd apps/web-dev && npm run dev

# Run MCP server
cd apps/mcp-server && uv run python -m mcp_server.main
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/retention_analytics

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth (WorkOS)
WORKOS_API_KEY=sk_...
WORKOS_CLIENT_ID=client_...

# Billing (Stripe)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Platform OAuth (for optional integrations)
KLAVIYO_CLIENT_ID=...
SHOPIFY_API_KEY=...

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run specific package tests
uv run pytest packages/reporting-engine/tests -v

# Run with coverage
uv run pytest --cov=packages --cov-report=html

# Run integration tests
uv run pytest -m integration

# Type checking
uv run mypy .

# Linting
uv run ruff check .
```

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed architecture documentation
- [API Reference](docs/API.md) - REST API and MCP tool reference
- [Vertical Packs](docs/VERTICAL_PACKS.md) - Creating custom vertical packs
- [Workflow Engine](docs/WORKFLOW_ENGINE.md) - Building custom workflows
- [Deployment](docs/DEPLOYMENT.md) - Production deployment guide

## 🔧 Core Packages

### Shared Services (from `shared-canonical-services`)

| Package | Purpose |
|---------|---------|
| `shared.multitenancy` | Agency/Client/User hierarchy, RLS |
| `shared.auth` | Authentication, RBAC, MFA, sessions |
| `shared.billing` | Stripe subscriptions, metered billing |
| `shared.database` | DB config, migrations, backup |
| `shared.analytics` | Metrics collection, KPI dashboards |
| `shared.metrics` | Business metrics, analytics router |
| `shared.reporting` | Base reporting service |
| `shared.email_builder` | MJML/template components |
| `shared.deliverability` | Inbox placement, reputation |
| `shared.webhooks` | Ingress/egress, DLQ, retry |
| `shared.workflows` | Durable execution, n8n adapters |
| `shared.oauth` | Platform OAuth, token refresh |
| `shared.rag` | Vector search for MCP/RAG |
| `shared.ai_llm` | LLM integration |

### Platform Packages

| Package | Description |
|---------|-------------|
| `core` | Dynamic entity system, workflow engine, permissions |
| `engagement/email` | Campaigns, templates, sending (SES/SendGrid), tracking |
| `engagement/sms` | Campaigns, compliance (TCPA), delivery receipts |
| `engagement/push` | Web push (FCM/APNs), mobile push, rich notifications |
| `engagement/flows` | Visual builder, durable execution, triggers/actions |
| `engagement/templates` | MJML editor, components, versioning, brand kits |
| `engagement/deliverability` | IP warmup, reputation, blocklist monitoring |
| `ecommerce/subscriptions` | Plans, lifecycle, billing, dunning, revenue recognition |
| `ecommerce/core` | Products, orders, cart, customers, inventory |
| `analytics-core` | SQLMesh models, dynamic metrics, materialized views |
| `attribution-engine` | Multi-touch attribution, channel priority, deduplication |
| `reporting-engine` | Drag-drop builder, PDF/HTML/CSV/JSON, scheduling |
| `vertical-packs/*` | Pluggable domain packs with entities, workflows, reports |

## 🌐 API Endpoints

### Core Entities (Dynamic)
```
GET    /api/v1/entities/{entity_id}              # List with filters
POST   /api/v1/entities/{entity_id}              # Create
GET    /api/v1/entities/{entity_id}/{id}         # Read
PATCH  /api/v1/entities/{entity_id}/{id}         # Update
DELETE /api/v1/entities/{entity_id}/{id}         # Delete
POST   /api/v1/entities/{entity_id}/{id}/actions/{action}  # Custom actions
```

### Engagement
```
GET    /api/v1/clients/{id}/email/campaigns
POST   /api/v1/clients/{id}/email/campaigns
POST   /api/v1/clients/{id}/email/campaigns/{id}/send
GET    /api/v1/clients/{id}/sms/campaigns
POST   /api/v1/clients/{id}/push/campaigns
GET    /api/v1/clients/{id}/flows
POST   /api/v1/clients/{id}/flows
POST   /api/v1/clients/{id}/flows/{id}/publish
```

### Ecommerce
```
GET    /api/v1/clients/{id}/subscriptions/plans
POST   /api/v1/clients/{id}/subscriptions
PATCH  /api/v1/subscriptions/{id}
POST   /api/v1/subscriptions/{id}/cancel
GET    /api/v1/clients/{id}/products
GET    /api/v1/clients/{id}/orders
```

### Analytics & Reporting
```
GET    /api/v1/clients/{id}/metrics/roster
GET    /api/v1/clients/{id}/metrics/daily
GET    /api/v1/clients/{id}/metrics/retention
GET    /api/v1/clients/{id}/metrics/rfm
POST   /api/v1/clients/{id}/reports
GET    /api/v1/reports/{id}/runs/{run_id}/download
```

### MCP Tools (for AI Assistants)
```
get_roster_summary(agency_id, date_range)
get_client_metrics(client_id, date_range)
get_campaign_performance(client_id, campaign_id?)
get_flow_performance(client_id, flow_id?)
get_retention_cohorts(client_id, cohort_months)
get_rfm_segments(client_id)
get_subscription_metrics(client_id)
search_creatives(query, channel?, limit)
execute_custom_query(source_type, metrics, dimensions, filters)
```

## 🚢 Deployment

### Development
```bash
docker-compose -f infra/docker/docker-compose.yml up -d
```

### Production (AWS)
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### CI/CD
GitHub Actions workflows in `.github/workflows/`:
- `test.yml` - Unit, integration, contract tests
- `build.yml` - Docker images, push to ECR
- `deploy.yml` - Terraform apply, ECS service update
- `migrate.yml` - Database migrations

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`uv run pytest`)
4. Run linting (`uv run ruff check . && uv run mypy .`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

### Code Standards
- **Zero hardcoded vertical logic** in core packages
- **No direct DB access** outside repositories
- **No sync HTTP calls** in async code
- **No secrets in code** (use `shared.secrets`)
- **No untyped public APIs**
- **No untested entity definitions**

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [shared-canonical-services](../shared-canonical-services) - Battle-tested shared service library
- [forms-workflow-automation](../forms-workflow-automation) - Workflow patterns reference
- All open-source libraries that make this possible
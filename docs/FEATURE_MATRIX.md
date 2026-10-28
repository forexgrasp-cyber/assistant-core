# Competitive Analysis & Feature Matrix - Retention Analytics Platform

## Competitor Landscape

| Competitor | Target | Strengths | Weaknesses | Pricing |
|------------|--------|-----------|------------|---------|
| **Hiro** | Retention agencies | Klaviyo partner, MCP, white-label, roster view | Limited integrations, no in-house engagement, expensive | ~$500-600/mo (10-20 clients) |
| **Triple Whale** | DTC brands | Creative analytics, Pixel, LTV, benchmarks | No agency multi-client, no white-label, no MCP | $129-479/mo |
| **Polar Analytics** | Shopify brands | Unified dashboard, alerts, benchmarks | Shopify-only, no agency features, no MCP | $300-800/mo |
| **Northbeam** | Media buyers | Multi-touch attribution, creative testing | Expensive, complex setup, no agency workflow | $1,000+/mo |
| **Databox** | Agencies/Teams | 70+ integrations, scorecards, goals | Generic, no retention depth, no attribution | $200-800/mo |
| **Glew.io** | Ecommerce | LTV, cohorts, RFM, benchmarks | No agency multi-client, no white-label | $299-999/mo |
| **Peel Insights** | Shopify brands | Cohorts, LTV, retention, automated | Shopify-only, no multi-platform, no MCP | $199-499/mo |
| **Daasity** | Enterprise DTC | Custom data warehouse, ELT, BI | Very expensive, long implementation, no MCP | $5,000+/mo |

---

## Feature Matrix - What We Must Beat

### 1. Multi-Client Agency Architecture (Hiro's Moat)

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| Agency → Client hierarchy | ✅ | ❌ | ❌ | ❌ | ✅ Basic | **✅ Deep (3-level)** |
| White-label client portals | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Full CNAME + SSL** |
| Client-specific branding | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Per-client themes** |
| Roster dashboard (all clients) | ✅ | ❌ | ❌ | ❌ | ✅ | **✅ Real-time + alerts** |
| Client pacing vs goals | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Multi-metric pacing** |
| Revenue drop alerts | ✅ | ❌ | ✅ Basic | ❌ | ✅ | **✅ ML anomaly detection** |
| Cross-client creative ranking | ✅ | ✅ | ❌ | ✅ | ❌ | **✅ AI-powered insights** |
| Team collaboration (comments, tasks) | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Built-in workspace** |
| Client onboarding wizard | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Guided + automated** |

**OUR EDGE**: True 3-level tenancy (Platform → Agency → Client → User), full white-label with custom domains, ML-powered roster intelligence, built-in agency workspace.

---

### 2. Integrations Breadth & Depth

| Platform | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|----------|------|--------------|-------|-----------|---------|----------------|
| **Email/SMS** | | | | | | |
| Klaviyo | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Native + Import** |
| Attentive | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Native + Import** |
| Postscript | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Native + Import** |
| Omnisend | ✅ | ✅ | ❌ | ✅ | ✅ | **✅ Native + Import** |
| Sendlane | ✅ | ✅ | ❌ | ❌ | ✅ | **✅ Native + Import** |
| **Our In-House** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Full Stack** |
| **Store** | | | | | | |
| Shopify | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Native + Import** |
| **Our In-House** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Full Ecommerce** |
| **Subscriptions** | | | | | | |
| Recharge | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Native + Import** |
| Skio | ✅ | ✅ | ❌ | ✅ | ❌ | **✅ Native + Import** |
| Loop | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Native + Import** |
| Stay AI | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Native + Import** |
| Ordergroove | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Native + Import** |
| **Our In-House** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Full Subscriptions** |
| **Popups/Forms** | | | | | | |
| Alia | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Native + Import** |
| **Our In-House** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Full Forms/Popups** |
| **Ads** | | | | | | |
| Meta Ads | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ Full + Creative** |
| Google Ads | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ Full + Creative** |
| TikTok Ads | ❌ | ✅ | ❌ | ✅ | ✅ | **✅ Full + Creative** |
| **Analytics** | | | | | | |
| GA4 | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ Full + Custom Events** |
| GSC | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ Full + Content** |
| **Warehouse** | | | | | | |
| Snowflake | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Read + Write** |
| BigQuery | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Read + Write** |
| Redshift | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Read + Write** |

**OUR EDGE**: Only platform with **in-house engagement stack** (email/SMS/push/flows) + **in-house ecommerce/subscriptions** + **optional imports** from all competitors. Zero vendor lock-in.

---

### 3. Analytics & Attribution

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **Attribution Models** | | | | | | |
| Last-click | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| First-click | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| Linear | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| Time-decay | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| Position-based (U-shaped) | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| **Custom ML model** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Auto-ML** |
| **Multi-touch with deduplication** | ✅ | ✅ | ✅ | ✅ | ❌ | **✅ Advanced** |
| **Cross-device matching** | ❌ | ✅ | ❌ | ✅ | ❌ | **✅ Probabilistic + Deterministic** |
| **Offline conversion import** | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ POS + CRM** |
| **Attribution windows (configurable)** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Per-channel + per-client** |
| **Revenue reconciliation** | ✅ | ✅ | ✅ | ✅ | ❌ | **✅ Automated daily** |
| **Attribution confidence scoring** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Bayesian confidence** |

| **Retention Analytics** | | | | | | |
| Cohort analysis (1/3/6/12mo) | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Real-time + Predictive** |
| RFM segmentation | ✅ | ✅ | ✅ | ❌ | ✅ | **✅ Auto-refresh + Push to ESP** |
| Product paths (1st→2nd→3rd) | ✅ | ❌ | ✅ | ❌ | ✅ | **✅ Visual Sankey + AI insights** |
| Time between orders | ✅ | ✅ | ✅ | ❌ | ✅ | **✅ Distribution + Percentiles** |
| Winback flow performance | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Flow-level attribution** |
| **Predictive LTV (ML)** | ❌ | ✅ | ❌ | ❌ | ✅ | **✅ Ensemble models + SHAP** |
| **Churn prediction (ML)** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Early warning + Actions** |
| **Next best action recommendations** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ RL-based** |

| **Subscription Analytics** | | | | | | |
| MRR/ARR tracking | ✅ | ✅ | ✅ | ❌ | ✅ | **✅ Real-time + Net new/expansion/churn** |
| Churn curves by cohort | ✅ | ✅ | ✅ | ❌ | ✅ | **✅ Kaplan-Meier + Cox regression** |
| LTV by starting product | ✅ | ✅ | ✅ | ❌ | ✅ | **✅ Multi-dimensional** |
| One-time → Subscriber conversion | ✅ | ❌ | ❌ | ❌ | ✅ | **✅ Funnel + Attribution** |
| Subscription attribution | ✅ | ✅ | ❌ | ❌ | ❌ | **✅ Recurring + One-time split** |
| **Pause/Resume impact analysis** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Causal inference** |
| **Price elasticity modeling** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ A/B + Historical** |

**OUR EDGE**: ML-powered attribution with confidence scoring, predictive LTV/churn with explainability, causal inference for subscription decisions, next-best-action RL engine.

---

### 4. Campaign & Flow Analytics

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **Campaign Deep Dive** | | | | | | |
| Creative + subject line side-by-side | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Visual gallery + AI tags** |
| Products purchased per campaign | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Attribution + Margin** |
| First-time vs returning buyers | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Cohort overlay** |
| A/B variant comparison | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Statistical significance** |
| **Creative element detection (AI)** | ❌ | ✅ | ❌ | ❌ | ❌ | **✅ CV + NLP auto-tagging** |
| **Creative fatigue detection** | ❌ | ✅ | ❌ | ❌ | ❌ | **✅ ML + Auto-pause recommendations** |
| **Send-time heatmap (rev/recipient)** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Per-segment + Channel** |
| **Deliverability score + inbox placement** | ✅ | ✅ | ✅ | ❌ | ❌ | **✅ Seed testing + Reputation** |
| **Bounce/complaint root cause** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Auto-classification + Fix** |

| **Flow/Automation Analytics** | | | | | | |
| Visual flow builder | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ React Flow + Versioning** |
| Branch-level performance | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Per-node revenue + Drop-off** |
| Per-message delivery/open/click/revenue | ✅ | ✅ | ❌ | ❌ | ❌ | **✅ Real-time + Anomaly alerts** |
| Flow revenue attribution | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Multi-touch within flow** |
| **Flow A/B testing (branch split)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Built-in + Auto-winner** |
| **Flow optimization recommendations** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ ML-based restructure suggestions** |
| **Cross-client flow templates** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Template marketplace + Sync** |

**OUR EDGE**: Only platform with visual flow builder + branch-level revenue attribution + ML optimization recommendations + cross-client template marketplace.

---

### 5. Reporting & Distribution

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **Report Builder** | | | | | | |
| Drag-drop builder | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Notion-style blocks + Code** |
| Pre-built templates | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ 50+ vertical-specific** |
| **AI-generated narratives** | ❌ | ✅ | ❌ | ❌ | ❌ | **✅ LLM + Custom prompts** |
| **Custom calculations/formulas** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Excel-like + SQL** |
| **Conditional formatting/alerts** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Threshold + Trend + Anomaly** |
| **Report versioning + approval** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Git-like + Workflow** |

| **Export Formats** | | | | | | |
| PDF (branded) | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Pixel-perfect + Watermarks** |
| HTML (interactive) | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Embeddable + Shareable** |
| CSV/Excel (raw data) | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Scheduled + API** |
| **PowerPoint/Google Slides** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Auto-generated decks** |
| **Notion/Confluence sync** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Bidirectional** |

| **Distribution** | | | | | | |
| Scheduled email | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Multi-recipient + CC/BCC** |
| Slack/Teams | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Rich blocks + Threads** |
| **Client white-label portal** | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Custom domain + SSO** |
| **Client self-serve dashboard** | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Embedded + Branded** |
| **Report embedding (iframe/JS)** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Signed URLs + Expiry** |
| **Webhook delivery** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Retry + DLQ + Signing** |

**OUR EDGE**: AI narratives with custom prompts, PowerPoint auto-generation, Notion sync, versioned reports with approval workflows, client white-label portals with SSO.

---

### 6. AI & MCP (New Category - First Mover Advantage)

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **MCP Server** | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ Full + SSE + Auth** |
| **Natural Language Queries** | ✅ | ❌ | ❌ | ❌ | ❌ | **✅ SQL + NoSQL + Explain** |
| **AI Report Generation** | ❌ | ✅ | ❌ | ❌ | ❌ | **✅ Prompt engineering + RAG** |
| **AI Creative Analysis** | ❌ | ✅ | ❌ | ❌ | ❌ | **✅ CV + NLP + Benchmarks** |
| **AI Anomaly Detection** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Multi-metric + Causal** |
| **AI Forecasting** | ❌ | ✅ | ❌ | ❌ | ✅ | **✅ Probabilistic + Scenarios** |
| **AI Recommendations** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Actionable + ROI-estimated** |
| **Custom AI Agents** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Build-your-own + Marketplace** |
| **RAG over Client Data** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Per-client + Privacy** |
| **Prompt Templates Marketplace** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Shareable + Versioned** |

**OUR EDGE**: First platform with full MCP + SSE, custom AI agents, prompt marketplace, per-client RAG with privacy guarantees.

---

### 7. Developer Experience (New Category)

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **Public REST API** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ OpenAPI 3.1 + SDKs** |
| **GraphQL API** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Federation + Subscriptions** |
| **Webhooks (reliable)** | ❌ | ✅ | ✅ | ✅ | ✅ | **✅ Signed + Retry + DLQ + Replay** |
| **SDKs (Python, TS, Go, Rust)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Generated + Typed** |
| **CLI Tool** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Full platform control** |
| **Terraform Provider** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Infrastructure as Code** |
| **Local Dev Environment** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Docker Compose + Tilt** |
| **Preview Deployments** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ PR-based + Seeded data** |
| **Schema Registry** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Versioned + Breaking change detection** |
| **API Mocking/Testing** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Contract testing + Chaos** |

**OUR EDGE**: Only platform with GraphQL federation, Terraform provider, local dev with Tilt, preview deployments, schema registry with breaking change detection.

---

### 8. Security, Compliance & Enterprise

| Feature | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|---------|------|--------------|-------|-----------|---------|----------------|
| **SOC 2 Type II** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Continuous + Public report** |
| **GDPR/CCPA/DSAR automation** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ One-click + Audit trail** |
| **HIPAA (opt-in)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ BAA + Encrypted PHI** |
| **PCI DSS (payments)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Level 1 + Tokenization** |
| **SSO (SAML/OIDC)** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ SCIM + JIT + Groups** |
| **RBAC (resource-level)** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ ABAC + Conditions** |
| **Audit Logs (immutable)** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ Cryptographic + Queryable** |
| **Data Residency (EU/US/APAC)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Multi-region + Failover** |
| **Encryption (KMS + BYOK)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Per-tenant + Rotation** |
| **Penetration Testing (annual)** | ✅ | ✅ | ✅ | ✅ | ✅ | **✅ Continuous + Bug bounty** |
| **Incident Response (SLA)** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ 15min + Runbooks** |

**OUR EDGE**: HIPAA/PCI opt-in, ABAC with conditions, cryptographic audit logs, multi-region data residency, 15min incident response with runbooks.

---

### 9. Performance & Scale

| Metric | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|--------|------|--------------|-------|-----------|---------|----------------|
| **Query Latency (p95)** | ~2s | ~1s | ~1.5s | ~3s | ~500ms | **<100ms (ClickHouse)** |
| **Dashboard Load (p95)** | ~3s | ~2s | ~2s | ~4s | ~1s | **<500ms (Edge + Cache)** |
| **Max Clients per Agency** | 200+ | N/A | N/A | N/A | 100+ | **10,000+ (Horizontal)** |
| **Events/Day** | ~100M | ~50M | ~100M | ~1B | ~1B | **1B+ (Partitioned)** |
| **Data Freshness** | Daily | Hourly | Hourly | 15min | 5min | **Real-time (Streams)** |
| **Uptime SLA** | 99.9% | 99.9% | 99.9% | 99.9% | 99.9% | **99.99% (Multi-AZ)** |
| **RPO/RTO** | 24h/4h | 24h/4h | 24h/4h | 24h/4h | 1h/1h | **1min/5min (Continuous)** |

**OUR EDGE**: Sub-100ms queries on ClickHouse, real-time streaming, 10k+ clients per agency, 99.99% uptime, 1min RPO.

---

### 10. Pricing & Business Model (Competitive Advantage)

| Model | Hiro | Triple Whale | Polar | Northbeam | Databox | **OUR TARGET** |
|-------|------|--------------|-------|-----------|---------|----------------|
| **Pricing Model** | Per-client + seats | Tiered revenue | Per-store | Custom | Per-seat | **Flexible: Per-client + Usage + Seats** |
| **Starting Price** | ~$500/mo | $129/mo | $300/mo | $1,000+/mo | $200/mo | **$299/mo (5 clients)** |
| **Free Trial** | 30 days | 14 days | 14 days | Demo only | 14 days | **60 days + Migration help** |
| **Setup Fee** | $0 | $0 | $0 | $5,000+ | $0 | **$0 + Free migration** |
| **Overage Protection** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ Auto-throttle + Alerts** |
| **Non-profit/Education Discount** | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ 50% + Grant program** |
| **Partner/Agency Program** | ✅ | ❌ | ❌ | ❌ | ✅ | **✅ Revenue share + Co-selling** |

**OUR EDGE**: Most flexible pricing, longest trial with migration help, overage protection, partner revenue share.

---

## Complete Feature Checklist - Must Have for Launch

### Phase 1: Core Platform (Weeks 1-8)
- [ ] **Database**: Complete schema with all migrations (PostgreSQL + ClickHouse)
- [ ] **Auth**: WorkOS integration, JWT, RBAC, MFA, Passkeys, SCIM
- [ ] **Multi-tenancy**: 3-level RLS, agency/client/user, white-label domains
- [ ] **API Gateway**: FastAPI, GraphQL federation, rate limiting, OpenAPI 3.1
- [ ] **Event Bus**: Redis Streams, schema registry, DLQ, replay
- [ ] **Workers**: Celery + Beat, priority queues, retries, monitoring
- [ ] **Secrets**: HashiCorp Vault / AWS KMS, rotation, BYOK

### Phase 2: Engagement Stack (Weeks 5-12)
- [ ] **Email Service**: SES/SendGrid/Mailgun, MJML, templates, A/B, deliverability
- [ ] **SMS Service**: Twilio/Plivo, 10DLC/shortcode, TCPA compliance, opt-in/out
- [ ] **Push Service**: FCM/APNs, Web Push (VAPID), rich notifications
- [ ] **Flows Engine**: Visual builder (React Flow), durable execution, versioning
- [ ] **Templates**: MJML editor, component library, brand kits, versioning
- [ ] **Deliverability**: IP warmup, seed testing, reputation, blocklist monitoring

### Phase 3: Ecommerce + Subscriptions (Weeks 8-14)
- [ ] **Subscriptions**: Plans, trials, dunning, proration, revenue recognition
- [ ] **Payments**: Stripe/Adyen, tokens, 3DS, refunds, disputes
- [ ] **Products**: Catalog, variants, collections, inventory, bundles
- [ ] **Orders**: Cart, checkout, fulfillment, returns, abandoned cart
- [ ] **Customers**: Profiles, addresses, segments, GDPR deletion

### Phase 4: Analytics Core (Weeks 10-16)
- [ ] **ClickHouse**: Cluster setup, sharding, replication, TTL
- [ ] **SQLMesh**: Models, incremental, tests, CI/CD, virtual environments
- [ ] **ETL**: Real-time streams, batch collectors, backfill, quality checks
- [ ] **Attribution**: Multi-touch, ML model, confidence, reconciliation
- [ ] **Metrics**: Cohort, RFM, LTV, churn, predictive (MLflow + Feast)

### Phase 5: Reporting + MCP (Weeks 14-20)
- [ ] **Report Builder**: Notion-style, AI narratives, versioning, approvals
- [ ] **Exporters**: PDF (WeasyPrint), HTML, CSV, Excel, PPTX, Notion
- [ ] **Distribution**: Email, Slack/Teams, webhooks, client portals
- [ ] **MCP Server**: SSE + stdio, 20+ tools, RAG, custom agents
- [ ] **AI**: Report gen, creative analysis, forecasting, recommendations

### Phase 6: Frontends (Weeks 12-22)
- [ ] **Customer Portal**: Dashboard, campaigns, flows, reports, settings, white-label
- [ ] **Developer Console**: Schema builder, workflow designer, pack manager, tenants
- [ ] **Components**: Charts (Recharts), Tables (TanStack), Forms (RHF), Flow (React Flow)
- [ ] **Real-time**: WebSockets, optimistic UI, offline support

### Phase 7: Vertical Packs + Marketplace (Weeks 18-24)
- [ ] **Pack SDK**: CLI, scaffolding, testing, publishing
- [ ] **Core Packs**: Marketing, Ecommerce, SaaS, Fintech, Healthcare
- [ ] **Marketplace**: Discovery, install, updates, reviews, revenue share
- [ ] **Template Library**: Reports, flows, dashboards, campaigns

### Phase 8: Enterprise + Ops (Weeks 20-28)
- [ ] **Observability**: Prometheus, Grafana, Tempo, Loki, alerting
- [ ] **Security**: CSP, HSTS, penetration testing, bug bounty, incident runbooks
- [ ] **Compliance**: SOC 2, GDPR, HIPAA, PCI, audit logs, DSAR
- [ ] **Infrastructure**: Terraform, EKS/GKE, ArgoCD, GitOps
- [ ] **CI/CD**: GitHub Actions, preview deploys, contract tests, chaos
- [ ] **Documentation**: API docs, guides, SDKs, CLI, Terraform provider

---

## Implementation Priority - Beat Each Competitor

| Sprint | Focus | Beats |
|--------|-------|-------|
| 1-2 | Core platform + Auth + Multi-tenancy | Databox (arch), All (foundation) |
| 3-4 | In-house Email + SMS + Templates | Hiro (engagement), All (no vendor lock) |
| 5-6 | Flows Engine + Visual Builder | Hiro (flows), All (visual + durable) |
| 7-8 | Ecommerce + Subscriptions | Triple Whale/Polar (Shopify-only), All (in-house) |
| 9-10 | ClickHouse + SQLMesh + Attribution | Northbeam (attribution), All (real-time + ML) |
| 11-12 | Reporting + MCP + AI | Hiro (MCP), All (SSE + Agents + RAG) |
| 13-14 | Customer Portal + White-label | Hiro (white-label), All (full CNAME + SSO) |
| 15-16 | Developer Console + SDKs | All (GraphQL + Terraform + CLI) |
| 17-18 | Vertical Packs + Marketplace | All (extensibility + ecosystem) |
| 19-20 | Observability + Security + Compliance | All (SOC2 + HIPAA + PCI + 99.99%) |
| 21-22 | Infrastructure + CI/CD + Load Testing | All (GitOps + Preview + Chaos) |
| 23-24 | Beta Launch + Migration Tools + Partner Program | Hiro (agency focus), All (ecosystem) |

---

## Success Metrics - Must Exceed Competitors

| Metric | Target | Competitor Best |
|--------|--------|-----------------|
| **Query Latency (p95)** | <100ms | 500ms (Databox) |
| **Dashboard Load (p95)** | <500ms | 1s (Databox) |
| **Data Freshness** | Real-time | 5min (Databox) |
| **Uptime** | 99.99% | 99.9% (all) |
| **Attribution Accuracy** | >95% (validated) | ~90% (Northbeam) |
| **Predictive LTV MAE** | <15% | ~25% (Triple Whale) |
| **Churn Prediction AUC** | >0.85 | ~0.75 (Glew) |
| **Report Generation** | <10s (PDF) | ~30s (Hiro) |
| **MCP Query Latency** | <2s | N/A (Hiro only) |
| **Client Onboarding Time** | <30min | ~2h (Hiro) |
| **Integration Setup** | <5min (native) | ~30min (Hiro) |
| **Support Response (P0)** | <15min | ~1h (all) |
| **NPS** | >70 | ~50 (best) |
| **Net Revenue Retention** | >130% | ~110% (best) |

---

## Technical Decisions - Why We Win

| Decision | Rationale | Competitor Gap |
|----------|-----------|----------------|
| **ClickHouse + SQLMesh** | Sub-100ms on billions of rows, incremental transforms, GitOps | All use Postgres/Snowflake - slow, expensive |
| **In-house Engagement** | Zero vendor lock-in, full data ownership, margins | All depend on Klaviyo/Attentive APIs |
| **GraphQL Federation** | Unified schema across services, subscriptions | All REST-only |
| **React Flow + Durable Execution** | Visual + reliable, versioned, testable | Hiro has flows but not visual + durable |
| **ML Attribution + Confidence** | Bayesian, explainable, auto-reconciliation | Northbeam has attribution but not confidence |
| **Per-client RAG + Privacy** | AI on client data without leakage | Hiro has MCP but no RAG/privacy |
| **Terraform Provider + CLI** | IaC for platform resources | None have this |
| **Preview Deployments + Tilt** | Fast local dev, PR environments | None have this |
| **Multi-region + 1min RPO** | True disaster recovery | All single-region, 1h+ RPO |
| **HIPAA/PCI Opt-in** | Vertical expansion | None offer this |

---

## Go-to-Market Differentiation

| Angle | Message | Proof |
|-------|---------|-------|
| **For Agencies** | "Only platform where you own the engagement stack + analytics + client portals" | In-house email/SMS/push + white-label + roster |
| **For Brands** | "Triple Whale depth + Northbeam attribution + in-house stack" | All features at 1/3 price |
| **For Developers** | "Stripe-level DX for analytics: GraphQL, Terraform, MCP, Preview deploys" | SDKs, CLI, local dev, schema registry |
| **For Enterprise** | "SOC2 + HIPAA + PCI + Multi-region + 99.99% + 15min IR" | Compliance matrix |
| **For Partners** | "Revenue share + co-selling + migration services + sandbox" | Partner program |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ClickHouse operational complexity | High | High | Managed Cloud (ClickHouse Cloud/Tinybird) + Runbooks |
| ML model accuracy | Medium | High | Human-in-loop, confidence thresholds, A/B testing |
| Deliverability reputation | High | High | Dedicated IP warmup, seed testing, compliance-first |
| Competitor API changes | High | Medium | Adapter pattern, versioned integrations, monitoring |
| Data privacy regulations | Medium | High | Privacy by design, DPIA, legal review quarterly |
| Talent acquisition | Medium | High | Remote-first, open source contributions, conference presence |
| Customer migration friction | High | High | Automated migration tools, white-glove onboarding, 60-day trial |

---

## Budget Estimate (First 18 Months)

| Category | Monthly | 18 Months |
|----------|---------|-----------|
| **Engineering (8 FTE)** | $120,000 | $2,160,000 |
| **Infrastructure (AWS/GCP)** | $15,000 | $270,000 |
| **ClickHouse Cloud** | $8,000 | $144,000 |
| **Vercel/Netlify (Frontends)** | $2,000 | $36,000 |
| **WorkOS/Auth0** | $3,000 | $54,000 |
| **Stripe/Adyen (platform fees)** | $5,000 | $90,000 |
| **SendGrid/Twilio/FCM (at scale)** | $10,000 | $180,000 |
| **Monitoring (Datadog/Grafana Cloud)** | $5,000 | $90,000 |
| **Security (Bug bounty, Pen test)** | $3,000 | $54,000 |
| **Legal/Compliance (SOC2, HIPAA)** | $8,000 | $144,000 |
| **Marketing/Sales (Post-launch)** | $20,000 | $360,000 |
| **Contingency (20%)** | $39,800 | $716,400 |
| **TOTAL** | **$238,800** | **$4,298,400** |

---

## Revenue Projection (Conservative)

| Month | Agencies | Avg Clients/Agency | MRR/Agency | Total MRR |
|-------|----------|-------------------|------------|-----------|
| 3 | 5 | 8 | $600 | $3,000 |
| 6 | 20 | 10 | $700 | $14,000 |
| 9 | 50 | 12 | $800 | $40,000 |
| 12 | 100 | 15 | $900 | $90,000 |
| 15 | 180 | 18 | $1,000 | $180,000 |
| 18 | 300 | 20 | $1,100 | $330,000 |

**Year 1 ARR: ~$1.5M | Year 2 ARR: ~$5M | Year 3 ARR: ~$15M**

---

This feature matrix defines the complete specification for a production-ready platform that beats every competitor in every measurable dimension. Every feature listed is a concrete implementation requirement.
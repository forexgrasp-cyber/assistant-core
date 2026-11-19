# AI Assistant

**One deployment. Every agent product. Capability-gated.**

`ai-assistant` is the *wrapper project*. It contains **no agent logic** — it
assembles the reusable services that live in
[`shared-canonical-services`](https://github.com/example/shared-canonical-services)
into a single capability-based platform.

```
PycharmProjects/
├── shared-canonical-services/   ← the library (single source of truth)
│   └── shared/
│       ├── agent_runtime/       ← core: UniversalAgent, AgentDefinition,
│       │                           Capability, VerticalSpec, entitlements
│       ├── agent_apps/          ← HTTP assembly: routers, services, deps
│       ├── platform/            ← multi-product app factory + platform service
│       └── ...                  ← auth, billing, voice, telephony, tutor, llm…
└── ai-assistant/                ← THIS PROJECT (wrapper only)
    └── app/
        ├── main.py              ← wiring: platform + entitlements + routes
        └── static/              ← landing page, dashboard
```

---

## Architecture

| Layer | Module | Responsibility |
|---|---|---|
| Core | `shared.agent_runtime` | `UniversalAgent`, `AgentDefinition`, `Capability`, `VerticalSpec`, entitlements |
| HTTP | `shared.agent_apps` | routers, per-vertical services, FastAPI dependencies |
| Platform | `shared.platform` | `create_unified_platform_app`, `UnifiedPlatformService` |
| Product | `ai-assistant/app` | tenant resolution, capability-gated routes, static surfaces |

### One agent core

There is exactly **one** agent implementation (`UniversalAgent`). Products are
differences in *data*, not code:

```python
from shared.agent_runtime.universal import create_agent

agent = create_agent("hvac")            # AgentDefinition from the registry
agent = create_agent("language-tutor")  # defined by its VerticalSpec
```

### Capabilities gate everything

A tenant's plan decides what they can reach. The canonical enum lives in
`shared.agent_runtime.capabilities`; legacy feature names (`"voice"`,
`"booking"`, …) resolve through the single alias table in the same module.

```python
from shared.agent_runtime.capabilities import Capability, resolve_capability

Capability.COMM_VOICE.value          # "communication.voice"
resolve_capability("voice")          # → Capability.COMM_VOICE
```

---

## Quick start (Windows)

```powershell
cd C:\Users\IhorLeshchuk\PycharmProjects\ai-assistant

# 1. Build + install the private shared wheel into this environment
.\install_shared_wheel.ps1

# 2. Copy the env template
Copy-Item .env.example .env

# 3. Run
uvicorn app.main:app --port 8000 --reload
```

Verify:

```powershell
curl.exe http://localhost:8000/health
```

---

## Endpoints

| Method | Path | Gating |
|---|---|---|
| GET | `/health` | public |
| GET | `/` , `/landing` | public |
| GET | `/dashboard` , `/app` | public (demo) |
| GET | `/api/v1/agents` | public |
| GET | `/api/v1/bundles` | public |
| GET | `/api/v1/entitlements/me` | tenant-scoped |
| GET | `/api/v1/entitlements/check/{capability}` | tenant-scoped |
| POST | `/api/v1/admin/entitlements/grant` | admin (prod: JWT role) |
| POST | `/api/v1/admin/entitlements/revoke` | admin (prod: JWT role) |
| POST | `/api/v1/agent/chat` | capability-gated |
| POST | `/api/v1/agent/voice/webhook` | `communication.voice` |
| GET | `/api/v1/callagent/calls` | `communication.voice` |
| POST | `/api/v1/callagent/calls/outbound` | `communication.voice` |
| GET | `/api/v1/tutor/curriculum` | `vertical.tutor` |
| GET | `/api/v1/tutor/progress` | `vertical.tutor` |
| GET | `/api/v1/jarvis/email` | `integration.email_provider` |
| GET | `/api/v1/jarvis/calendar` | `integration.calendar` |

### Tenant selection

Resolution order:

1. `X-Tenant-ID` header
2. subdomain (`<tenant>.example.com` → `tenant-<tenant>`)
3. `?tenant=<slug>` query parameter
4. default → `tenant-combo`

Demo tenants: `tenant-callagent`, `tenant-tutor`, `tenant-jarvis`,
`tenant-hvac`, `tenant-combo` (everything).

```powershell
curl.exe "http://localhost:8000/api/v1/entitlements/me?tenant=hvac"
curl.exe -H "X-Tenant-ID: tenant-tutor" http://localhost:8000/api/v1/tutor/curriculum
```

An **unconfigured** tenant is unrestricted (the agent definition is the
contract). A **configured** tenant is strict — only granted capabilities work.

---

## Deployment

```powershell
# Build the wheel, stage it, package and ship to the VPS
.\deploy.bat
```

or on Linux/macOS:

```bash
./deploy.sh
```

The script:

1. builds the private wheel in the canonical repo and stages it in `./dist/`
2. packages `docker-compose.yml`, `Dockerfile`, `nginx.conf`, `init-db.sh`
3. uploads to the VPS (`/opt/ai-assistant`)
4. starts PostgreSQL + Redis, runs the schema init, builds and starts the app
5. starts Nginx + Certbot

### Ports

| Service | Port |
|---|---|
| ai-assistant | 8000 |
| tutor-service | 8147 |
| callagent-service | 8192 |
| jarvis-service | 8301 |
| hvac-service | 8423 |

---

## Environment

See `.env.example`. Required in production:

```bash
SECRET_KEY=...                  # openssl rand -base64 32
POSTGRES_PASSWORD=...
PII_ENCRYPTION_KEY=...
CREDENTIAL_ENCRYPTION_KEY=...
```

Optional: LLM provider keys (free-tier providers work without keys), Twilio /
Plivo / SignalWire for telephony, SMTP for conversation export e-mail.

---

## Tests

The library's own suite lives in the canonical repo:

```powershell
cd ..\shared-canonical-services
python -m pytest tests/agent_runtime tests/agent_apps -q
```

There are no GitHub Actions workflows — everything runs locally.

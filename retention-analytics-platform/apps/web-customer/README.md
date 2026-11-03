# Customer Portal (web-customer)

Next.js frontend for agencies. Consumes the FastAPI API via `/api` rewrites.

Pages:
- `/` — landing
- `/dashboard` — platform status + workflows
- `/campaigns` — send email/SMS/push through registered services
- `/flows` — run durable workflows (churn prevention, cart abandonment, win-back)
- `/reports` — generate + download reports
- `/settings` — white-label agency settings

All service calls go through the API gateway, which routes them into the
ServiceRegistry and WorkflowEngine — no siloed frontend service calls.

Run:
```bash
npm install
npm run dev
```

# Stripe Webhook Testing

## Local testing with Stripe CLI

```bash
# 1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
# 2. Login
stripe login

# 3. Forward webhooks to local API
stripe listen --forward-to http://127.0.0.1:47319/api/v1/webhooks/payments/stripe

# 4. In another terminal, trigger a test event
stripe trigger payment_intent.succeeded
```

## Verify signature in production mode

Set `STRIPE_WEBHOOK_SECRET` env var (from `stripe listen` output or Stripe Dashboard → Webhooks):

```bash
$env:STRIPE_WEBHOOK_SECRET = "whsec_..."
$env:ENVIRONMENT = "production"
python -m uvicorn apps.api.main:app --port 47319
```

The endpoint at `POST /api/v1/webhooks/payments/stripe` verifies the HMAC-SHA256 signature and is idempotent (replaying the same event `id` returns `idempotent_replay: true`).

## Test idempotency

```bash
# Same event twice — second returns idempotent_replay
curl -X POST http://127.0.0.1:47319/api/v1/webhooks/payments/stripe \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"id": "evt_test_123", "type": "payment_intent.succeeded"}'
# Repeat — same response + "idempotent_replay": true
```

## Automated test

`tests/test_validation_all.py::test_payment_webhook_idempotent` verifies this in CI.

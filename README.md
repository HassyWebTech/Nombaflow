# NombaFlow — Managed Recurring Billing Engine

> The missing subscriptions layer for the Nomba ecosystem.

NombaFlow is a production-grade recurring billing engine built on top of Nomba's payment primitives. It gives product teams plan management, intelligent dunning, proration, and webhook-driven automation — without rebuilding subscription logic from scratch.

**Live Dashboard:** https://nombaflow.vercel.app  
**Live API:** https://nombaflow-production-686f.up.railway.app  
**API Docs:** https://nombaflow-production-686f.up.railway.app/docs  
**GitHub:** https://github.com/HassyWebTech/nombaflow

---

## The Problem

Nomba exposes powerful payment primitives but ships no managed subscriptions layer. Every product team that wants recurring billing rebuilds the same logic from scratch — plan management, billing cycles, failed-payment recovery, proration. NombaFlow solves this once, cleanly, for the entire Nomba ecosystem.

---

## What's Inside

**Subscription State Machine**  
Six states — trialing, active, past_due, paused, cancelled, expired — with validated transitions. No illegal state jumps. Every transition is logged and emitted as a webhook event.

**Intelligent Dunning Engine**  
Failed payment recovery with failure-reason classification and exponential backoff retries at 1, 3, 7, and 14 days. Cards flagged as expired or stolen skip retries entirely and escalate immediately.

**Proration Engine**  
Accurate mid-cycle credit calculation when customers upgrade or downgrade plans. Charges or credits the exact fraction of the billing period remaining.

**Webhook Infrastructure**  
HMAC-SHA256 signed payloads, per-merchant endpoint registration, event filtering with wildcard support, and automatic retry with backoff on delivery failure.

**Multi-Tenant Architecture**  
Every plan, customer, subscription, invoice, and webhook endpoint is scoped to a tenant. Full data isolation between merchants. API key authentication per tenant.

**Merchant Dashboard**  
Live React dashboard with subscription state machine visualizer, MRR metrics, dunning queue, and full CRUD operations — connected to the live backend.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL + SQLAlchemy 2.0 + Alembic |
| Task Queue | Celery + Redis |
| HTTP Client | httpx (async) |
| Frontend | React + Tailwind CSS |
| Deployment | Railway (backend + DB), Vercel (frontend) |
| Nomba APIs | Checkout, Tokenised Cards, Charge, Transfers |

---

## API Reference

All endpoints require `X-API-Key` header.

### Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/plans/` | Create billing plan |
| GET | `/v1/plans/` | List all plans |
| GET | `/v1/plans/{id}` | Get plan |
| PATCH | `/v1/plans/{id}` | Update plan |

### Customers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/customers/` | Create customer |
| GET | `/v1/customers/` | List customers |
| POST | `/v1/customers/{id}/checkout` | Create checkout session |

### Subscriptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/subscriptions/` | Subscribe customer to plan |
| GET | `/v1/subscriptions/` | List all subscriptions |
| POST | `/v1/subscriptions/{id}/cancel` | Cancel subscription |
| POST | `/v1/subscriptions/{id}/pause` | Pause subscription |
| POST | `/v1/subscriptions/{id}/resume` | Resume subscription |
| POST | `/v1/subscriptions/{id}/upgrade` | Upgrade plan with proration |
| POST | `/v1/subscriptions/{id}/downgrade` | Downgrade plan with credit |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/invoices/` | List invoices |
| GET | `/v1/invoices/{id}` | Get invoice |
| POST | `/v1/invoices/{id}/retry` | Retry failed invoice |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/webhooks/endpoints` | Register endpoint |
| GET | `/v1/webhooks/endpoints` | List endpoints |
| DELETE | `/v1/webhooks/endpoints/{id}` | Deactivate endpoint |
| POST | `/v1/webhooks/nomba/inbound` | Receive Nomba events |

---

## Running Locally

**Clone and set up backend:**

```bash
git clone https://github.com/HassyWebTech/nombaflow.git
cd nombaflow
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Configure environment:**

```bash
cp .env.example .env
# Fill in your values in .env
```

**Run migrations:**

```bash
alembic upgrade head
```

**Start backend:**

```bash
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nombaflow
REDIS_URL=redis://localhost:6379/0
NOMBA_CLIENT_ID=your_client_id
NOMBA_PRIVATE_KEY=your_private_key
NOMBA_ACCOUNT_ID=your_account_id
NOMBA_SUBACCOUNT_ID=your_subaccount_id
NOMBA_BASE_URL=https://api.nomba.com/v1
SECRET_KEY=your_secret_key
ENVIRONMENT=development
```

---

## Project Structure

```
nombaflow/
├── app/
│   ├── api/v1/          # Route handlers
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   │   ├── subscription_service.py   # State machine
│   │   ├── billing_service.py        # Charge execution
│   │   ├── dunning_service.py        # Retry orchestration
│   │   ├── proration_service.py      # Credit calculation
│   │   └── webhook_service.py        # Event dispatch
│   ├── nomba/           # Nomba API integration
│   └── workers/         # Celery tasks
├── alembic/             # Database migrations
├── tests/
├── main.py
└── requirements.txt
```

---

## Built for Nomba Hackathon 2026

**Hassan Yakubu**  
GitHub: [HassyWebTech](https://github.com/HassyWebTech)  
LinkedIn: [hassan-yakubu](https://www.linkedin.com/in/hassan-yakubu)  
X: [@yakubhassan83](https://x.com/yakubhassan83)****

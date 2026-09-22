# ExportOS

**AI Export Operations Copilot for Pakistani SME exporters**

ExportOS is a multi-tenant operations platform that keeps one authoritative record of an export deal from first buyer contact through payment and closure. Natural language (emails, RFQs, chat pastes, uploaded files) is interpreted by an LLM. Inventory, costing, state transitions, documents, compliance, and analytics stay **deterministic** — calculated in code, never invented by the model.

```text
Buyer inquiry → AI extraction → inventory check → Incoterm costing
    → quote approval → order confirmation → documents → compliance
    → shipment → payment → closed
```

---

## Why it exists

Export work for SMEs is usually scattered across WhatsApp, email, quotation spreadsheets, invoice templates, and informal checklists. That produces:

- Promised stock that is already reserved
- Quotes that do not match Incoterm obligations
- Documents that disagree with each other
- Missed State Bank of Pakistan (SBP) foreign-exchange realization windows

ExportOS puts those steps in one product, with role-based access, tenant isolation, and an audit trail.

---

## Features

### Organisation and access

- Multi-tenant organisations with full data isolation
- JWT authentication (register company + first admin, then invite the team)
- Roles: `ADMIN`, `EXPORT_MANAGER`, `DOCUMENTATION_OFFICER`, `SALES`, `ACCOUNTS`

### Catalogue and inventory

- SKU master with UoM, carton packing, net weight, default Pakistan HS code, and factory cost
- Deterministic availability: **available = current − reserved**
- Reservations on order confirmation so two people cannot sell the same units
- Shortfall handling: adjust quantity to what is in stock, or mark the deal for production / procurement

### Inquiries and AI extraction

- Intake from paste, PDF / Word / Excel upload, and inbound webhook
- Artifacts stored with SHA-256 integrity hashes
- Extraction via Hugging Face (`Qwen/Qwen2.5-Coder-32B-Instruct`) with rotating API keys on rate limits
- Field-level confidence and evidence quotes; human review before the deal is trusted

### Costing, quotes, and deal lifecycle

- Incoterms 2020: `EXW`, `FCA`, `FOB`, `CFR`, `CIF`, `CPT`, `CIP`, `DAP`, `DDP`
- Fixed-point decimal arithmetic for freight, packing, origin THC, insurance, and duties
- Quote approval before confirmation
- Directed state machine with immutable audit log:

```text
INQUIRY → QUOTED → CONFIRMED → IN_PRODUCTION → DOCS_READY
        → SHIPPED → PAID → CLOSED
```

`CANCELLED` is allowed until shipment. Terminal states do not reverse.

### Documents and consistency

- Generated set: Proforma Invoice, Commercial Invoice, Packing List, Certificate of Origin
- HTML preview and approval workflow
- Cross-document consistency checker (quantities, values, Incoterm, ports, parties)

### Compliance

- SBP foreign-exchange rules (Chapter XII and related circulars)
- Destination customs hints (US CBP, EU REX)
- HS code advisory against the product master

### Shipment and payment

- Shipments with Incoterm-aware milestone sequences
- Payment recording and deal-level settlement summary
- Receivables aging and SBP 120-day realization exposure

### Export Copilot

- Grounded Q&A: live deal data + markdown knowledge corpus in Qdrant
- Seven-pillar **ready-to-ship** radar (inventory, quote, documents, compliance, shipment, payment, and related blockers)
- Commercial buyer-message drafts with a human-in-the-loop gate (nothing is sent automatically)
- Default local Qdrant storage (`backend/qdrant_storage`); optional remote Qdrant via env

### Executive dashboard

- KPI ribbon, pipeline waterfall, Incoterm and SKU profitability
- Destination market view
- JSON executive report download
- USD / PKR toggle in the UI

---

## Architecture

| Layer | Stack |
| --- | --- |
| API | Python 3.11+ · FastAPI · Pydantic v2 · Uvicorn |
| Data | PostgreSQL · SQLAlchemy 2.0 (async / `asyncpg`) · Alembic |
| Auth | JWT (HS256) · bcrypt |
| AI | Hugging Face Inference Router · Qwen 2.5 Coder |
| Vectors | Qdrant (embedded local path or cloud URL) |
| Web | React 19 · Vite · Tailwind CSS 3 · React Router 7 |
| Tests | Pytest · pytest-asyncio · HTTPX |

The Vite dev server proxies `/api` to `http://localhost:8000`.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **PostgreSQL 14+** running locally (or a reachable instance)

Hugging Face keys are optional. Without them, extraction and Copilot chat fall back to deterministic / grounded behaviour rather than live LLM calls.

---

## Quick start

### 1. Database

```sql
CREATE DATABASE exportos;
```

Default connection (override in `.env`):

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/exportos
```

### 2. Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
pip install qdrant-client

copy .env.example .env
# macOS / Linux: cp .env.example .env

alembic upgrade head

python run.py
```

API: [http://localhost:8000](http://localhost:8000)

| Resource | URL |
| --- | --- |
| OpenAPI (dev) | [http://localhost:8000/api/docs](http://localhost:8000/api/docs) |
| ReDoc (dev) | [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc) |
| Health | [http://localhost:8000/api/health](http://localhost:8000/api/health) |

OpenAPI is disabled when `APP_ENV` is not `development`.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

Register a company (creates the organisation and the first `ADMIN` user), then sign in.

---

## Environment

Copy `backend/.env.example` to `backend/.env`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://…`) |
| `SECRET_KEY` | JWT signing secret (change in production) |
| `JWT_SECRET_KEY` | Optional override; falls back to `SECRET_KEY` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default 24 hours) |
| `CORS_ORIGINS` | Comma-separated origins (default `http://localhost:5173`) |
| `APP_ENV` | `development` or `production` |
| `HF_MODEL` | Hugging Face model id |
| `HF_API_URL` | Chat completions endpoint |
| `HF_API_KEY_1` … `HF_API_KEY_5` | Rotating HF tokens |
| `HF_API_KEYS` | Optional comma-separated extra tokens |
| `QDRANT_PATH` | Local storage directory (default `qdrant_storage`) |
| `QDRANT_URL` / `QDRANT_API_KEY` | Use a remote Qdrant instead of local files |
| `QDRANT_COLLECTION_NAME` | Default `exportos_copilot` |
| `DOCS_DATA_DIR` | Knowledge markdown folder (default `data/docs`) |
| `UPLOAD_DIR` | Inquiry artifact uploads |

---

## First Copilot index

After the API is up, an `ADMIN` or `EXPORT_MANAGER` can re-index the regulatory corpus:

```http
POST /api/copilot/sync-docs
Authorization: Bearer <token>
```

Knowledge files live in `backend/data/docs/`:

- Incoterms 2020 rules
- SBP FE Manual Chapter XII
- SBP FE circulars
- TDAP export policy notes
- US CBP and EU REX destination customs notes

Deal records can be synced with `POST /api/copilot/deals/{deal_id}/sync-vector`.

---

## Application map

| Route | Purpose |
| --- | --- |
| `/` | Executive dashboard and analytics |
| `/copilot` | Grounded chat, readiness radar, drafts |
| `/inquiries` | Intake and extraction |
| `/deals` | Costing, documents, compliance, shipment, payment |
| `/products` | SKU catalogue |
| `/inventory` | Stock, reservations, shortfalls |
| `/team` | Users and roles |
| `/login`, `/register` | Auth |

---

## API surface

Mounted at `/api`:

| Area | Prefix / routes |
| --- | --- |
| Health | `GET /health` |
| Auth | `/auth/register`, `/auth/login`, `/auth/me` |
| Users & organisation | `/users`, organisation profile |
| Products & inventory | `/products`, `/inventory` |
| Deals & costing | `/deals` |
| Inquiries | `/inquiries` |
| Extraction | `/extraction` |
| Documents | `/deals/{id}/documents`, consistency check |
| Compliance | `/compliance` |
| Logistics | `/shipments`, `/payments` |
| Copilot | `/copilot` |
| Analytics | `/analytics` |

Use the OpenAPI UI for request and response schemas.

---

## Project layout

```text
ExportOS-/
├── backend/
│   ├── alembic/versions/     # 0001–0008 schema revisions
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── core/             # JWT, tenant scoping, RBAC
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic DTOs
│   │   ├── services/         # Domain logic (costing, inventory, Copilot, …)
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── data/docs/            # Copilot knowledge corpus
│   ├── tests/
│   ├── run.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── components/       # Layout, ProtectedRoute
│       ├── context/          # Auth
│       ├── lib/api.js        # Fetch client + JWT
│       └── pages/
└── README.md
```

---

## Tests

From `backend` with the virtualenv active:

```bash
pytest -v
```

Coverage includes inventory availability, costing and state transitions, documents and consistency, compliance / HS advice, shipments and payments, Copilot retrieval, and executive analytics.

Some Copilot tests expect Qdrant and the docs folder. Install `qdrant-client` before running the full suite.

---

## Production notes

- Replace `SECRET_KEY` (and use `JWT_SECRET_KEY` if you split secrets).
- Set `APP_ENV=production` so `/api/docs` is not public.
- Restrict `CORS_ORIGINS` to the real frontend origin.
- Run PostgreSQL with backups; Alembic is the only supported schema path (`alembic upgrade head`).
- Treat Copilot and HS/SBP output as **advisory**. Confirm with your bank, freight forwarder, and counsel before filing or shipping.

---

## Design boundary

| AI may | Code must |
| --- | --- |
| Parse unstructured buyer text | Compute stock and reservations |
| Draft emails for a human to send | Compute Incoterm totals and margins |
| Retrieve and cite indexed policy text | Enforce deal state transitions |
| Explain a shortfall or blocker | Generate and cross-check documents |

If the model and the database disagree, the database wins.

---

## License

Proprietary / unpublished unless a license file is added to this repository.

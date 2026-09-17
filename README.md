# ExportOS — AI Export Operations Copilot

ExportOS is an AI-assisted export operations platform tailored for small and medium-sized exporters in Pakistan. It centralizes and streamlines the entire export lifecycle into one authoritative record:

$$\text{Buyer Inquiry} \longrightarrow \text{AI Interpretation} \longrightarrow \text{Inventory Check} \longrightarrow \text{Incoterm Costing} \longrightarrow \text{Quotation Approval} \longrightarrow \text{Order Confirmation} \longrightarrow \text{Document Generation} \longrightarrow \text{Shipment \& Payment}$$

ExportOS strictly maintains a **deterministic boundary**: AI handles unstructured natural language interpretation (extracting specs from buyer emails, RFQs, and messages), while critical operations (stock availability, reservation, currency conversions, Incoterm costing, margin calculations, and state transitions) are executed deterministically.

---

## Key Features

- **Multi-Tenant Architecture & RBAC**: Complete tenant isolation for export organisations with role-based access control (`ADMIN`, `EXPORT_MANAGER`, `DOCUMENTATION_OFFICER`, `SALES`, `ACCOUNTS`).
- **Product Catalogue**: Centralized master SKU records with unit of measure, carton capacities, net weights, default Pakistan HS codes, and base factory costs.
- **Deterministic Inventory Engine**: Real-time stock tracking with math: $\text{Available} = \text{Current} - \text{Reserved}$.
- **Inquiry Ingestion & Artifacts**: Multi-channel raw intake (manual copy-paste, file uploads of PDF/Word/Excel, and inbound webhook endpoints) stored with cryptographic SHA-256 integrity hashes.
- **AI Extraction with Qwen 2.5 & Key Rotation**: Uses Hugging Face inference (`Qwen/Qwen2.5-Coder-32B-Instruct`) with automatic key rotation across multiple API tokens on HTTP 429 rate limits, accompanied by field-level confidence scores and verbatim evidence quotes.
- **Inventory Shortfall Resolution**: Instant warehouse lookup upon inquiry extraction with commercial resolution gateways (`[Adjust Quantity to Available]` or `[Mark for Production/Procurement]`).
- **Incoterm Costing & Quotation Engine**: Fixed-point decimal arithmetic supporting Incoterms 2020 (`EXW`, `FCA`, `FOB`, `CFR`, `CIF`, `CPT`, `CIP`, `DAP`, `DDP`), itemized cost breakdowns (freight, packaging, origin THC, insurance, duties), and managerial quote approvals.
- **Deal State Machine & Immutable Audit Log**: Strict legal lifecycle state progression (`INQUIRY` → `QUOTED` → `CONFIRMED` → `IN_PRODUCTION` → `DOCS_READY` → `SHIPPED` → `PAID` → `CLOSED`) with complete audit trails.

---

## Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3.11+ · FastAPI · Pydantic v2 |
| **Database & ORM** | PostgreSQL · SQLAlchemy 2.0 (Async via `asyncpg`) |
| **Migrations** | Alembic |
| **AI / LLM Engine** | Hugging Face Router · Qwen 2.5 with Auto-Rotating Keys |
| **Frontend SPA** | React 18 · Vite · Tailwind CSS v3 · React Router v6 |
| **Testing** | Pytest · Pytest-Asyncio · HTTPX |

---

## Quickstart Guide

### 1. Prerequisites

- **Python 3.11+**
- **Node.js 18+** & **npm**
- **PostgreSQL** running locally

---

### 2. Database Setup

Create the local PostgreSQL database:

```sql
CREATE DATABASE exportos;
```

---

### 3. Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS / Linux:
# source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
# Copy .env.example to .env and adjust DATABASE_URL or Hugging Face keys if needed
copy .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. (Optional) Seed realistic Pakistani export products & inventory
python seed_data.py

# 6. Start the backend development server
python run.py
```

The backend server will run at **`http://localhost:8000`**:
- **Interactive Swagger Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **Alternative ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
- **Healthcheck**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### 4. Frontend Setup

In a separate terminal:

```bash
cd frontend

# 1. Install frontend packages
npm install

# 2. Start the Vite dev server
npm run dev
```

The web application will open at **`http://localhost:5173`**.

---

## Project Structure

```text
ExportOS-/
├── backend/
│   ├── alembic/                  # Database migration scripts
│   │   └── versions/             # Migration revisions (0001 to 0005)
│   ├── app/
│   │   ├── api/                  # API routers (auth, deals, inventory, products, etc.)
│   │   ├── core/                 # Auth dependencies, JWT security & tenant scoping
│   │   ├── models/               # SQLAlchemy declarative domain models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Business services (AI extractor, costing, inventory, state)
│   │   ├── config.py             # Settings & environment validation
│   │   ├── database.py           # Async SQLAlchemy engine session factory
│   │   └── main.py               # FastAPI application factory
│   ├── tests/                    # Pytest unit & integration test suite
│   ├── run.py                    # Server startup script
│   ├── seed_data.py              # Sample product catalogue and inventory seeder
│   └── requirements.txt          # Python backend dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/           # Reusable UI elements (Navbar, Layout, ProtectedRoute)
│   │   ├── context/              # Global state (AuthContext)
│   │   ├── lib/                  # Axios HTTP client with auto-refresh JWT tokens
│   │   ├── pages/                # Page views (Deals, Inquiries, Inventory, Products, Team, Login)
│   │   ├── App.jsx               # React Router configuration
│   │   └── main.jsx              # Application entry point
│   ├── package.json              # Frontend dependencies and scripts
│   ├── tailwind.config.js        # Tailwind styling configuration
│   └── vite.config.js            # Vite bundler & API proxy configuration
│
└── README.md
```

---

## Running Tests

Run the backend test suite:

```bash
cd backend
pytest -v
```

---

## Development Roadmap

- [x] **Phase 0** — Project Foundation, FastAPI Factory, PostgreSQL Engine, Vite + Tailwind Setup
- [x] **Phase 1** — Multi-Tenant Authentication, User Roles & Tenant Isolation
- [x] **Phase 2** — Product Catalogue CRUD & Master SKU Specifications
- [x] **Phase 3** — Deterministic Inventory Engine, Availability Checking & Reservations
- [x] **Phase 4** — Central Deal Model, State Machine Progression & Immutable Audit Logging
- [x] **Phase 5** — Inquiry Multi-Channel Ingestion & Cryptographic Artifact Vault
- [x] **Phase 6** — AI Deal Extraction Engine (Qwen 2.5 with Auto-Rotating API Keys)
- [x] **Phase 7** — AI → Inventory Matching & Interactive Shortfall Resolution
- [x] **Phase 8** — Deterministic Incoterm Costing Engine & Quotation Approvals
- [x] **Phase 9** — Order Confirmation & Automatic Inventory Allocation
- [x] **Phase 10** — Multi-Document Generation (Proforma Invoice, Commercial Invoice, Packing List, CoO)
- [x] **Phase 11** — Cross-Document Consistency Checker (Deterministic Audit Engine)
- [ ] **Phase 12** — Compliance Engine, SBP FX Regulations & HS Code Advisory
- [ ] **Phase 13** — Shipment & Milestone Logistics Tracking
- [ ] **Phase 14** — Payment Reconciliation & Electronic Form-E / Financial Closure
- [ ] **Phase 15** — Executive Dashboard, Profitability Reports & Operational Analytics
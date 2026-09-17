# ExportOS — AI Export Operations Copilot

An AI-assisted export operations platform for small and medium exporters in Pakistan. ExportOS centralizes the entire export deal lifecycle — from buyer inquiry to payment reconciliation — into one authoritative record.

## Tech Stack

| Layer        | Technology                                    |
| ------------ | --------------------------------------------- |
| Backend      | Python · FastAPI · SQLAlchemy · Pydantic      |
| Database     | PostgreSQL (async via asyncpg)                |
| Migrations   | Alembic                                       |
| Frontend     | React · Vite · Tailwind CSS v3 · React Router |
| Auth         | JWT (access + refresh tokens) — Phase 1       |
| Testing      | Pytest · pytest-asyncio · httpx               |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL** installed and running locally

---

## Setup

### 1. Create the database

```sql
-- Connect to PostgreSQL and run:
CREATE DATABASE exportos;
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and update if needed
copy .env.example .env
# (or on macOS/Linux: cp .env.example .env)

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**
- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at **http://localhost:5173**

The Vite dev server proxies `/api` requests to `localhost:8000`, so both servers need to be running.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Project Structure

```
ExportOS-/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app factory
│   │   ├── config.py         # Settings (env vars)
│   │   ├── database.py       # Async SQLAlchemy engine
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # API route handlers
│   │   └── core/             # Security & shared utils
│   ├── alembic/              # Database migrations
│   ├── tests/                # Pytest tests
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page components
│   │   └── lib/              # Utilities (API client, etc.)
│   └── package.json
│
└── README.md
```

---

## Development Phases

- [x] **Phase 0** — Project Foundation
- [ ] **Phase 1** — Authentication & Organisation
- [ ] **Phase 2** — Product Catalogue
- [ ] **Phase 3** — Inventory System
- [ ] **Phase 4** — Deal Management
- [ ] **Phase 5** — Inquiry Ingestion
- [ ] **Phase 6** — AI Extraction
- [ ] **Phase 7** — AI → Inventory Connection
- [ ] **Phase 8** — Quotation & Costing
# ReceiptBrain

An expense tracker that turns receipt photos and bill emails into searchable transactions. I built it to explore a practical question: can an AI-assisted expense tracker save manual entry time without losing the precision needed for financial data?

ReceiptBrain has a React frontend and a FastAPI backend. It extracts receipt details, stores expenses in Supabase, supports manual entries, and shows spending summaries, trends, and alerts. A hybrid search layer combines MiniLM embeddings with merchant, date, category, and amount matching.

> **Project status:** Works locally. Cloud deployment and production authentication are still in progress. Use sample data for public demos, not personal financial records.

## What it does

- **Receipt upload:** Extract merchant, date, amount, category, and line items from JPG/PNG/WEBP receipts using a vision-language model.
- **Manual expenses:** Record a purchase without uploading an image.
- **Gmail import (local):** Read supported bills and order confirmations through Gmail's read-only OAuth scope; deduplicate by message ID.
- **Search:** Find expenses using queries such as `Swiggy in 2025` or `food above 400`.
- **Dashboard and trends:** View monthly spending, categories, transactions, and historical trends.
- **Alerts:** Flag possible duplicates, spikes, and new merchants using explainable rules.
- **AI insights (optional):** Run a CrewAI pipeline with Groq-hosted models for expense interpretation.

The Upload page includes two sample restaurant bills (₹441 and ₹420). **Analyzing a sample currently saves it as a real expense**, so repeated demos can create duplicate entries.

## Screenshots

_Add screenshots of Upload, Dashboard, Search, and Alerts here after your final UI pass._

## Stack

| Part | Technology |
| --- | --- |
| Frontend | React, Vite, React Router, Recharts, CSS |
| API | Python, FastAPI |
| Database | Supabase PostgreSQL + pgvector |
| Embeddings | `all-MiniLM-L6-v2` (384 dimensions) |
| Receipt extraction | Gemini through OpenRouter (configured model) |
| Agent workflow | CrewAI + Groq-hosted Llama models |
| Email import | Gmail API + OAuth 2.0 |

## How it works

```text
Receipt image ──> vision model ──> validation ──┐
Gmail message ──> email parser ──> validation ──┼──> FastAPI ──> Supabase
Manual entry ──────────────────────────────────┘                  │
                                                                 ├──> embeddings / pgvector search
                                                                 ├──> rule-based analytics and alerts
                                                                 └──> optional CrewAI insights
React UI <────────────────────── API endpoints <───────────────────┘
```

The key design choice is to keep financial calculations in code. Models help extract and interpret data; Python and SQL handle totals, filters, and anomaly rules.

## Repository layout

```text
backend/                 FastAPI, OCR, ingestion, analytics, embeddings, Gmail, agents
frontend/src/pages/      Upload, Dashboard, ManualExpense, Trends, Alerts, Search
frontend/public/samples/ Sample receipt images
supabase/migrations/      Database schema and pgvector setup
docs/EXPLAINED.md        Engineering decisions and problems encountered
```

## Run locally

### Requirements

Python 3.11, Node.js/npm, a Supabase project, and the API keys needed for the features you enable.

### 1. Database

Run `supabase/migrations/20261101000000_receiptbrain_v2.sql` in the Supabase SQL Editor. Ensure your current schema also permits `manual` as a receipt source.

### 2. Backend (Windows PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Fill in .env with your own keys and settings
python check_setup.py
uvicorn main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Use the exact variable names shown in `backend/.env.example` and referenced in the code. Do not commit `.env`, OAuth credentials, or access tokens.

### 3. Frontend

In a second terminal:

```powershell
cd frontend
npm install
```

Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env` if required, then run:

```powershell
npm run dev
```

Open http://localhost:5173.

### 4. Optional demo data and Gmail

```powershell
# From backend/ with the virtual environment active
python seed_demo.py
# To remove the seeded sample history later:
python seed_demo.py --clear
```

For Gmail, place your local OAuth client file at `backend/gmail_credentials.json` and run `python gmail_sync.py` to complete the browser authorization. The deployed web OAuth flow has not been implemented.

## API routes used in the app

| Method | Route | Use |
| --- | --- | --- |
| `POST` | `/upload` | Parse and save a receipt image |
| `POST` | `/upload-text` | Parse and save receipt text |
| `POST` | `/expenses/manual` | Add an expense manually |
| `GET` | `/expenses` | List transactions |
| `GET` | `/summary` | Spending summary |
| `GET` | `/expenses/by-month` | Monthly aggregates |
| `GET` | `/query?q=...` | Search expenses |
| `GET` | `/anomalies` | List anomaly flags |
| `GET` | `/insights` | View generated insights |
| `POST` | `/analyze/{expense_id}` | Run agent analysis |
| `POST` | `/embeddings/backfill` | Populate missing embeddings |
| `GET` | `/gmail-sync` | Run local Gmail sync |

Check `/docs` for the live request/response schemas.

## Things I still want to improve

- **Authentication and isolation:** Add Supabase Auth, row-level security, and authorization on every expense endpoint before exposing personal data publicly.
- **Receipt review:** Show editable extracted fields and save only after confirmation. This would also make sample analysis safer.
- **Search:** Move more filtering into PostgreSQL and handle aggregation queries separately from ranked retrieval.
- **Jobs:** Replace in-process background tasks with a durable queue for model-heavy work.
- **Deployment:** Test model memory use on Render or another backend host; deploy the Vite frontend on Vercel. Gmail's current OAuth flow is local-only.
- **Tests:** Add parser fixtures, ingestion tests, and API tests for filtering and authorization.

## Engineering notes

I documented the main tradeoffs, bugs, and fixes in [docs/EXPLAINED.md](docs/EXPLAINED.md).

## Security note

This is a development/portfolio project, **not a production-ready financial service**. Don't expose the existing API with real personal expenses until authentication, per-user access controls, and secret handling have been reviewed. Use synthetic data for a public demo.

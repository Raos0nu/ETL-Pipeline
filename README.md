# ⟡ DataFlow Studio

**Real-Time ETL Pipeline & Analytics Platform**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Pandas](https://img.shields.io/badge/Pandas-2.2-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

DataFlow Studio is a **production-grade, full-stack ETL pipeline** with a real-time analytics dashboard. It ingests raw CSV data, applies configurable validation and transformation rules, persists results to SQLite, and exposes a versioned REST API — all wrapped in a modern React frontend with live pipeline monitoring, data quality scoring, and interactive visualisations.

---

## ✨ Features

| Category | Highlights |
|---|---|
| **Backend Engineering** | Clean Flask REST API · Retry with exponential backoff · Background async job processing (threading) · ETL job history in SQLite · Structured logging · Request-ID tracing · CORS + security headers |
| **ETL Core** | Extract (CSV / JSON / Excel) · Schema validation · Data quality scoring · Duplicate detection · Configurable transformations · Batch processing |
| **Analytics API** | Per-product aggregations · Time-series revenue · Top-N rankings · Data quality reports |
| **React Frontend** | Dashboard with 6 KPI cards · Pipeline Monitor with step visualiser · Interactive Recharts charts · Inline record editing · CSV import/export · Skeleton loaders · Dark mode |
| **DevOps** | Vercel serverless (Python 3.12) · Multi-stage Docker build · docker-compose · `.env` configuration management · Health check endpoint |

---

## 🏗 Architecture

```
dataflow-studio/
├── api/
│   ├── index.py            ← Vercel serverless entry — complete Flask app
│   └── requirements.txt    ← Minimal Vercel deps (Flask, Pandas)
├── backend/
│   ├── core/               ← Extract · Transform · Load modules
│   ├── models/             ← SQLAlchemy models, Pydantic schemas
│   └── utils/              ← Logger, retry decorator
├── frontend/
│   └── src/
│       ├── services/api.js ← Axios client with retry interceptors
│       └── components/     ← Dashboard · Pipeline · DataTable · Analytics · AddDataForm
├── data/sample_sales.csv   ← Seed dataset (50 records)
├── .env.example            ← Environment variable template
├── vercel.json             ← Vercel deployment config
└── Dockerfile              ← Multi-stage build
```

**Data flow:**
```
CSV / Upload
    │
    ▼ Extract (pandas.read_csv + encoding handling)
    │
    ▼ Transform (type coercion · dedup · validation · quality scoring)
    │
    ▼ Load (SQLite via sqlite3 with WAL mode + retry)
    │
    ▼ REST API  →  React Dashboard
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+, Node.js 18+

### 1. Clone & install

```bash
git clone https://github.com/your-username/dataflow-studio.git
cd dataflow-studio

# Python deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Node deps
cd frontend && npm install && cd ..
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — defaults work out of the box for local dev
```

### 3. Run

**Dev (two terminals):**
```bash
# Terminal 1 — API
python api/index.py

# Terminal 2 — React dev server with hot reload
cd frontend && npm start
# Open http://localhost:3000
```

**Production build (single server):**
```bash
cd frontend && npm run build && cd ..
python api/index.py
# Open http://localhost:5000
```

**Docker:**
```bash
docker compose up --build
# Open http://localhost:5000
```

---

## 🌐 Deploy to Vercel

### Option A — Vercel Dashboard (recommended)

1. Push your fork to GitHub.
2. Go to [vercel.com/new](https://vercel.com/new) → import your repo.
3. Vercel reads `vercel.json` automatically. Click **Deploy**.

### Option B — Vercel CLI

```bash
npm i -g vercel
vercel login

vercel          # preview deployment
vercel --prod   # production deployment
```

### Environment variables (set in Vercel dashboard)

| Variable | Example Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `SECRET_KEY` | *(generate: `python -c "import secrets; print(secrets.token_hex(32))"`)* |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |

> **Vercel note:** Vercel's filesystem is read-only except `/tmp`. The API automatically detects `VERCEL=1` and redirects data files and SQLite to `/tmp`.

---

## 📡 API Reference

Base: `http://localhost:5000` · Production: `https://your-app.vercel.app`

### Health

```http
GET  /api/health      → service info + db status
GET  /api/status      → active jobs, recent runs, data file info
```

### Records

```http
GET    /api/data                  → list (page, per_page, product, sort_by, sort_order)
GET    /api/data/:order_id        → single record
POST   /api/data                  → create  { order_id, product, quantity, price }
PUT    /api/data/:order_id        → update  { product?, quantity?, price? }
DELETE /api/data/:order_id        → delete
POST   /api/data/bulk-delete      → { order_ids: [1,2,3] }
POST   /api/data/import           → multipart CSV upload
GET    /api/data/export           → download CSV
```

### Analytics

```http
GET  /api/analytics/overview     → stats + quality report
GET  /api/analytics/products     → per-product aggregations
GET  /api/analytics/timeseries   → daily revenue/orders
GET  /api/analytics/summary      → top-N products (?top=5)
```

### ETL Pipeline

```http
POST /api/etl/run                 → { mode: "sync"|"async", triggered_by: "..." }
GET  /api/etl/status/:job_id      → poll async job
GET  /api/etl/history             → last N jobs (?limit=20)
```

**Typical ETL run response:**
```json
{
  "success": true,
  "data": {
    "job_id": "job_20250101_120000_abc123",
    "status": "completed",
    "records_extracted": 50,
    "records_transformed": 48,
    "records_loaded": 48,
    "quality_score": 0.96,
    "quality_percentage": 96.0,
    "duration_seconds": 0.142
  }
}
```

---

## 🔧 Configuration

All settings via environment variables (see `.env.example`):

```ini
ENVIRONMENT=development        # development | production
DEBUG=true
PORT=5000
SECRET_KEY=change-me
CORS_ORIGINS=http://localhost:3000
DATABASE_URL=sqlite:///dataflow.db
DATA_FILE=data/sample_sales.csv
LOG_LEVEL=INFO
ETL_MAX_RETRIES=3
ETL_RETRY_DELAY=0.5
```

---

## 📊 Sample Dataset

Shipped in `data/sample_sales.csv` — 50 orders across 5 product categories. To load your own data, use the **Import CSV** button on the Data Table page.

**Required CSV columns:**

| Column | Type | Description |
|---|---|---|
| `order_id` | integer | Unique positive identifier |
| `product` | string | Product name or SKU |
| `quantity` | integer | Units sold |
| `price` | float | Unit price (USD) |

*Optional:* `category`, `created_at`

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| API Server | Python 3.12 · Flask 3.0 · flask-cors |
| Data Processing | Pandas 2.2 · NumPy |
| Database | SQLite (WAL mode) · SQLAlchemy |
| Validation | Pydantic v2 |
| Frontend | React 18 · Recharts · react-hot-toast |
| Deployment | Vercel Serverless Functions (Python runtime) |
| Containers | Docker · Docker Compose |

---

## 🗺 Roadmap

- [ ] PostgreSQL / PlanetScale for persistent production storage
- [ ] Cron-triggered scheduled ETL jobs
- [ ] Multi-source: REST APIs, Amazon S3, Google Sheets
- [ ] JWT-based authentication
- [ ] Prometheus `/metrics` endpoint
- [ ] Row-level audit trail

---

## 👤 Author

**Sonu Yadav** — Final-year CSE student · Backend & Data Engineering

📧 sonuyadav97297@gmail.com


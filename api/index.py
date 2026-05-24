"""
DataFlow Studio v2.0 — Production-Ready ETL Pipeline API
=========================================================
Flask serverless function for Vercel deployment.
All backend logic lives here for zero-dependency serverless execution.

Features:
  - Clean architecture with route organisation via local functions
  - Retry decorator with exponential backoff
  - Background (async) ETL job processing via threading
  - Persistent ETL job history in SQLite
  - Data quality scoring and reporting
  - Request middleware (request-id, timing headers)
  - Structured JSON-style logging
  - Comprehensive input validation
  - CORS + security headers
"""

import sys
import os
import shutil
import time
import uuid
import threading
import io
import csv
import logging
import json
from datetime import datetime
from functools import wraps
from collections import deque
from typing import Dict, Any, Optional, List, Tuple

# ---------------------------------------------------------------------------
# PATH BOOTSTRAP  (makes parent-dir imports work on Vercel and locally)
# ---------------------------------------------------------------------------
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from flask import Flask, jsonify, request, g, send_from_directory
from flask_cors import CORS
import pandas as pd
import sqlite3

# ---------------------------------------------------------------------------
# ENVIRONMENT / CONFIGURATION
# ---------------------------------------------------------------------------
IS_VERCEL      = bool(os.getenv("VERCEL"))
ENV            = os.getenv("ENVIRONMENT", "development")
VERSION        = "2.0.0"
SERVICE_NAME   = "DataFlow Studio"
MAX_PER_PAGE   = 10_000
MAX_IMPORT     = 50_000
MAX_BULK_DEL   = 1_000
JOB_HIST_MEM   = 100   # in-memory deque limit

# File paths — Vercel's filesystem is read-only except /tmp
_TMP            = "/tmp" if IS_VERCEL else parent_dir
DATA_ORIG       = os.path.join(parent_dir, "data", "sample_sales.csv")
DATA_FILE       = os.path.join(_TMP, "sample_sales.csv")    if IS_VERCEL else DATA_ORIG
DB_FILE         = os.path.join(_TMP, "dataflow.db")

REQUIRED_COLS   = ["order_id", "product", "quantity", "price"]

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("dataflow")

# ---------------------------------------------------------------------------
# IN-MEMORY JOB STORE  (thread-safe)
# ---------------------------------------------------------------------------
_job_history: deque        = deque(maxlen=JOB_HIST_MEM)
_job_history_lock          = threading.Lock()
_active_jobs: Dict[str, Dict] = {}
_active_jobs_lock          = threading.Lock()

# ===========================================================================
# RETRY DECORATOR
# ===========================================================================
def with_retry(max_attempts: int = 3, delay: float = 0.5,
               exceptions: tuple = (Exception,)):
    """Exponential-backoff retry decorator."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_err = exc
                    if attempt < max_attempts:
                        wait = delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Retry %d/%d for %s — %s (backoff %.1fs)",
                            attempt, max_attempts, fn.__name__, exc, wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "All %d attempts exhausted for %s: %s",
                            max_attempts, fn.__name__, exc,
                        )
            raise last_err
        return wrapper
    return decorator

# ===========================================================================
# DATA-FILE HELPERS
# ===========================================================================
def ensure_data_file() -> None:
    """Guarantee DATA_FILE exists, copying from original if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(DATA_FILE)), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        if os.path.exists(DATA_ORIG) and DATA_FILE != DATA_ORIG:
            shutil.copy2(DATA_ORIG, DATA_FILE)
            logger.info("Copied data file → %s", DATA_FILE)
        else:
            pd.DataFrame(columns=REQUIRED_COLS).to_csv(DATA_FILE, index=False)
            logger.info("Created empty data file at %s", DATA_FILE)


@with_retry(max_attempts=3, delay=0.3, exceptions=(sqlite3.OperationalError, IOError))
def _db_connect() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all required tables on first run."""
    try:
        db_dir = os.path.dirname(os.path.abspath(DB_FILE))
        os.makedirs(db_dir, exist_ok=True)
        conn = _db_connect()
        cur  = conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS sales (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER UNIQUE NOT NULL,
            product     TEXT    NOT NULL,
            category    TEXT    DEFAULT 'General',
            quantity    INTEGER NOT NULL,
            price       REAL    NOT NULL,
            total_price REAL    NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS etl_jobs (
            id                  TEXT PRIMARY KEY,
            status              TEXT NOT NULL,
            triggered_by        TEXT DEFAULT 'manual',
            started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at        TIMESTAMP,
            records_extracted   INTEGER DEFAULT 0,
            records_transformed INTEGER DEFAULT 0,
            records_loaded      INTEGER DEFAULT 0,
            records_valid       INTEGER DEFAULT 0,
            records_invalid     INTEGER DEFAULT 0,
            quality_score       REAL    DEFAULT 0,
            duration_seconds    REAL    DEFAULT 0,
            error_message       TEXT
        );
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialised at %s", DB_FILE)
    except Exception as exc:
        logger.error("DB init failed: %s", exc, exc_info=True)

# ===========================================================================
# CORE ETL ENGINE
# ===========================================================================
def _extract(file_path: str) -> pd.DataFrame:
    """Read CSV; return empty DataFrame on missing file."""
    if not os.path.exists(file_path):
        logger.warning("Source file not found: %s — returning empty DataFrame", file_path)
        return pd.DataFrame(columns=REQUIRED_COLS)
    df = pd.read_csv(
        file_path,
        encoding="utf-8",
        on_bad_lines="skip",
        dtype={"order_id": "object", "product": "str",
               "quantity": "object", "price": "object"},
    )
    logger.info("Extracted %d rows from %s", len(df), file_path)
    return df


def _transform(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Clean, validate and enrich the DataFrame.
    Returns (clean_df, quality_report_dict).
    """
    if df.empty:
        report = {"total_rows": 0, "valid_rows": 0, "invalid_rows": 0,
                  "duplicates_removed": 0, "quality_score": 0.0,
                  "quality_percentage": 0.0, "issues": []}
        return df, report

    original = len(df)
    issues: List[str] = []
    df = df.copy()

    # Coerce numeric types
    df["order_id"]  = pd.to_numeric(df["order_id"],  errors="coerce")
    df["quantity"]  = pd.to_numeric(df["quantity"],  errors="coerce")
    df["price"]     = pd.to_numeric(df["price"],     errors="coerce")

    # Remove duplicates
    dups = int(df.duplicated(subset=["order_id"], keep="first").sum())
    if dups:
        df = df.drop_duplicates(subset=["order_id"], keep="first")
        issues.append(f"Removed {dups} duplicate order_id(s)")

    # Validity mask
    valid_mask = (
        df["order_id"].notna()  & (df["order_id"]  > 0) &
        df["product"].notna()   & (df["product"].astype(str).str.strip() != "") &
        df["quantity"].notna()  & (df["quantity"]  > 0) &
        df["price"].notna()     & (df["price"]     > 0)
    )
    invalid = int((~valid_mask).sum())
    if invalid:
        df = df[valid_mask].copy()
        issues.append(f"Dropped {invalid} row(s) with invalid/missing data")

    # Type normalisation
    df["order_id"]    = df["order_id"].astype(int)
    df["quantity"]    = df["quantity"].astype(int)
    df["price"]       = df["price"].round(2)
    df["total_price"] = (df["quantity"] * df["price"]).round(2)
    df["product"]     = df["product"].astype(str).str.strip()

    if "category" not in df.columns:
        df["category"] = "General"
    if "created_at" not in df.columns:
        df["created_at"] = datetime.utcnow().isoformat()

    quality  = len(df) / original if original else 0.0
    report = {
        "total_rows":          original,
        "valid_rows":          len(df),
        "invalid_rows":        invalid + dups,
        "duplicates_removed":  dups,
        "quality_score":       round(quality, 3),
        "quality_percentage":  round(quality * 100, 1),
        "issues":              issues,
    }
    logger.info(
        "Transform: %d → %d rows  |  quality %.1f%%",
        original, len(df), quality * 100,
    )
    return df, report


@with_retry(max_attempts=3, delay=0.5, exceptions=(sqlite3.OperationalError,))
def _load(df: pd.DataFrame, mode: str = "replace") -> Dict[str, Any]:
    """Persist DataFrame to the sales table."""
    conn = _db_connect()
    cur  = conn.cursor()
    loaded = 0
    try:
        if mode == "replace":
            cur.execute("DELETE FROM sales")

        for _, row in df.iterrows():
            try:
                cur.execute(
                    """INSERT OR REPLACE INTO sales
                       (order_id, product, category, quantity, price, total_price, updated_at)
                       VALUES (?,?,?,?,?,?, CURRENT_TIMESTAMP)""",
                    (int(row["order_id"]), str(row["product"]),
                     str(row.get("category", "General")),
                     int(row["quantity"]),  float(row["price"]),
                     float(row["total_price"])),
                )
                loaded += 1
            except Exception as row_err:
                logger.warning("Skipped row %s: %s", row.get("order_id"), row_err)

        conn.commit()
        logger.info("Loaded %d records (mode=%s)", loaded, mode)
        return {"records_loaded": loaded, "mode": mode, "total_processed": loaded}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run_pipeline(source: str, job_id: str,
                  triggered_by: str = "manual") -> Dict[str, Any]:
    """Orchestrate extract → transform → load and record the job."""
    t0 = time.time()
    _set_job(job_id, "running", triggered_by=triggered_by)

    try:
        ensure_data_file()
        raw       = _extract(source)
        clean, qr = _transform(raw)
        lr        = _load(clean, mode="replace")

        duration = round(time.time() - t0, 3)
        result = {
            "job_id":              job_id,
            "status":              "completed",
            "records_extracted":   len(raw),
            "records_transformed": len(clean),
            "records_loaded":      lr["records_loaded"],
            "records_valid":       qr["valid_rows"],
            "records_invalid":     qr["invalid_rows"],
            "quality_score":       qr["quality_score"],
            "quality_percentage":  qr["quality_percentage"],
            "duration_seconds":    duration,
            "quality_report":      qr,
            "completed_at":        datetime.utcnow().isoformat(),
            "triggered_by":        triggered_by,
        }
        _set_job(job_id, "completed", result=result)
        _persist_job(job_id, "completed", result)
        logger.info("Pipeline job %s completed in %.2fs", job_id, duration)
        return result

    except Exception as exc:
        duration = round(time.time() - t0, 3)
        err_result = {
            "job_id":           job_id,
            "status":           "failed",
            "error":            str(exc),
            "duration_seconds": duration,
            "failed_at":        datetime.utcnow().isoformat(),
            "triggered_by":     triggered_by,
        }
        _set_job(job_id, "failed", result=err_result)
        _persist_job(job_id, "failed", err_result, error=str(exc))
        logger.error("Pipeline job %s failed: %s", job_id, exc, exc_info=True)
        raise

# ---------------------------------------------------------------------------
# Job-state helpers
# ---------------------------------------------------------------------------
def _set_job(job_id: str, status: str,
             triggered_by: str = "manual", result: Dict = None) -> None:
    with _active_jobs_lock:
        if job_id not in _active_jobs:
            _active_jobs[job_id] = {
                "job_id":       job_id,
                "status":       status,
                "started_at":   datetime.utcnow().isoformat(),
                "triggered_by": triggered_by,
            }
        else:
            _active_jobs[job_id]["status"] = status
            if result:
                _active_jobs[job_id].update(result)

    if status in ("completed", "failed"):
        with _job_history_lock:
            _job_history.appendleft(dict(_active_jobs.get(job_id, {})))
        with _active_jobs_lock:
            _active_jobs.pop(job_id, None)


def _persist_job(job_id: str, status: str,
                 result: Dict, error: str = None) -> None:
    try:
        conn = _db_connect()
        conn.execute(
            """INSERT OR REPLACE INTO etl_jobs
               (id, status, triggered_by, completed_at,
                records_extracted, records_transformed, records_loaded,
                records_valid, records_invalid, quality_score,
                duration_seconds, error_message)
               VALUES (?,?,?, CURRENT_TIMESTAMP, ?,?,?,?,?,?,?,?)""",
            (job_id, status, result.get("triggered_by","manual"),
             result.get("records_extracted",   0),
             result.get("records_transformed", 0),
             result.get("records_loaded",      0),
             result.get("records_valid",       0),
             result.get("records_invalid",     0),
             result.get("quality_score",       0),
             result.get("duration_seconds",    0),
             error),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Failed to persist job %s to DB: %s", job_id, exc)

# ===========================================================================
# RESPONSE HELPERS
# ===========================================================================
def ok(data=None, message: str = None, code: int = 200, **extras):
    body = {"success": True, "timestamp": datetime.utcnow().isoformat()}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    body.update(extras)
    return jsonify(body), code


def err(message: str, code: int = 400, details: str = None):
    body = {"success": False, "error": message,
            "timestamp": datetime.utcnow().isoformat()}
    if details:
        body["details"] = details
    return jsonify(body), code

# ===========================================================================
# INPUT VALIDATION
# ===========================================================================
def _validate_record(data: dict) -> Tuple[Optional[dict], Optional[str]]:
    if not data:
        return None, "Request body is required"
    for f in REQUIRED_COLS:
        if f not in data:
            return None, f"Missing required field: '{f}'"
    try:
        order_id = int(data["order_id"])
        assert order_id > 0
    except (ValueError, TypeError, AssertionError):
        return None, "order_id must be a positive integer"
    product = str(data["product"]).strip()
    if not product or len(product) > 200:
        return None, "product must be a non-empty string (max 200 chars)"
    try:
        qty = int(data["quantity"])
        assert 0 < qty <= 999_999
    except (ValueError, TypeError, AssertionError):
        return None, "quantity must be an integer between 1 and 999,999"
    try:
        price = round(float(data["price"]), 2)
        assert 0 < price <= 9_999_999
    except (ValueError, TypeError, AssertionError):
        return None, "price must be a positive number (max 9,999,999)"
    return {"order_id": order_id, "product": product,
            "quantity": qty, "price": price}, None


def _stats(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"total_orders": 0, "total_revenue": 0.0,
                "average_order_value": 0.0, "total_items_sold": 0,
                "unique_products": 0, "highest_value_order": 0.0}
    return {
        "total_orders":         len(df),
        "total_revenue":        round(float(df["total_price"].sum()),  2),
        "average_order_value":  round(float(df["total_price"].mean()), 2),
        "total_items_sold":     int(df["quantity"].sum()),
        "unique_products":      int(df["product"].nunique()),
        "highest_value_order":  round(float(df["total_price"].max()),  2),
    }


def _new_job_id() -> str:
    return f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def _db_fetch_df() -> pd.DataFrame:
    """Read all sales records from SQLite as a DataFrame."""
    _EMPTY = pd.DataFrame(columns=[
        "order_id","product","category","quantity","price","total_price","created_at","updated_at"
    ])
    try:
        conn = _db_connect()
        df   = pd.read_sql_query("SELECT * FROM sales ORDER BY order_id", conn)
        conn.close()
        return df if not df.empty else _EMPTY
    except Exception as exc:
        logger.warning("DB fetch failed: %s", exc)
        return _EMPTY


def _last_quality_report() -> Dict[str, Any]:
    """Return quality metrics from the most recent completed ETL job."""
    try:
        conn = _db_connect()
        row  = conn.execute(
            "SELECT * FROM etl_jobs WHERE status='completed' ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            # No ETL job yet — derive from current row count
            count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
            conn.close()
            return {"total_rows": count, "valid_rows": count, "invalid_rows": 0,
                    "quality_score": 1.0 if count else 0.0,
                    "quality_percentage": 100.0 if count else 0.0, "issues": []}
        conn.close()
        r     = dict(row)
        score = r.get("quality_score", 1.0) or 1.0
        return {
            "total_rows":         r.get("records_extracted",   0),
            "valid_rows":         r.get("records_valid",       0),
            "invalid_rows":       r.get("records_invalid",     0),
            "quality_score":      score,
            "quality_percentage": round(score * 100, 1),
            "issues":             [],
        }
    except Exception as exc:
        logger.warning("_last_quality_report failed: %s", exc)
        return {"total_rows": 0, "valid_rows": 0, "invalid_rows": 0,
                "quality_score": 0.0, "quality_percentage": 0.0, "issues": []}

# ===========================================================================
# FLASK APP FACTORY
# ===========================================================================
def create_app() -> Flask:
    static_folder = os.path.join(parent_dir, "frontend", "build")
    app = Flask(
        __name__,
        static_folder=static_folder if os.path.isdir(static_folder) else None,
        static_url_path="",
    )
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

    # ── CORS ─────────────────────────────────────────────────────────────────
    origins = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS(app, resources={r"/api/*": {
        "origins": origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
    }})

    # ── MIDDLEWARE ────────────────────────────────────────────────────────────
    @app.before_request
    def _before():
        g.req_id    = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
        g.t0        = time.time()
        logger.info("[%s] ▶  %s %s", g.req_id, request.method, request.path)

    @app.after_request
    def _after(resp):
        ms = (time.time() - g.t0) * 1000
        resp.headers.update({
            "X-Request-ID":    g.req_id,
            "X-Response-Time": f"{ms:.2f}ms",
            "X-Service":       SERVICE_NAME,
            "X-Version":       VERSION,
            "X-Content-Type-Options": "nosniff",
        })
        logger.info("[%s] ◀  %s  %.0fms", g.req_id, resp.status_code, ms)
        return resp

    # ── ROUTES ────────────────────────────────────────────────────────────────
    _register_routes(app)

    # ── ERROR HANDLERS ────────────────────────────────────────────────────────
    @app.errorhandler(400)
    def _400(_): return err("Bad request", 400)

    @app.errorhandler(404)
    def _404(e):
        if request.path.startswith("/api/"):
            return err(f"Endpoint '{request.path}' not found", 404)
        if app.static_folder and os.path.isfile(
                os.path.join(app.static_folder, "index.html")):
            return send_from_directory(app.static_folder, "index.html")
        return err("Not found", 404)

    @app.errorhandler(405)
    def _405(_):
        return err(f"Method {request.method} not allowed", 405)

    @app.errorhandler(413)
    def _413(_): return err("File too large — maximum upload is 10 MB", 413)

    @app.errorhandler(500)
    def _500(e):
        logger.error("Unhandled 500: %s", e, exc_info=True)
        return err("Internal server error. Please try again.", 500)

    return app


# ===========================================================================
# ROUTE REGISTRATION
# ===========================================================================
def _register_routes(app: Flask) -> None:

    # ── Health & Status ───────────────────────────────────────────────────────

    @app.route("/api/health")
    def health():
        db_ok = "healthy"
        try:
            c = _db_connect(); c.execute("SELECT 1"); c.close()
        except Exception:
            db_ok = "degraded"
        return ok({
            "status":      "healthy",
            "version":     VERSION,
            "service":     SERVICE_NAME,
            "environment": ENV,
            "database":    db_ok,
        })

    @app.route("/api/status")
    def status():
        ensure_data_file()
        size = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
        with _active_jobs_lock:
            active = list(_active_jobs.values())
        with _job_history_lock:
            recent = list(_job_history)[:10]
        return ok({
            "service": SERVICE_NAME,
            "version": VERSION,
            "data_file": {
                "name":       os.path.basename(DATA_FILE),
                "size_bytes": size,
                "exists":     os.path.exists(DATA_FILE),
            },
            "active_jobs": active,
            "recent_jobs": recent,
        })

    # ── Data CRUD ─────────────────────────────────────────────────────────────

    @app.route("/api/data", methods=["GET"])
    def get_data():
        try:
            df = _db_fetch_df()
            qr = _last_quality_report()

            # Filters
            prod_q = request.args.get("product", "").strip()
            if prod_q:
                df = df[df["product"].str.lower().str.contains(prod_q.lower(), na=False)]

            s_date = request.args.get("start_date")
            e_date = request.args.get("end_date")
            if (s_date or e_date) and "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
                if s_date: df = df[df["created_at"] >= pd.to_datetime(s_date)]
                if e_date: df = df[df["created_at"] <= pd.to_datetime(e_date)]

            # Sort
            sort_by  = request.args.get("sort_by", "order_id")
            sort_asc = request.args.get("sort_order", "asc") == "asc"
            if sort_by in df.columns:
                df = df.sort_values(sort_by, ascending=sort_asc)

            # Paginate
            page     = max(1, int(request.args.get("page", 1)))
            per_page = min(MAX_PER_PAGE, max(1, int(request.args.get("per_page", 50))))
            total    = len(df)
            pages    = max(1, (total + per_page - 1) // per_page)
            chunk    = df.iloc[(page - 1) * per_page: page * per_page].copy()
            chunk    = chunk.where(pd.notna(chunk), None)

            return ok(
                data=chunk.to_dict("records"),
                stats=_stats(df),
                quality_report=qr,
                pagination={"page": page, "per_page": per_page,
                            "total_records": total, "total_pages": pages},
            )
        except Exception as exc:
            logger.error("GET /api/data: %s", exc, exc_info=True)
            return err(str(exc), 500)

    @app.route("/api/data/<int:oid>", methods=["GET"])
    def get_record(oid):
        try:
            conn = _db_connect()
            row  = conn.execute("SELECT * FROM sales WHERE order_id=?", (oid,)).fetchone()
            conn.close()
            if not row:
                return err(f"Order #{oid} not found", 404)
            return ok(data=dict(row))
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/data", methods=["POST"])
    def add_record():
        try:
            cleaned, e = _validate_record(request.json)
            if e: return err(e, 400)
            total_price = round(cleaned["quantity"] * cleaned["price"], 2)
            conn = _db_connect()
            exists = conn.execute(
                "SELECT 1 FROM sales WHERE order_id=?", (cleaned["order_id"],)
            ).fetchone()
            if exists:
                conn.close()
                return err(f"Order #{cleaned['order_id']} already exists. Use PUT to update.", 409)
            conn.execute(
                """INSERT INTO sales (order_id, product, category, quantity, price, total_price)
                   VALUES (?,?,?,?,?,?)""",
                (cleaned["order_id"], cleaned["product"], "General",
                 cleaned["quantity"], cleaned["price"], total_price),
            )
            conn.commit()
            conn.close()
            payload = {**cleaned, "total_price": total_price}
            return ok(data=payload,
                      message=f"Order #{cleaned['order_id']} created successfully",
                      code=201)
        except Exception as exc:
            logger.error("POST /api/data: %s", exc, exc_info=True)
            return err(str(exc), 500)

    @app.route("/api/data/<int:oid>", methods=["PUT"])
    def update_record(oid):
        try:
            data = request.json or {}
            conn = _db_connect()
            row  = conn.execute("SELECT * FROM sales WHERE order_id=?", (oid,)).fetchone()
            if not row:
                conn.close()
                return err(f"Order #{oid} not found", 404)
            rec = dict(row)
            if "product" in data:
                p = str(data["product"]).strip()
                if not p: conn.close(); return err("product cannot be empty", 400)
                rec["product"] = p
            if "quantity" in data:
                try:
                    q = int(data["quantity"]); assert q > 0
                    rec["quantity"] = q
                except (ValueError, AssertionError):
                    conn.close(); return err("quantity must be a positive integer", 400)
            if "price" in data:
                try:
                    pr = round(float(data["price"]), 2); assert pr > 0
                    rec["price"] = pr
                except (ValueError, AssertionError):
                    conn.close(); return err("price must be a positive number", 400)
            rec["total_price"] = round(rec["quantity"] * rec["price"], 2)
            conn.execute(
                """UPDATE sales SET product=?, quantity=?, price=?, total_price=?,
                   updated_at=CURRENT_TIMESTAMP WHERE order_id=?""",
                (rec["product"], rec["quantity"], rec["price"], rec["total_price"], oid),
            )
            conn.commit()
            conn.close()
            return ok(message=f"Order #{oid} updated successfully")
        except Exception as exc:
            logger.error("PUT /api/data/%d: %s", oid, exc, exc_info=True)
            return err(str(exc), 500)

    @app.route("/api/data/<int:oid>", methods=["DELETE"])
    def delete_record(oid):
        try:
            conn = _db_connect()
            exists = conn.execute("SELECT 1 FROM sales WHERE order_id=?", (oid,)).fetchone()
            if not exists:
                conn.close()
                return err(f"Order #{oid} not found", 404)
            conn.execute("DELETE FROM sales WHERE order_id=?", (oid,))
            conn.commit()
            conn.close()
            return ok(message=f"Order #{oid} deleted successfully")
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/data/bulk-delete", methods=["POST"])
    def bulk_delete():
        try:
            order_ids = (request.json or {}).get("order_ids", [])
            if not order_ids:
                return err("order_ids array is required", 400)
            if len(order_ids) > MAX_BULK_DEL:
                return err(f"Cannot delete more than {MAX_BULK_DEL} records at once", 400)
            conn = _db_connect()
            placeholders = ",".join("?" * len(order_ids))
            cur = conn.execute(
                f"DELETE FROM sales WHERE order_id IN ({placeholders})", order_ids
            )
            deleted = cur.rowcount
            conn.commit()
            conn.close()
            return ok(message=f"{deleted} record(s) deleted successfully",
                      deleted_count=deleted)
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/data/import", methods=["POST"])
    def import_csv():
        try:
            if "file" not in request.files:
                return err("No file provided. Send CSV as multipart/form-data with key 'file'", 400)
            f = request.files["file"]
            if not f.filename:
                return err("No file selected", 400)
            if not f.filename.lower().endswith(".csv"):
                return err("Only .csv files are accepted", 400)

            content = f.read().decode("utf-8", errors="replace")
            reader  = csv.DictReader(io.StringIO(content))
            rows, skipped = [], 0
            for i, row in enumerate(reader):
                if i >= MAX_IMPORT: break
                cleaned, e = _validate_record(row)
                if e: skipped += 1; continue
                rows.append(cleaned)

            if not rows:
                return err(
                    "No valid rows found. CSV must have columns: order_id, product, quantity, price",
                    400,
                )
            conn = _db_connect()
            inserted = 0
            for r in rows:
                total_price = round(r["quantity"] * r["price"], 2)
                try:
                    conn.execute(
                        """INSERT OR REPLACE INTO sales
                           (order_id, product, category, quantity, price, total_price,
                            updated_at)
                           VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                        (r["order_id"], r["product"], "General",
                         r["quantity"], r["price"], total_price),
                    )
                    inserted += 1
                except Exception as row_err:
                    skipped += 1
                    logger.warning("Import skipped row %s: %s", r.get("order_id"), row_err)
            conn.commit()
            conn.close()
            return ok(
                message=f"{inserted} record(s) imported ({skipped} skipped)",
                imported_count=inserted,
                skipped_count=skipped,
                code=201,
            )
        except Exception as exc:
            logger.error("CSV import error: %s", exc, exc_info=True)
            return err(str(exc), 500)

    # ── Analytics ─────────────────────────────────────────────────────────────

    @app.route("/api/analytics/overview")
    def analytics_overview():
        try:
            df = _db_fetch_df()
            qr = _last_quality_report()
            return ok(data={**_stats(df), "quality_report": qr})
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/analytics/products")
    def analytics_products():
        try:
            df = _db_fetch_df()
            if df.empty:
                return ok(data=[])
            grp = (
                df.groupby("product")
                  .agg(total_quantity=  ("quantity",    "sum"),
                       total_revenue=   ("total_price", "sum"),
                       order_count=     ("order_id",    "count"),
                       avg_price=       ("price",       "mean"),
                       avg_order_value= ("total_price", "mean"))
                  .reset_index()
                  .sort_values("total_revenue", ascending=False)
            )
            for col in ("total_revenue", "avg_price", "avg_order_value"):
                grp[col] = grp[col].round(2)
            return ok(data=grp.to_dict("records"))
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/analytics/timeseries")
    def analytics_timeseries():
        try:
            df = _db_fetch_df()
            if df.empty:
                return ok(data=[])
            if "created_at" not in df.columns or df["created_at"].isna().all():
                df["created_at"] = (
                    pd.to_datetime("2024-01-01")
                    + pd.to_timedelta(df["order_id"].astype(int), unit="D")
                )
            else:
                df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
                df = df.dropna(subset=["created_at"])
            df["date"] = df["created_at"].dt.date
            daily = (
                df.groupby("date")
                  .agg(revenue= ("total_price", "sum"),
                       orders=  ("order_id",    "count"),
                       quantity= ("quantity",   "sum"))
                  .reset_index()
            )
            daily["date"]    = daily["date"].astype(str)
            daily["revenue"] = daily["revenue"].round(2)
            return ok(data=daily.to_dict("records"))
        except Exception as exc:
            return err(str(exc), 500)

    @app.route("/api/analytics/summary")
    def analytics_summary():
        try:
            df  = _db_fetch_df()
            qr  = _last_quality_report()
            if df.empty:
                return ok(data={"top_products": [], "stats": _stats(df),
                                "quality_report": qr})
            top_n = min(10, int(request.args.get("top", 5)))
            top = (
                df.groupby("product")
                  .agg(revenue=("total_price", "sum"),
                       units=  ("quantity",    "sum"))
                  .reset_index()
                  .sort_values("revenue", ascending=False)
                  .head(top_n)
            )
            top["revenue"] = top["revenue"].round(2)
            return ok(data={"top_products": top.to_dict("records"),
                            "stats":        _stats(df),
                            "quality_report": qr})
        except Exception as exc:
            return err(str(exc), 500)

    # ── ETL Pipeline control ──────────────────────────────────────────────────

    @app.route("/api/etl/run", methods=["POST"])
    def etl_run():
        try:
            body         = request.json or {}
            mode         = body.get("mode", "sync")          # "sync" | "async"
            triggered_by = body.get("triggered_by", "dashboard")
            job_id       = _new_job_id()

            if mode == "async":
                _set_job(job_id, "queued", triggered_by=triggered_by)

                def _bg():
                    try:
                        _run_pipeline(DATA_FILE, job_id, triggered_by)
                    except Exception as exc:
                        logger.error("Async job %s error: %s", job_id, exc)

                threading.Thread(target=_bg, daemon=True).start()
                return ok(
                    data={"job_id": job_id, "status": "queued", "mode": "async"},
                    message="ETL job queued for background processing",
                    code=202,
                )

            # Synchronous (default)
            result = _run_pipeline(DATA_FILE, job_id, triggered_by)
            return ok(data=result, message="ETL pipeline completed successfully")

        except Exception as exc:
            logger.error("ETL run error: %s", exc, exc_info=True)
            return err(str(exc), 500)

    @app.route("/api/etl/status/<job_id>")
    def etl_status(job_id):
        with _active_jobs_lock:
            if job_id in _active_jobs:
                return ok(data=_active_jobs[job_id])
        with _job_history_lock:
            for j in _job_history:
                if j.get("job_id") == job_id:
                    return ok(data=j)
        return err(f"Job '{job_id}' not found", 404)

    @app.route("/api/etl/history")
    def etl_history():
        try:
            limit = min(50, int(request.args.get("limit", 20)))
            conn  = _db_connect()
            rows  = conn.execute(
                "SELECT * FROM etl_jobs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return ok(data=[dict(r) for r in rows])
        except Exception:
            with _job_history_lock:
                return ok(data=list(_job_history)[:20])

    # ── Data export ───────────────────────────────────────────────────────────

    @app.route("/api/data/export")
    def export_csv():
        try:
            from flask import Response
            df      = _db_fetch_df()
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            return Response(
                csv_buf.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition":
                         "attachment; filename=dataflow_export.csv"},
            )
        except Exception as exc:
            return err(str(exc), 500)

    # ── Static frontend catch-all ─────────────────────────────────────────────

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        sf = app.static_folder
        if sf:
            full = os.path.join(sf, path)
            if path and os.path.isfile(full):
                return send_from_directory(sf, path)
            idx = os.path.join(sf, "index.html")
            if os.path.isfile(idx):
                return send_from_directory(sf, "index.html")
        return ok({"service": SERVICE_NAME, "version": VERSION,
                   "docs": "/api/health"})


# ===========================================================================
# APPLICATION BOOTSTRAP
# ===========================================================================
app = create_app()

try:
    ensure_data_file()
    init_db()
    # Auto-seed: populate the DB from CSV if it's empty on first launch
    _conn = _db_connect()
    _count = _conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    _conn.close()
    if _count == 0 and os.path.exists(DATA_FILE):
        logger.info("DB is empty — running initial ETL seed from %s", DATA_FILE)
        _run_pipeline(DATA_FILE, _new_job_id(), triggered_by="startup")
except Exception as _boot_err:
    logger.error("Startup init error: %s", _boot_err)

# ---------------------------------------------------------------------------
# Local dev entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    print(f"""
╔══════════════════════════════════════════════╗
║        DataFlow Studio  v{VERSION}             ║
║   Real-Time ETL Pipeline & Analytics         ║
╚══════════════════════════════════════════════╝
  Dashboard   →  http://localhost:{port}
  API Health  →  http://localhost:{port}/api/health
  ETL Status  →  http://localhost:{port}/api/status
  Environment →  {ENV}
""")
    app.run(debug=debug, host="0.0.0.0", port=port)

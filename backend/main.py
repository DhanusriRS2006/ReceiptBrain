"""
main.py - FastAPI app: turns the Python modules into HTTP endpoints for the React UI.

Endpoints that call slow APIs are plain `def` (not `async def`) so FastAPI runs them in a
worker thread and the server stays responsive. Heavy follow-up work (embeddings,
anomaly checks, the 4 agents) runs in BackgroundTasks AFTER the response is sent.
"""
import os
import re
from datetime import datetime, date

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from db import supabase                                         # noqa: E402
from embeddings import backfill_embeddings, search_expenses     # noqa: E402
from ingest import receipt_json, save_expense                   # noqa: E402
from ocr import parse_receipt_image, parse_receipt_text         # noqa: E402
from services import fetch_expenses, process_expense            # noqa: E402
from analytics import monthly_totals                            # noqa: E402

try:                                                            # app still runs if crewai is missing
    from agents.crew import run_agent_pipeline, run_insights_only
    CREW_OK = True
except Exception as e:                                          # pragma: no cover
    print(f"[main] CrewAI unavailable: {e}")
    CREW_OK = False

app = FastAPI(title="ReceiptBrain API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

RUN_AGENTS = os.getenv("RUN_AGENTS_ON_UPLOAD", "true").lower() == "true"


def post_ingest(expense_id: str):
    """Background job after a new expense is saved."""
    try:
        process_expense(expense_id)                  # embedding + duplicate + anomaly rules (fast)
        if CREW_OK and RUN_AGENTS:
            run_agent_pipeline(expense_id)           # 4 CrewAI agents (slower)
    except Exception as e:
        print(f"[post_ingest] {expense_id}: {e}")


@app.get("/")
def root():
    return {"status": "ReceiptBrain API running", "version": "2.0.0", "crewai": CREW_OK}


# ---------------- ingestion ----------------
@app.post("/upload")
def upload_receipt(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Receipt photo -> Gemini vision -> saved expense. Agents run in the background."""
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg", "image/webp"):
        raise HTTPException(400, f"Unsupported file type {file.content_type}. Use JPG, PNG or WEBP.")
    try:
        parsed = parse_receipt_image(file.file.read())
        expense_id = save_expense(parsed, "image", receipt_json(parsed))
    except Exception as e:
        raise HTTPException(500, str(e))
    background_tasks.add_task(post_ingest, expense_id)
    return {"success": True, "expense_id": expense_id, "parsed_data": {
        **parsed, "merchant_category_hint": parsed["category"]}}


class TextIn(BaseModel):
    text: str


@app.post("/upload-text")
def upload_text(body: TextIn, background_tasks: BackgroundTasks):
    """Paste receipt text (handy for testing without a photo)."""
    try:
        parsed = parse_receipt_text(body.text)
        expense_id = save_expense(parsed, "text", body.text)
    except Exception as e:
        raise HTTPException(500, str(e))
    background_tasks.add_task(post_ingest, expense_id)
    return {"success": True, "expense_id": expense_id, "parsed_data": parsed}


class ManualExpenseIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=150)
    total: float = Field(gt=0)
    date: date
    category: str = "Other"
    payment_method: str = "UPI"
    notes: str = Field(default="", max_length=1000)


@app.post("/expenses/manual", status_code=201)
def create_manual_expense(
    body: ManualExpenseIn,
    background_tasks: BackgroundTasks
):
    """Save a manually entered expense without OCR."""

    allowed_categories = {
        "Food", "Travel", "Shopping", "Utilities",
        "Entertainment", "Subscriptions", "Healthcare", "Other"
    }

    if body.category not in allowed_categories:
        raise HTTPException(400, "Invalid expense category")

    merchant = body.merchant.strip()
    if not merchant:
        raise HTTPException(400, "Merchant name is required")

    
    parsed = {
        "merchant": merchant,
        "date": body.date.isoformat(),
        "total": round(body.total, 2),
        "currency": "INR",
        "category": body.category,
        "payment_method": body.payment_method,
        "line_items": [],
        "taxes": 0.0,
        "parse_confidence": 1.0
    }


    try:
        raw_text = receipt_json({
            **parsed,
            "notes": body.notes
        })

        expense_id = save_expense(
            parsed,
            "manual",
            raw_text
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}"
        )

    background_tasks.add_task(post_ingest, expense_id)

    return {
        "success": True,
        "expense_id": expense_id,
        "parsed_data": parsed
    }


@app.get("/gmail-sync")
def gmail_sync(days: int = 30, max_results: int = 25):
    """Imports bill emails. Needs gmail_credentials.json / token.pickle (local only)."""
    from gmail_sync import sync_gmail_bills
    try:
        r = sync_gmail_bills(days, max_results)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"success": True, "bills_imported": r["saved"], "skipped": r["skipped"], "errors": r["errors"]}


# ---------------- agents ----------------
@app.post("/analyze/{expense_id}")
def analyze(expense_id: str):
    """Run the full 4-agent CrewAI pipeline on one expense (10-30s)."""
    if not CREW_OK:
        raise HTTPException(503, "CrewAI is not installed")
    try:
        return run_agent_pipeline(expense_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/insights")
def insights(refresh: bool = False):
    """Latest saved insight; refresh=true regenerates it with the Insight agent."""
    try:
        if refresh:
            if not CREW_OK:
                raise HTTPException(503, "CrewAI is not installed")
            return {"insight": run_insights_only()}
        rows = supabase.table("insights").select("*").order("generated_at", desc=True).limit(1).execute().data
        return {"insight": rows[0] if rows else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------- reads for the dashboard ----------------

@app.get("/expenses")
def get_expenses(limit: int = 50, month: str = None):
    """Fetch expenses, optionally filtered by month."""

    if not 1 <= limit <= 10000:
        raise HTTPException(400, "Limit must be between 1 and 10000")

    if month and month != "all":
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise HTTPException(400, "Month must be YYYY-MM")

    results = []
    page_size = 500

    try:
        while len(results) < limit:
            query = (
                supabase.table("expenses")
                .select("*")
                .order("date", desc=True)
                .order("id", desc=True)
            )

            if month and month != "all":
                year, m = map(int, month.split("-"))

                start = date(year, m, 1)

                end = (
                    date(year + 1, 1, 1)
                    if m == 12
                    else date(year, m + 1, 1)
                )

                query = (
                    query.gte("date", start.isoformat())
                    .lt("date", end.isoformat())
                )

            batch_size = min(page_size, limit - len(results))

            rows = (
                query.range(
                    len(results),
                    len(results) + batch_size - 1
                )
                .execute()
                .data or []
            )

            results.extend(rows)

            if len(rows) < batch_size:
                break

        return {"expenses": results}

    except Exception as e:
        print(f"[get expenses] {e}")
        raise HTTPException(500, "Could not fetch expenses")


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: str):
    supabase.table("anomalies").delete().eq("expense_id", expense_id).execute()
    supabase.table("expenses").delete().eq("id", expense_id).execute()
    return {"success": True}


@app.get("/expenses/by-month")
def by_month():
    rows = get_expenses(
        limit=10000,
        month="all"
    )["expenses"]

    return {
        "monthly_data": monthly_totals(rows)
    }

@app.get("/summary")
def summary(month: str = None):
    """Spending summary for a month or all time."""

    month = month or datetime.now().strftime("%Y-%m")

    if month != "all" and not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", month
    ):
        raise HTTPException(400, "Month must be YYYY-MM or all")

    rows = get_expenses(
        limit=10000,
        month=month
    )["expenses"]

    by_cat = {}

    for row in rows:
        category = row.get("category") or "Other"
        amount = float(row.get("total") or 0)

        by_cat[category] = round(
            by_cat.get(category, 0) + amount,
            2
        )

    return {
        "this_month": month,
        "total_spent": round(sum(by_cat.values()), 2),
        "transaction_count": len(rows),
        "by_category": by_cat
    }


@app.get("/anomalies")
def anomalies():
    rows = supabase.table("anomalies").select("*, expenses(merchant,total,date)") \
        .eq("resolved", False).order("flagged_at", desc=True).execute().data
    return {"anomalies": rows}


@app.post("/anomalies/{anomaly_id}/resolve")
def resolve(anomaly_id: str):
    supabase.table("anomalies").update({"resolved": True}).eq("id", anomaly_id).execute()
    return {"success": True}


@app.get("/query")
def query(q: str, limit: int = 10):
    if not q.strip():
        raise HTTPException(400, "Search query cannot be empty")

    if not 1 <= limit <= 100:
        raise HTTPException(400, "Limit must be between 1 and 100")

    try:
        return {
            "results": search_expenses(q, limit),
            "query": q
        }
    except Exception as e:
        print(f"[search] {e}")
        raise HTTPException(500, "Search failed")

@app.post("/embeddings/backfill")
def backfill():
    return {"embedded": backfill_embeddings()}

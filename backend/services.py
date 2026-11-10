"""Post-processing every new expense goes through (fast, no LLM calls)."""
from db import supabase
from embeddings import store_embedding, find_duplicate_candidates
from analytics import detect_anomalies

COLS = "id, merchant, date, total, currency, category, subcategory, payment_method, line_items, parse_confidence, created_at"


def fetch_expenses(limit: int = 1000) -> list:
    return supabase.table("expenses").select(COLS).order("date", desc=True).limit(limit).execute().data


def save_anomalies(expense_id: str, anomalies: list) -> int:
    """Insert anomalies, skipping any (expense, type) pair that already exists."""
    existing = {a["type"] for a in supabase.table("anomalies").select("type")
                .eq("expense_id", expense_id).execute().data}
    n = 0
    for a in anomalies:
        if a["type"] in existing:
            continue
        supabase.table("anomalies").insert({"expense_id": expense_id, "type": a["type"],
                                            "description": a["description"]}).execute()
        existing.add(a["type"])
        n += 1
    return n


def process_expense(expense_id: str) -> list:
    """embedding -> pgvector duplicate check -> statistical anomaly rules -> save flags."""
    exp = supabase.table("expenses").select(COLS).eq("id", expense_id).single().execute().data
    store_embedding(expense_id, exp["merchant"], exp["category"], exp["line_items"])
    history = [e for e in fetch_expenses() if e["id"] != expense_id]
    found = detect_anomalies(exp, history, find_duplicate_candidates(expense_id))
    save_anomalies(expense_id, found)
    return found

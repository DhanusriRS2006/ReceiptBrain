"""Shared 'save to database' step used by upload, text-paste and Gmail sync."""
import json
from db import supabase


def save_expense(parsed: dict, source: str, raw_text: str, source_id: str = None,
                 user_id: str = None) -> str:
    """Insert one receipt row + one expense row. Returns the new expense id."""
    receipt = supabase.table("receipts").insert({
        "source": source, "raw_text": raw_text[:4000], "source_id": source_id, "user_id": user_id,
    }).execute()
    expense = supabase.table("expenses").insert({
        "receipt_id": receipt.data[0]["id"], "user_id": user_id,
        "merchant": parsed["merchant"], "date": parsed["date"], "total": parsed["total"],
        "currency": parsed["currency"], "category": parsed["category"],
        "payment_method": parsed["payment_method"], "line_items": parsed["line_items"],
        "taxes": parsed["taxes"], "parse_confidence": parsed["parse_confidence"],
    }).execute()
    return expense.data[0]["id"]


def receipt_json(parsed: dict) -> str:
    return json.dumps(parsed, ensure_ascii=False)

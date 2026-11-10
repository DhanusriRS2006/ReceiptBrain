
"""
embeddings.py - ReceiptBrain hybrid expense search.

Combines:
1. MiniLM semantic embeddings
2. Exact merchant and category matching
3. Amount and date filters
4. Relevance ranking
5. Highest / lowest expense sorting

Keeps existing embedding and duplicate detection functions.
"""

import re
from datetime import date, timedelta

from db import supabase

_model = None

CATEGORIES = {
    "food": ["food", "restaurant", "dining", "meal", "groceries"],
    "travel": ["travel", "transport", "cab", "taxi", "uber", "ola"],
    "shopping": ["shopping", "purchase", "clothes", "fashion"],
    "utilities": ["utilities", "electricity", "water bill", "internet bill"],
    "entertainment": ["entertainment", "movie", "cinema", "gaming"],
    "subscriptions": ["subscriptions", "subscription", "streaming"],
    "healthcare": ["healthcare", "medical", "hospital", "pharmacy"]
}

STOPWORDS = {
    "show", "find", "search", "get", "give", "me", "my",
    "expenses", "expense", "transactions", "transaction",
    "orders", "order", "payments", "payment", "spent",
    "spend", "on", "for", "from", "at", "the", "a", "an",
    "in", "during", "of", "and", "all", "how", "much",
    "did", "i", "above", "below", "over", "under",
    "more", "than", "less", "greater", "last", "this",
    "month", "year", "highest", "lowest", "top",
    "biggest", "smallest", "between", "to"
}


def get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer

        print("[embeddings] Loading all-MiniLM-L6-v2...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def generate_embedding(text: str) -> list:
    return get_model().encode(text).tolist()


def expense_text(merchant: str, category: str, items: list) -> str:
    names = " ".join(
        str(i.get("name", ""))
        for i in (items or [])
        if isinstance(i, dict)
    )

    return f"{merchant} {category} {names}".strip()


def store_embedding(
    expense_id: str,
    merchant: str,
    category: str,
    items: list
):
    embedding = generate_embedding(
        expense_text(merchant, category, items)
    )

    supabase.table("expenses").update({
        "embedding": embedding
    }).eq("id", expense_id).execute()


def backfill_embeddings() -> int:
    rows = (
        supabase.table("expenses")
        .select("id, merchant, category, line_items")
        .is_("embedding", "null")
        .execute()
        .data or []
    )

    for row in rows:
        store_embedding(
            row["id"],
            row["merchant"],
            row["category"],
            row["line_items"]
        )

    return len(rows)


def find_duplicate_candidates(expense_id: str) -> list:
    try:
        return supabase.rpc(
            "find_duplicate_candidates",
            {"p_expense_id": expense_id}
        ).execute().data

    except Exception as e:
        print(f"[embeddings] Duplicate lookup failed: {e}")
        return []


def parse_query_filters(query: str) -> dict:
    q = query.lower()
    filters = {}

    # Amount: above 400
    match = re.search(
        r"(?:above|over|more than|greater than|>)\s*₹?\s*(\d+(?:\.\d+)?)",
        q
    )
    if match:
        filters["min"] = float(match.group(1))

    # Amount: below 400
    match = re.search(
        r"(?:below|under|less than|cheaper than|<)\s*₹?\s*(\d+(?:\.\d+)?)",
        q
    )
    if match:
        filters["max"] = float(match.group(1))

    # Amount: between 200 and 500
    match = re.search(
        r"between\s*₹?\s*(\d+(?:\.\d+)?)\s*(?:and|to)\s*₹?\s*(\d+(?:\.\d+)?)",
        q
    )
    if match:
        filters["min_inclusive"] = float(match.group(1))
        filters["max_inclusive"] = float(match.group(2))

    today = date.today()

    if "last month" in q:
        filters["month"] = (
            today.replace(day=1) - timedelta(days=1)
        ).strftime("%Y-%m")

    elif "this month" in q:
        filters["month"] = today.strftime("%Y-%m")

    # Specific month: 2026-08
    match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", q)
    if match:
        filters["month"] = match.group(0)

    # Specific year: in 2025
    match = re.search(r"\b(?:in|during|for)\s+(20\d{2})\b", q)
    if match:
        filters["year"] = match.group(1)

    if any(word in q for word in ["highest", "biggest", "largest"]):
        filters["sort"] = "highest"

    elif any(word in q for word in ["lowest", "smallest", "cheapest"]):
        filters["sort"] = "lowest"

    for category, keywords in CATEGORIES.items():
        if any(
            re.search(r"\b" + re.escape(k) + r"\b", q)
            for k in keywords
        ):
            filters["category"] = category.capitalize()
            break

    return filters


def clean_query(query: str) -> str:
    """Remove filter language before semantic embedding."""

    q = query.lower()

    q = re.sub(
        r"\b(?:above|over|below|under|more than|less than)"
        r"\s*₹?\s*\d+(?:\.\d+)?",
        " ",
        q
    )

    q = re.sub(r"\b20\d{2}(?:-\d{2})?\b", " ", q)

    words = re.findall(r"[a-zA-Z]+", q)

    meaningful = [
        word for word in words
        if word not in STOPWORDS
    ]

    return " ".join(meaningful) or query


def matches_filters(row: dict, filters: dict) -> bool:
    amount = float(row.get("total") or 0)
    expense_date = str(row.get("date") or "")
    category = str(row.get("category") or "").lower()

    if "min" in filters and amount <= filters["min"]:
        return False

    if "max" in filters and amount >= filters["max"]:
        return False

    if "min_inclusive" in filters and amount < filters["min_inclusive"]:
        return False

    if "max_inclusive" in filters and amount > filters["max_inclusive"]:
        return False

    if "month" in filters:
        if not expense_date.startswith(filters["month"]):
            return False

    if "year" in filters:
        if not expense_date.startswith(filters["year"]):
            return False

    if "category" in filters:
        if category != filters["category"].lower():
            return False

    return True


def search_expenses(query: str, limit: int = 10) -> list:
    """
    Hybrid search using exact merchant matching,
    category filters and semantic similarity.
    """

    filters = parse_query_filters(query)
    semantic_query = clean_query(query)

    # Retrieve candidates from pgvector.
    vector_rows = supabase.rpc(
        "search_expenses",
        {
            "query_embedding": generate_embedding(semantic_query),
            "match_count": 200
        }
    ).execute().data or []

    # Also retrieve expenses for exact matching.
    # Pagination avoids Supabase's default row limit.
    all_rows = []
    page_size = 500
    offset = 0

    while True:
        batch = (
            supabase.table("expenses")
            .select("id, merchant, category, total, date, line_items")
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )

        all_rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    vector_map = {
        str(row["id"]): row
        for row in vector_rows
    }

    query_words = {
        word for word in re.findall(r"[a-zA-Z]+", semantic_query)
        if len(word) > 2
    }

    results = []

    for row in all_rows:
        if not matches_filters(row, filters):
            continue

        merchant = str(row.get("merchant") or "").lower()
        category = str(row.get("category") or "").lower()

        vector = vector_map.get(str(row["id"]))
        similarity = float(
            vector.get("similarity", 0) if vector else 0
        )

        merchant_words = set(re.findall(r"[a-zA-Z]+", merchant))

        merchant_match = bool(query_words & merchant_words)
        category_match = category in query_words

        # Semantic score + exact match boosts.
        score = max(0, similarity)

        if merchant_match:
            score += 0.45

        if category_match:
            score += 0.20

        # Exclude irrelevant results.
        has_structured_filter = any(
            key in filters
            for key in (
                "category", "month", "year", "min",
                "max", "min_inclusive", "max_inclusive"
            )
        )

        if score < 0.20 and not has_structured_filter:
            continue

        result = {
            **row,
            "similarity": round(min(score, 1.0), 4)
        }

        results.append(result)

    if filters.get("sort") == "highest":
        results.sort(
            key=lambda r: float(r.get("total") or 0),
            reverse=True
        )

    elif filters.get("sort") == "lowest":
        results.sort(
            key=lambda r: float(r.get("total") or 0)
        )

    else:
        results.sort(
            key=lambda r: r["similarity"],
            reverse=True
        )

    return results[:limit]


if __name__ == "__main__":
    examples = [
        "Swiggy orders last month",
        "food expenses above 400",
        "travel in 2025",
        "highest shopping expenses"
    ]

    for q in examples:
        print(q, parse_query_filters(q), clean_query(q))

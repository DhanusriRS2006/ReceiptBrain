"""
analytics.py - the NUMBERS. Pure functions, no LLM, no database.

LLMs are unreliable at arithmetic, so we compute spend statistics in code and hand the
agents the results to reason about. This is "grounding" an agent in tool output.
"""
from collections import defaultdict
from datetime import datetime
from statistics import median


def month_of(d) -> str:
    return str(d)[:7]


def monthly_totals(expenses: list) -> dict:
    """{'2026-03': {'Food': 1800.0, ...}, ...}"""
    out = defaultdict(lambda: defaultdict(float))
    for e in expenses:
        if e.get("date"):
            out[month_of(e["date"])][e.get("category") or "Other"] += float(e.get("total") or 0)
    return {m: dict(c) for m, c in sorted(out.items())}


def category_series(monthly: dict, category: str, last_n: int = 3) -> list:
    return [monthly[m][category] for m in sorted(monthly) if category in monthly[m]][-last_n:]


def inflation_candidates(monthly: dict, threshold: float = 0.15) -> list:
    """Lifestyle inflation = a category growing >15% month-on-month, 2 months in a row."""
    cats = {c for m in monthly.values() for c in m}
    flags = []
    for c in sorted(cats):
        s = category_series(monthly, c, 3)
        if len(s) == 3 and s[0] > 0 and s[1] > 0:
            g1, g2 = s[1] / s[0] - 1, s[2] / s[1] - 1
            if g1 > threshold and g2 > threshold:
                flags.append({"category": c, "values": s,
                              "increase_percent": round((s[2] / s[0] - 1) * 100, 1),
                              "months_consecutive": 2})
    return flags


def forecast_baseline(monthly: dict) -> dict:
    """Weighted moving average of last 3 months (recent months weigh more)."""
    cats = {c for m in monthly.values() for c in m}
    out = {}
    for c in sorted(cats):
        s = list(reversed(category_series(monthly, c, 3)))      # newest first
        w = [0.5, 0.3, 0.2][:len(s)]
        out[c] = round(sum(v * x for v, x in zip(s, w)) / sum(w), 2) if s else 0.0
    out["total"] = round(sum(out.values()), 2)
    return out


def detect_anomalies(exp: dict, history: list, duplicates: list) -> list:
    """exp = the new expense, history = all OTHER expenses, duplicates = pgvector matches."""
    found = []
    name, total, cat = exp.get("merchant", "?"), float(exp.get("total") or 0), exp.get("category")

    for d in duplicates[:1]:
        found.append({"type": "duplicate", "severity": "high",
                      "description": f"{name} charged Rs.{total:.0f}, which looks like a duplicate of "
                                     f"Rs.{d['total']:.0f} on {d['date']}. Check your bank statement."})

    # monthly spike: this month's category total vs average of previous months
    cur_month = month_of(exp["date"])
    same_cat = [e for e in history if e.get("category") == cat and e.get("date")]
    prev = monthly_totals(same_cat)
    prev = [v[cat] for m, v in prev.items() if m < cur_month and cat in v][-3:]
    cur_total = total + sum(float(e["total"] or 0) for e in same_cat if month_of(e["date"]) == cur_month)
    if len(prev) >= 2:
        avg = sum(prev) / len(prev)
        if avg > 0 and cur_total > 2 * avg and cur_total - avg > 300:
            found.append({"type": "spike", "severity": "medium",
                          "description": f"{cat} spending this month is Rs.{cur_total:.0f}, "
                                         f"{cur_total / avg:.1f}x your recent average of Rs.{avg:.0f}."})

    # single unusually large transaction
    amounts = [float(e["total"] or 0) for e in same_cat]
    if len(amounts) >= 5 and total > 500 and total > 3 * median(amounts):
        found.append({"type": "spike", "severity": "low",
                      "description": f"Rs.{total:.0f} at {name} is far above your typical {cat} "
                                     f"purchase (median Rs.{median(amounts):.0f})."})

    # brand-new merchant with a big amount (only meaningful once we have some history)
    seen = {str(e.get("merchant", "")).lower() for e in history}
    if len(history) >= 10 and name.lower() not in seen and total >= 2000:
        found.append({"type": "unusual_merchant", "severity": "medium",
                      "description": f"First time you've paid {name}, and the amount is Rs.{total:.0f}. "
                                     f"Verify this charge is yours."})
    return found

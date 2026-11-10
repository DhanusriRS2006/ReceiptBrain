"""
crew.py - wires the 4 agents into a sequential CrewAI pipeline.

  Parser/Validator -> Categorizer -> Anomaly Detector -> Insight

Design rule: code computes numbers (analytics.py), agents reason about them, and
code validates + saves what the agents return. Agents never write to the DB blindly.
"""
import json
import os
from datetime import datetime

os.environ.setdefault("OTEL_SDK_DISABLED", "true")           # silence telemetry prompts
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

import litellm
litellm.drop_params = True

from crewai import Crew, LLM, Process   # noqa: E402
from dotenv import load_dotenv          # noqa: E402


load_dotenv()

from analytics import (detect_anomalies, forecast_baseline, inflation_candidates,  # noqa: E402
                       monthly_totals)
from categories import CATEGORIES                                                    # noqa: E402
from db import supabase                                                              # noqa: E402
from embeddings import find_duplicate_candidates                                     # noqa: E402
from jsonutil import extract_json                                                    # noqa: E402
from services import fetch_expenses, save_anomalies                                  # noqa: E402
from agents.anomaly import create_anomaly_agent, create_anomaly_task                 # noqa: E402
from agents.categorizer import create_categorizer_agent, create_categorize_task      # noqa: E402
from agents.insight import create_insight_agent, create_insight_task                 # noqa: E402
from agents.parser import create_parser_agent, create_parse_task                     # noqa: E402

from .groq_compat import enable_groq_compat

enable_groq_compat()

EXP_COLS = "id, merchant, date, total, currency, category, payment_method, line_items, taxes, parse_confidence"


def _llm(fast: bool = False):
    name = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant") if fast \
        else os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return LLM(
    model=f"groq/{name}",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=1200,
    additional_drop_params=["cache_breakpoint"],
    )

def _safe_json(task_output) -> dict:
    try:
        return extract_json(task_output.raw)
    except Exception as e:
        print(f"[crew] could not parse agent output: {e}")
        return {}


def _insight_payload(all_expenses: list) -> tuple:
    monthly = monthly_totals(all_expenses)
    recent = dict(list(monthly.items())[-4:])
    base, infl = forecast_baseline(monthly), inflation_candidates(monthly)
    return json.dumps({"monthly_totals": recent, "baseline_forecast": base,
                       "inflation_candidates": infl}), base, infl


def _save_insight(out: dict, base: dict, infl: list):
    month = datetime.now().strftime("%Y-%m")
    preds = out.get("predictions") or base
    supabase.table("insights").delete().eq("month", month).execute()
    supabase.table("insights").insert({
        "month": month, "predictions": preds,
        "inflation_flags": out.get("inflation_flags", infl) if out else infl,
        "summary_text": out.get("summary", ""), "savings_tip": out.get("savings_tip", ""),
    }).execute()
    return {"month": month, "predictions": preds, "inflation_flags": out.get("inflation_flags", infl),
            "summary": out.get("summary", ""), "savings_tip": out.get("savings_tip", ""),
            "top_category": out.get("top_category", "")}


def run_agent_pipeline(expense_id: str) -> dict:
    """Full 4-agent run for one stored expense. Takes ~10-30s."""
    exp = supabase.table("expenses").select(EXP_COLS).eq("id", expense_id).single().execute().data
    allx = fetch_expenses()
    history = [e for e in allx if e["id"] != expense_id]
    py_signals = detect_anomalies(exp, history, find_duplicate_candidates(expense_id))
    ins_payload, base, infl = _insight_payload(allx)

    expense_view = {k: exp[k] for k in ("merchant", "date", "total", "currency", "payment_method",
                                       "line_items", "taxes", "parse_confidence")}
    fast, strong = _llm(fast=True), _llm()
    a1, a2, a3, a4 = (create_parser_agent(fast), create_categorizer_agent(fast),
                      create_anomaly_agent(strong), create_insight_agent(strong))
    t1 = create_parse_task(a1, json.dumps(expense_view))
    t2 = create_categorize_task(a2, json.dumps(expense_view), [t1])
    t3 = create_anomaly_task(a3, json.dumps({"expense": expense_view, "computed_signals": py_signals}), [t2])
    t4 = create_insight_task(a4, ins_payload, [t3])

    result = Crew(agents=[a1, a2, a3, a4], tasks=[t1, t2, t3, t4],
                  process=Process.sequential, verbose=False).kickoff()
    o1, o2, o3, o4 = (_safe_json(t) for t in result.tasks_output[:4])

    update = {}
    if isinstance(o1.get("parse_confidence"), (int, float)):
        update["parse_confidence"] = max(0.0, min(1.0, float(o1["parse_confidence"])))
    if o2.get("category") in CATEGORIES:
        update.update({"category": o2["category"], "subcategory": o2.get("subcategory"),
                       "tags": o2.get("tags", [])})
    if update:
        supabase.table("expenses").update(update).eq("id", expense_id).execute()

    flagged = list(py_signals)
    if o3.get("is_anomaly") and o3.get("anomaly_type") in ("spike", "duplicate", "unusual_merchant"):
        flagged.append({"type": o3["anomaly_type"], "description": o3.get("description", "")})
    save_anomalies(expense_id, [a for a in flagged if a.get("description")])
    insight = _save_insight(o4, base, infl)

    return {"validation": o1, "categorization": o2, "anomaly_verdict": o3,
            "python_signals": py_signals, "insight": insight}


def run_insights_only() -> dict:
    """Insight agent alone, on current data. Used by the Trends page button."""
    payload, base, infl = _insight_payload(fetch_expenses())
    agent = create_insight_agent(_llm())
    task = create_insight_task(agent, payload)
    result = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()
    return _save_insight(_safe_json(result.tasks_output[0]), base, infl)

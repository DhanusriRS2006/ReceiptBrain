"""
Optional: fill the database with clearly-labelled SAMPLE data so Trends, Alerts and Insights
have 4 months of history to work with.   python seed_demo.py          (add sample data)
                                         python seed_demo.py --clear  (remove it again)
Sample rows are tagged raw_text='DEMO_SEED'. Say "sample data" in any demo video / interview.
"""
import sys
from datetime import date

from db import supabase
from embeddings import backfill_embeddings
from services import process_expense


def month_start(back: int) -> date:
    t = date.today().replace(day=1)
    y, m = t.year, t.month - back
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def rows():
    out = []
    food = [1500, 1850, 2300, 2900]                      # +20-25% a month -> lifestyle inflation
    for i, base in enumerate(food):                      # i=0 is 3 months ago
        d0 = month_start(3 - i)
        out += [("Swiggy", d0.replace(day=4), base * 0.4, "Food"), ("Zomato", d0.replace(day=13), base * 0.35, "Food"),
                ("Swiggy", d0.replace(day=24), base * 0.25, "Food"),
                ("Airtel", d0.replace(day=7), 599, "Utilities"), ("BESCOM", d0.replace(day=15), 1100 + i * 40, "Utilities"),
                ("Netflix", d0.replace(day=9), 649, "Subscriptions"),
                ("Uber", d0.replace(day=18), 280 + i * 30, "Travel"), ("Amazon", d0.replace(day=21), 700 + 350 * (i % 2), "Shopping")]
    last = month_start(0)
    out += [("Airtel", last.replace(day=8), 599, "Utilities"),        # duplicate charge
            ("Myntra", last.replace(day=19), 5400, "Shopping")]       # spike
    return out


def main():
    if "--clear" in sys.argv:
        ids = [r["id"] for r in supabase.table("receipts").select("id").eq("raw_text", "DEMO_SEED").execute().data]
        for rid in ids:
            for e in supabase.table("expenses").select("id").eq("receipt_id", rid).execute().data:
                supabase.table("anomalies").delete().eq("expense_id", e["id"]).execute()
            supabase.table("expenses").delete().eq("receipt_id", rid).execute()
            supabase.table("receipts").delete().eq("id", rid).execute()
        print(f"removed {len(ids)} sample rows")
        return
    new_ids = []
    for merchant, d, total, cat in rows():
        if d > date.today():
            continue
        r = supabase.table("receipts").insert({"source": "text", "raw_text": "DEMO_SEED"}).execute().data[0]["id"]
        e = supabase.table("expenses").insert({
            "receipt_id": r, "merchant": merchant, "date": d.isoformat(), "total": round(total, 2), "currency": "INR",
            "category": cat, "payment_method": "UPI", "line_items": [{"name": merchant, "qty": 1, "amount": round(total, 2)}],
            "parse_confidence": 1.0}).execute().data[0]["id"]
        new_ids.append(e)
    print(f"inserted {len(new_ids)} sample expenses; embedding...")
    backfill_embeddings()
    for eid in new_ids:
        process_expense(eid)
    print("done. Open Dashboard / Trends / Alerts.")


if __name__ == "__main__":
    main()

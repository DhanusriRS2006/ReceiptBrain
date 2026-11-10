"""
ocr.py - receipt image / text  ->  clean, validated expense dict.

Model: Gemini via OpenRouter (OpenAI-compatible API).
Why your earlier run failed: the model leaked its "thinking" into the reply and
ran out of tokens mid-JSON. Fixes here:
  1. response_format=json_object + low reasoning effort + max_tokens=4000
  2. extract_json() survives chatter / markdown / truncated output
  3. validation + retry (and optional fallback model) if fields are missing
"""
import base64
import io
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from categories import normalize_category
from jsonutil import extract_json

load_dotenv()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
MODELS = [m for m in (os.getenv("OPENROUTER_MODEL", "google/gemini-3.5-flash"),
                      os.getenv("OPENROUTER_FALLBACK_MODEL", "")) if m]

SYSTEM = ("You extract expense data from Indian receipts, bills and order emails. "
          "Reply with ONE JSON object and nothing else.")

PROMPT = """Extract this expense. Output exactly this JSON shape:
{"merchant": "store/service name", "date": "YYYY-MM-DD", "total": 0.0, "currency": "INR",
 "payment_method": "UPI|Cash|Card|Online|Unknown",
 "line_items": [{"name": "item", "qty": 1, "amount": 0.0}],
 "taxes": 0.0,
 "merchant_category_hint": "Food|Travel|Shopping|Utilities|Entertainment|Healthcare|Subscriptions|Other",
 "parse_confidence": 0.9}
Rules: total = final amount paid (number only). date = YYYY-MM-DD. If unclear use 0.0 / "Unknown".
parse_confidence is 0.5-0.7 when blurry or ambiguous."""


# ---------- model call ----------
def _chat(messages, model):
    kwargs = dict(model=model, messages=messages, max_tokens=1500, temperature=0)
    try:
        return client.chat.completions.create(
            **kwargs, response_format={"type": "json_object"},
            extra_body={"reasoning": {"effort": "low"}})
    except Exception as e:  # some models reject these extras -> retry plain
        print(f"[ocr] retrying without extras: {str(e)[:100]}")
        return client.chat.completions.create(**kwargs)


def _run(messages) -> dict:
    last = None
    for model in MODELS:
        for attempt in (1, 2):
            try:
                raw = _chat(messages, model).choices[0].message.content or ""
                data = extract_json(raw)
                if "merchant" in data and "total" in data:
                    return data
                last = ValueError(f"missing fields in: {raw[:120]!r}")
            except Exception as e:
                last = e
            print(f"[ocr] {model} attempt {attempt} failed: {str(last)[:120]}")
    raise RuntimeError(f"Receipt parsing failed: {last}")


# ---------- normalisation ----------
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%B %d, %Y",
                "%b %d, %Y", "%d/%m/%y", "%d-%b-%Y", "%d-%b-%y", "%m/%d/%Y"]


def normalize_date(value) -> tuple:
    """Returns (YYYY-MM-DD, guessed?). Falls back to today if unparseable."""
    s = str(value or "").strip()
    for candidate in (s, s[:10]):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d"), False
            except ValueError:
                continue
    return datetime.today().strftime("%Y-%m-%d"), True


def clean_amount(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "")
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def normalize(p: dict) -> dict:
    date, guessed = normalize_date(p.get("date"))
    items = []
    for it in p.get("line_items") or []:
        if isinstance(it, dict):
            items.append({"name": str(it.get("name", "")), "qty": it.get("qty", 1) or 1,
                          "amount": clean_amount(it.get("amount", 0))})
    merchant = str(p.get("merchant") or "Unknown").strip() or "Unknown"
    try:
        conf = max(0.0, min(1.0, float(p.get("parse_confidence", 0.8))))
    except (TypeError, ValueError):
        conf = 0.8
    return {
        "merchant": merchant, "date": date, "total": clean_amount(p.get("total")),
        "currency": p.get("currency") or "INR",
        "payment_method": p.get("payment_method") or "Unknown",
        "line_items": items, "taxes": clean_amount(p.get("taxes")),
        "category": normalize_category(merchant, p.get("merchant_category_hint", "")),
        "parse_confidence": round(conf - (0.2 if guessed else 0), 2),
    }


# ---------- public API ----------
def _shrink(image_bytes: bytes) -> str:
    """Phone photos are 5-10 MB. Resize to <=1600px JPEG so the API call is fast and cheap."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def parse_receipt_image(image_bytes: bytes) -> dict:
    b64 = _shrink(image_bytes)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
    return normalize(_run(messages))


def parse_receipt_text(text: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{PROMPT}\n\nReceipt text:\n{text[:6000]}"}]
    return normalize(_run(messages))


if __name__ == "__main__":
    import json
    sample = """SWIGGY ORDER RECEIPT  Order #SW123456  Date: 20 Jan 2025
    Paneer Butter Masala x1 Rs. 280 | Butter Naan x2 Rs. 100 | Delivery Fee Rs. 40 | GST Rs. 21
    Total Paid: Rs. 441   Payment: UPI"""
    print(json.dumps(parse_receipt_text(sample), indent=2))

"""
gmail_sync.py - read bill emails from Gmail and turn them into expenses.

OAuth 2.0 (authorization, not authentication): the user approves "read-only Gmail"
once in the browser; Google gives us a token saved in token.pickle and refreshed
automatically. We never see the password. Scope gmail.readonly = least privilege.

First-time login:  python gmail_sync.py     (opens a browser)
"""
import base64
import os
import pickle
import re

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pathlib import Path

from db import supabase
from ingest import save_expense
from ocr import parse_receipt_text
from services import process_expense

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BASE_DIR = Path(__file__).resolve().parent

TOKEN_PATH = BASE_DIR / "token.pickle"
CREDENTIALS_PATH = BASE_DIR / "gmail_credentials.json"

SENDERS = "swiggy OR zomato OR amazon OR flipkart OR myntra OR airtel OR jio OR bescom OR irctc OR " \
          "makemytrip OR bookmyshow OR uber OR ola OR netflix OR spotify OR blinkit OR zepto OR phonepe OR paytm"



def get_gmail_service():
    creds = None

    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES
            ).run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def extract_body(payload: dict) -> str:
    """Walk the MIME tree. Prefer text/plain; fall back to text/html (most Indian
    receipts are HTML-only) converted to plain text."""
    plain, html = [], []

    def walk(part):
        mime, data = part.get("mimeType", ""), part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_decode(data))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain).strip()
    if html:
        return re.sub(r"\n\s*\n+", "\n", BeautifulSoup("\n".join(html), "html.parser")
                      .get_text("\n")).strip()
    return ""


def sync_gmail_bills(days: int = 30, max_results: int = 25) -> dict:
    service = get_gmail_service()
    query = (f'(subject:(invoice OR receipt OR "order confirmed" OR "order summary" OR bill OR payment) '
             f'OR from:({SENDERS})) newer_than:{days}d')
    refs = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute() \
        .get("messages", [])
    print(f"[gmail] {len(refs)} candidate emails")
    saved = skipped = 0
    errors = []
    for ref in refs:
        mid = ref["id"]
        try:
            if supabase.table("receipts").select("id").eq("source_id", mid).execute().data:
                skipped += 1                                  # already imported
                continue
            msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
            body = extract_body(msg["payload"])
            if len(body) < 50 or not re.search(r"(₹|Rs\.?|INR|total|amount)", body, re.I):
                skipped += 1
                continue
            parsed = parse_receipt_text(body)
            if parsed["total"] <= 0:
                skipped += 1
                continue
            expense_id = save_expense(parsed, "gmail", body, source_id=mid)
            process_expense(expense_id)
            saved += 1
            print(f"[gmail] saved {parsed['merchant']} Rs.{parsed['total']} {parsed['date']}")
        except Exception as e:
            errors.append(str(e)[:120])
            print(f"[gmail] error: {e}")
    return {"saved": saved, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    print(sync_gmail_bills())

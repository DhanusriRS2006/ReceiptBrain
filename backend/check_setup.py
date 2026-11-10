"""Run this FIRST:  python check_setup.py   - verifies every key and service, one line each."""
import os
from dotenv import load_dotenv

load_dotenv()


def check(name, fn):
    try:
        print(f"[ OK ] {name}: {fn()}")
    except Exception as e:
        print(f"[FAIL] {name}: {str(e)[:200]}")


def env():
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY")
               if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"missing in .env: {missing}")
    return "all keys present"


def supabase_db():
    from db import supabase
    supabase.table("expenses").select("id").limit(1).execute()
    supabase.table("expenses").select("embedding, subcategory").limit(1).execute()
    return "connected, v2 schema columns present"


def openrouter():
    from ocr import parse_receipt_text
    r = parse_receipt_text("SWIGGY order 20 Jan 2025. Paneer Rs 280. Total Rs 441. UPI")
    return f"{r['merchant']} / {r['total']} / {r['date']} / {r['category']}"


def groq():
    from openai import OpenAI
    c = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
    r = c.chat.completions.create(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                                  messages=[{"role": "user", "content": "Say OK"}], max_tokens=5)
    return r.choices[0].message.content


def embed():
    from embeddings import generate_embedding
    return f"{len(generate_embedding('test'))} dimensions"


def crew():
    import crewai
    return f"crewai {getattr(crewai, '__version__', 'installed')}"


for n, f in (("env file", env), ("Supabase + schema", supabase_db), ("OpenRouter / Gemini", openrouter),
             ("Groq", groq), ("Embeddings", embed), ("CrewAI", crew)):
    check(n, f)

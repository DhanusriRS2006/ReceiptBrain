import os
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    from openai import OpenAI
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        response = client.chat.completions.create(
    model="google/gemini-3.5-flash",  # or any working model
    messages=[{"role": "user", "content": "Say the word OK only"}],
    max_tokens=50   # ✅ ADD THIS
)
        print("OpenRouter + Gemini Flash works:", response.choices[0].message.content)
    except Exception as e:
        print("OpenRouter FAILED:", e)

def test_groq():
    from groq import Groq
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say the word OK only"}]
        )
        print("Groq + Llama 3.3 works:", response.choices[0].message.content)
    except Exception as e:
        print("Groq FAILED:", e)

test_openrouter()
test_groq()
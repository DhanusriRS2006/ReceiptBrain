
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

# Fix unsupported cache_breakpoint field for Groq
original_completion = litellm.completion

def fixed_completion(*args, **kwargs):
    model = kwargs.get("model", "")

    if isinstance(model, str) and model.startswith("groq/"):
        messages = kwargs.get("messages", [])

        kwargs["messages"] = [
            {
                key: value
                for key, value in message.items()
                if key != "cache_breakpoint"
            }
            for message in messages
        ]

    return original_completion(*args, **kwargs)

litellm.completion = fixed_completion

# Initialize Groq model
llm = LLM(
    model="groq/" + os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
    max_tokens=100
)

# Create AI agent
agent = Agent(
    role="Expense Categorizer",
    goal="Categorize expenses accurately",
    backstory="You classify personal expenses into categories.",
    llm=llm,
    verbose=False,
    allow_delegation=False,
    cache=False
)

# Create task
task = Task(
    description="Categorize a Swiggy food order. Reply with only Food.",
    expected_output="One category name",
    agent=agent
)

# Run CrewAI
result = Crew(
    agents=[agent],
    tasks=[task],
    verbose=False,
    cache=False
).kickoff()

print("RESULT:", result.raw)

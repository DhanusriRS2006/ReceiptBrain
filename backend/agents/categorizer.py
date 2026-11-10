"""Agent 2 - Categorizer: category + subcategory + tags."""
from crewai import Agent, Task
from categories import CATEGORIES


def create_categorizer_agent(llm):
    return Agent(
        role="Indian Expense Categorizer",
        goal="Assign the correct spending category, a precise subcategory and useful tags",
        backstory="You know Indian merchants: Swiggy/Zomato/Blinkit = Food, Amazon/Flipkart/Myntra = Shopping, "
                  "Airtel/Jio/BESCOM = Utilities, Uber/Ola/IRCTC = Travel, Netflix/Spotify = Subscriptions.",
        llm=llm, allow_delegation=False, verbose=False)


def create_categorize_task(agent, payload: str, context):
    return Task(
        description=f"""Categorize this expense. Return ONLY JSON:
{{"category": "one of {CATEGORIES}", "subcategory": "2-3 words e.g. Food Delivery",
 "tags": ["2-4 keywords"], "confidence": 0.9}}
Expense: {payload}""",
        expected_output="JSON with category, subcategory, tags, confidence", agent=agent, context=context)

"""Agent 4 - Insight: forecast + lifestyle-inflation narrative."""
from crewai import Agent, Task


def create_insight_agent(llm):
    return Agent(
        role="Personal Finance Insight Generator",
        goal="Explain spending trends, forecast next month and give one concrete saving tip",
        backstory="You are a warm, honest finance advisor for Indian users. You receive monthly totals, "
                  "a baseline forecast and pre-detected inflation candidates computed in code. "
                  "You may adjust the forecast slightly but stay close to the baseline.",
        llm=llm, allow_delegation=False, verbose=False)


def create_insight_task(agent, payload: str, context=None):
    return Task(
        description=f"""Write the monthly insight. Return ONLY JSON:
{{"predictions": {{"<Category>": 0.0, "total": 0.0}},
 "inflation_flags": [{{"category": "", "increase_percent": 0.0, "message": "friendly alert"}}],
 "top_category": "", "summary": "2-3 sentences using 'you' and 'your'",
 "savings_tip": "one specific actionable tip"}}
Use the inflation candidates as the only source of inflation_flags (empty list if none).
Data: {payload}""",
        expected_output="JSON with predictions, inflation_flags, summary, savings_tip",
        agent=agent, context=context or [])

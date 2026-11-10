"""Agent 3 - Anomaly Detector: judges statistical signals computed in code."""
from crewai import Agent, Task


def create_anomaly_agent(llm):
    return Agent(
        role="Financial Anomaly Detector",
        goal="Decide whether a new expense is a genuine anomaly and explain it to the user clearly",
        backstory="You are a careful personal-finance guard. You are given pre-computed signals "
                  "(duplicate matches, spend vs average) and decide if the user should be alerted. "
                  "You never flag normal recurring bills. You never do arithmetic yourself - you trust the signals.",
        llm=llm, allow_delegation=False, verbose=False)


def create_anomaly_task(agent, payload: str, context):
    return Task(
        description=f"""Judge this expense using the computed signals. Return ONLY JSON:
{{"is_anomaly": false, "anomaly_type": "none|spike|duplicate|unusual_merchant",
 "severity": "none|low|medium|high", "description": "one friendly sentence with amounts, empty if none",
 "recommended_action": "what the user should do, empty if none"}}
Data: {payload}""",
        expected_output="JSON anomaly verdict", agent=agent, context=context)

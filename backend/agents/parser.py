"""Agent 1 - Parser/Validator: checks the OCR output for internal consistency."""
from crewai import Agent, Task


def create_parser_agent(llm):
    return Agent(
        role="Receipt Parser & Validator",
        goal="Verify extracted receipt data is internally consistent and score its reliability",
        backstory="You are a meticulous data-quality specialist for Indian receipts (INR, UPI, GST). "
                  "You check that line items plus taxes roughly match the total, the date is plausible "
                  "and the merchant name is clean.",
        llm=llm, allow_delegation=False, verbose=False)


def create_parse_task(agent, payload: str):
    return Task(
        description=f"""Validate this extracted expense. Return ONLY JSON:
{{"valid": true, "issues": ["short issue strings, empty if none"], "parse_confidence": 0.0}}
Expense: {payload}""",
        expected_output="JSON with valid, issues, parse_confidence", agent=agent)

import json
import re
from typing import List
from groq import Groq
from server.agent.models import Step
from server.config import settings

SYSTEM_PROMPT = """
You are a browser automation planner.

Return ONLY a JSON array of steps.
No markdown. No explanation.

Rules:
- Use actions: navigate, click, type, press, scroll, wait
- Extract search keywords from instructions
- Never paste full instruction into search fields
- URLs must be valid

Example:

Goal:
Find full stack course on geeksforgeeks

Output:
[
 {"action":"navigate","url":"https://www.geeksforgeeks.org"},
 {"action":"type","selector":"input[type='search']","text":"full stack"},
 {"action":"press","selector":"input[type='search']","key":"Enter"}
]
"""


class Planner:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)
        self.last_plan_source = "llm"

    def generate_steps(self, goal: str) -> List[Step]:
        try:
            text = self._generate_text(goal)
            steps_raw = _parse_json(text)

            if isinstance(steps_raw, list):
                steps = _validate_steps(steps_raw)
                if steps:
                    self.last_plan_source = "llm"
                    return steps[: settings.max_steps]
        except Exception:
            pass

        self.last_plan_source = "fallback"
        return _fallback_steps(goal)

    def _generate_text(self, goal: str) -> str:
        response = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Goal: {goal}"},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


def _validate_steps(raw) -> List[Step]:
    steps = []
    for s in raw:
        try:
            steps.append(Step.model_validate(s))
        except Exception:
            continue
    return steps


def _parse_json(text: str):
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON")
    return json.loads(match.group(0))


def _fallback_steps(goal: str) -> List[Step]:
    url = _extract_url(goal)
    query = _extract_query(goal)

    if url:
        return [
            Step(action="navigate", url=url),
            Step(action="wait", ms=500),
            Step(action="type", selector="input[type='search']", text=query),
            Step(action="press", selector="input[type='search']", key="Enter"),
        ]

    return [
        Step(action="navigate", url=f"https://www.google.com/search?q={query.replace(' ', '+')}"),
        Step(action="wait", ms=500),
    ]


def _extract_url(goal: str) -> str | None:
    m = re.search(r"https?://[^\s]+", goal)
    if m:
        return m.group(0)
    return None


def _extract_query(goal: str) -> str:
    q = re.sub(r"https?://[^\s]+", "", goal)
    q = q.replace("find", "").replace("course", "")
    q = q.replace("on", "").strip()
    return q

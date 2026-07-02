from __future__ import annotations

# Cost-aware per-task model routing. Change here, not in call sites.
ROUTING: dict[str, str] = {
    "tutor_socratic": "claude-haiku-4-5",
    "grade_reasoning": "claude-haiku-4-5",
    "generate_question": "claude-sonnet-4-6",
}

DEFAULT_MODEL = "claude-haiku-4-5"


def model_for(task: str) -> str:
    return ROUTING.get(task, DEFAULT_MODEL)

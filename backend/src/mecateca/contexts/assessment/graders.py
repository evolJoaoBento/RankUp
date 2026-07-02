from __future__ import annotations

from dataclasses import dataclass, field

from mecateca.adapters.llm.base import LLMMessage, LLMProvider, LLMRequest, Usage


@dataclass
class Grade:
    correct: bool
    reasoning_score: float
    feedback: str = ""
    detail: dict = field(default_factory=dict)
    graded_by: str = ""
    usage: Usage | None = None


class MCQGrader:
    kind = "mcq"

    def grade(self, raw: dict, payload: dict) -> Grade:
        selected = raw.get("selected_index")
        answer = payload.get("answer_index")
        correct = selected is not None and selected == answer
        return Grade(
            correct=correct,
            reasoning_score=0.0,  # MCQ shows no reasoning -> base XP only
            feedback=payload.get("why", "") if correct else "Revê o conceito e tenta de novo.",
            detail={"selected": selected, "answer": answer},
            graded_by=self.kind,
        )


_SCHEMA = {
    "type": "object",
    "properties": {
        "correct": {"type": "boolean"},
        "reasoning_score": {"type": "number"},
        "feedback": {"type": "string"},
    },
    "required": ["correct", "reasoning_score", "feedback"],
    "additionalProperties": False,
}


class AIReasoningGrader:
    kind = "ai_reasoning"

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    async def grade(self, raw: dict, payload: dict, rubric: list | None, material: str | None = None) -> Grade:
        prompt = payload.get("prompt") or payload.get("stem", "")
        student = raw.get("text", "")
        criteria = "\n".join(
            f"- {c.get('key')}: {c.get('descriptor','')} (peso {c.get('weight')})"
            for c in (rubric or [])
        )
        system = (
            "És um avaliador rigoroso. Avalia a resposta do aluno contra a rubrica"
            + (" e o MATERIAL DE REFERÊNCIA (fonte da verdade)" if material else "") + ". "
            "Dá reasoning_score entre 0 e 1 pela qualidade do raciocínio mostrado "
            "(não só pela conclusão). 'correct' indica se demonstra compreensão suficiente. "
            "Feedback curto, em português de Portugal."
        )
        ref = f"\n\nMaterial de referência:\n{material}" if material else ""
        user = f"Pergunta: {prompt}\n\nRubrica:\n{criteria}{ref}\n\nResposta do aluno:\n{student}"
        req = LLMRequest(task="grade_reasoning", system=system, messages=[LLMMessage("user", user)])
        data, usage = await self._provider.parse(req, _SCHEMA)
        return Grade(
            correct=bool(data.get("correct")),
            reasoning_score=float(max(0.0, min(1.0, data.get("reasoning_score", 0.0)))),
            feedback=str(data.get("feedback", "")),
            detail=data,
            graded_by=self.kind,
            usage=usage,
        )

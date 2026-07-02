from __future__ import annotations

from mecateca.adapters.llm.base import LLMMessage, LLMProvider, LLMRequest

_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["1", "2", "draw"]},
        "reason": {"type": "string"},
    },
    "required": ["winner", "reason"],
    "additionalProperties": False,
}


async def judge_answers(
    provider: LLMProvider,
    question: str,
    answer1: str,
    answer2: str,
    reference: str | None,
):
    """Compare two answers to the same question. Answer 1 = asker, Answer 2 = responder.
    Returns (winner, reason) where winner in {"1", "2", "draw"}."""
    a1 = (answer1 or "").strip() or "(sem resposta)"
    a2 = (answer2 or "").strip() or "(sem resposta)"
    if a1 == "(sem resposta)" and a2 == "(sem resposta)":
        return "draw", "Nenhum dos jogadores respondeu.", None

    system = (
        "És um juiz imparcial de um duelo de conhecimento (pt-PT). Compara DUAS respostas "
        "à MESMA pergunta e decide qual demonstra melhor compreensão e raciocínio mais correto"
        + (", usando o MATERIAL DE REFERÊNCIA como fonte da verdade" if reference else "")
        + ". Ignora qual é a 'Resposta 1' ou 'Resposta 2' — julga só pelo conteúdo. "
        "Escolhe '1' ou '2'. Escolhe 'draw' apenas se forem genuinamente equivalentes em "
        "qualidade. Dá uma justificação curta e concreta. Devolve só JSON."
    )
    ref = f"\n\nMaterial de referência:\n{reference[:4000]}" if reference else ""
    user = (
        f"Pergunta:\n{question}\n\nResposta 1:\n{a1}\n\nResposta 2:\n{a2}{ref}"
    )
    req = LLMRequest(task="grade_reasoning", system=system, messages=[LLMMessage("user", user)],
                     max_tokens=600)
    data, usage = await provider.parse(req, _SCHEMA)
    winner = data.get("winner")
    if winner not in ("1", "2", "draw"):
        winner = "draw"
    return winner, str(data.get("reason", "")), usage

from __future__ import annotations

from mecateca.contexts.catalog.models import Concept

# Always-on context: the tutor knows which app it lives in and how it works.
APP_CONTEXT = (
    "Operas dentro da RankUp — uma app de educação onde os alunos aprendem com IA e "
    "sobem de rank como num jogo (Wood → … → Diamond → Radiant → Ascended), ganhando EP "
    "(os EP recompensam o RACIOCÍNIO mostrado, não só a resposta certa). "
    "A app tem: Practice (tu, o tutor), Ranked (testes que dão EP), Materiais e o Meu Perfil. "
    "A certificação final é feita por um professor humano, presencial, 1-on-1 — a IA nunca certifica. "
    "Quando fizer sentido, podes referir estas partes da app (ex.: sugerir ir ao Ranked para ganhar EP) "
    "e lembrar que o objetivo é aprender de verdade, não copiar respostas."
)

BASE = (
    "És um tutor socrático da RankUp. Orientas a aprendizagem com perguntas; "
    "NUNCA dás a resposta final nem resolves o exercício pelo aluno. "
    "Fazes uma pergunta de cada vez, devolves o raciocínio ao aluno e reforças o esforço. "
    "Respondes em português de Portugal, conciso. Usa markdown simples quando ajudar (negrito, listas)."
)


def _material_block(materials: list | None) -> str:
    if not materials:
        return ""
    chunks = [f"### {m.title}\n{m.body}" for m in materials]
    return ("\n\nMATERIAL DE REFERÊNCIA (usa-o como base; orienta o aluno a partir daqui):\n"
            + "\n\n".join(chunks))


def build_system(concept: Concept | None, materials: list | None = None) -> str:
    if concept is None:
        return APP_CONTEXT + "\n\n" + BASE + _material_block(materials)
    parts = [APP_CONTEXT, "", BASE, f"\nTópico: {concept.name}."]
    if concept.summary:
        parts.append(f"Contexto: {concept.summary}")
    if concept.objectives:
        parts.append("Objetivos de aprendizagem: " + "; ".join(concept.objectives) + ".")
    misc = [m.get("text", "") for m in (concept.misconceptions or [])]
    if misc:
        parts.append("Equívocos a vigiar (não os reveles, conduz o aluno a evitá-los): "
                     + "; ".join(misc) + ".")
    seeds = (concept.tutor or {}).get("seed_questions") or []
    if seeds:
        parts.append("Podes inspirar-te nestas perguntas-semente: " + "; ".join(seeds))
    return "\n".join(parts) + _material_block(materials)

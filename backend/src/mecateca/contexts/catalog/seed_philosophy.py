"""Permanent seed of original Filosofia tests for the Portuguese 10º/11º/12º
curriculum themes (Aprendizagens Essenciais). Questions are ORIGINAL, written
to cover the official programme structure — not reproduced from any exam.

Idempotent: concepts/tests already present (by key/title) are skipped.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog import service as catalog_service
from mecateca.contexts.catalog.models import Concept, ConceptEdge, Test
from mecateca.contexts.catalog.schemas import AddQuestionIn
from mecateca.contexts.identity.service import get_by_identifier
from mecateca.shared.errors import NotFound

# (key, name, difficulty, [prerequisite keys])
CONCEPTS: list[tuple[str, str, int, list[str]]] = [
    ("fil-natureza", "Natureza e sentido da Filosofia", 1, []),
    ("logica-argumentacao", "Lógica e argumentação", 2, ["fil-natureza"]),
    ("falacias", "Falácias informais", 2, ["logica-argumentacao"]),
    ("accao-liberdade", "Ação humana e liberdade", 2, ["fil-natureza"]),
    ("etica-deontologica", "Ética deontológica (Kant)", 3, ["accao-liberdade"]),
    ("etica-consequencialista", "Consequencialismo (Mill)", 3, ["accao-liberdade"]),
    ("filosofia-politica", "Filosofia política e justiça", 3, ["accao-liberdade"]),
    ("estetica", "Estética e juízo de gosto", 2, ["fil-natureza"]),
    ("conhecimento", "Conhecimento e racionalidade", 2, ["fil-natureza"]),
    ("racionalismo-empirismo", "Racionalismo e empirismo", 3, ["conhecimento"]),
    ("ceticismo", "Ceticismo e justificação", 3, ["conhecimento"]),
    ("estatuto-ciencia", "Estatuto da ciência (Popper/Kuhn)", 3, ["conhecimento"]),
    ("metafisica", "Metafísica e existência", 3, ["fil-natureza"]),
    ("filosofia-religiao", "Filosofia da religião", 3, ["metafisica"]),
    ("fenomenologia-existencialismo", "Fenomenologia e existencialismo", 3, ["conhecimento"]),
    ("filosofia-mente", "Filosofia da mente", 3, ["conhecimento"]),
]


def _mcq(concept, stem, options, ans, why, d=2, ep=30):
    return {"concept": concept, "kind": "mcq", "difficulty": d, "ep_award": ep,
            "stem": stem, "options": options, "answer_index": ans, "why": why}


def _open(concept, prompt, d=2, ep=50):
    return {"concept": concept, "kind": "reasoning", "difficulty": d, "ep_award": ep, "prompt": prompt}


# reference material per theme (original summaries of the official programme),
# linked to each test's open questions so the AI grader is grounded.
MATERIALS: dict[str, str] = {
    "Lógica e Argumentação — síntese":
        "Validade vs. verdade: um argumento é válido quando a conclusão decorre "
        "necessariamente das premissas, independentemente de estas serem de facto "
        "verdadeiras. Um argumento é sólido quando é válido E tem premissas verdadeiras. "
        "Falácias informais frequentes: ad hominem (atacar a pessoa), apelo à autoridade, "
        "falsa causa, petição de princípio (assumir o que se quer provar).",
    "Ética — dever e consequências":
        "Kant (deontologia): o valor moral está em agir por dever segundo o imperativo "
        "categórico; age só segundo a máxima que possas querer universal e trata a "
        "humanidade sempre como fim, nunca apenas como meio. Mill (utilitarismo): uma ação "
        "é correta na medida em que promove a maior felicidade do maior número; a moralidade "
        "avalia-se pelas consequências. Tensão central: regras absolutas vs. resultados.",
    "Política e Estética — justiça e gosto":
        "Rawls: justiça como equidade; na posição original, sob o véu de ignorância (não "
        "sabemos a nossa posição social), escolheríamos princípios justos — liberdades iguais "
        "e o princípio da diferença (desigualdades só se beneficiarem os mais desfavorecidos). "
        "Estética kantiana: o juízo de gosto é desinteressado e singular, mas reclama validade "
        "universal — daí não se reduzir a 'gostos não se discutem'.",
    "Conhecimento — racionalismo, empirismo, ceticismo":
        "Racionalismo (Descartes): dúvida metódica até à certeza do cogito ('penso, logo "
        "existo'); critério das ideias claras e distintas. Empirismo (Hume): todo o "
        "conhecimento deriva de impressões e ideias; a causalidade é hábito; problema da "
        "indução. Ceticismo: questiona a possibilidade de justificação segura do conhecimento.",
    "Estatuto da ciência — Popper e Kuhn":
        "Popper: o que demarca a ciência é a falsificabilidade; a ciência avança por "
        "conjecturas e refutações, nunca por verificação definitiva. Kuhn: a ciência normal "
        "opera dentro de um paradigma; a acumulação de anomalias gera crise e revolução "
        "científica, com mudança de paradigma e alguma incomensurabilidade entre eles.",
    "Metafísica e religião — síntese":
        "Argumentos sobre a existência de Deus: cosmológico (o mundo exige uma causa "
        "primeira), ontológico (do conceito de ser perfeito), teleológico (ordem e "
        "finalidade); contra: o problema do mal. Metafísica: investiga o ser e a existência "
        "para além do que as ciências empíricas descrevem.",
    "Mente e existência — síntese":
        "Problema mente-corpo: dualismo (Descartes — mente e corpo são substâncias "
        "distintas) vs. materialismo/fisicalismo (os estados mentais são estados físicos do "
        "cérebro). Existencialismo (Sartre): a existência precede a essência — não há "
        "natureza humana fixa; somos livres e, por isso, responsáveis, o que gera angústia.",
}

# (title, description, material_title, [questions])
TESTS: list[tuple[str, str, str, list[dict]]] = [
    ("Filosofia 10º — Lógica e Argumentação", "Validade, verdade e falácias (10.º ano)",
     "Lógica e Argumentação — síntese", [
        _mcq("logica-argumentacao",
             "Um argumento dedutivo é válido quando:",
             ["As suas premissas são verdadeiras",
              "Se as premissas forem verdadeiras, a conclusão tem necessariamente de ser verdadeira",
              "A sua conclusão é, de facto, verdadeira",
              "É persuasivo para a maioria das pessoas"],
             1, "Validade é a relação de necessidade entre premissas e conclusão, independente da verdade factual."),
        _mcq("falacias",
             "Atacar quem defende um argumento em vez de avaliar o argumento é a falácia:",
             ["Ad hominem", "Apelo à autoridade", "Falsa causa", "Petição de princípio"],
             0, "Ad hominem desvia a discussão da tese para a pessoa."),
        _open("logica-argumentacao",
              "Distingue 'validade' de 'verdade' num argumento e dá um exemplo, inventado por ti, de um argumento válido cujas premissas sejam falsas.", 2, 55),
    ]),
    ("Filosofia 10º — Ética", "Dever vs. consequências (10.º ano)",
     "Ética — dever e consequências", [
        _mcq("etica-deontologica",
             "Para Kant, uma ação tem valor moral quando é feita:",
             ["Por inclinação ou simpatia", "Por dever, segundo o imperativo categórico",
              "Pelas boas consequências que produz", "Por hábito social"],
             1, "Em Kant o valor moral está no agir por dever, não pelas consequências nem pela inclinação."),
        _open("etica-deontologica",
              "Compara a ética do dever de Kant com o utilitarismo de Mill perante o dilema: é admissível mentir para salvar uma vida? Justifica de ambos os lados.", 3, 70),
        _open("etica-consequencialista",
              "Explica o princípio da maior felicidade de Mill e aponta uma objeção a avaliar a moralidade só pelas consequências.", 3, 60),
    ]),
    ("Filosofia 10º — Política e Estética", "Justiça e juízo de gosto (10.º ano)",
     "Política e Estética — justiça e gosto", [
        _open("filosofia-politica",
              "Explica a ideia do 'véu de ignorância' de Rawls e o que ela pretende garantir na escolha dos princípios de justiça.", 3, 65),
        _open("estetica",
              "O juízo de gosto é subjetivo mas pretende validade universal (Kant). Como defenderias que uma obra é bela sem cair no 'gostos não se discutem'?", 3, 60),
    ]),
    ("Filosofia 11º — Conhecimento e Racionalidade", "Racionalismo, empirismo e ceticismo (11.º ano)",
     "Conhecimento — racionalismo, empirismo, ceticismo", [
        _mcq("racionalismo-empirismo",
             "Para o empirismo de Hume, a origem última do conhecimento está:",
             ["Em ideias inatas da razão", "Na experiência sensível",
              "Na revelação", "Na intuição intelectual pura"],
             1, "O empirismo defende que todo o conhecimento deriva da experiência."),
        _open("racionalismo-empirismo",
              "Explica como Descartes, pela dúvida metódica, chega ao 'penso, logo existo' e porque é que essa certeza resiste à dúvida.", 3, 65),
        _open("ceticismo",
              "O ceticismo radical afirma que não podemos ter conhecimento seguro. Avalia se a própria tese cética é coerente consigo mesma.", 3, 65),
    ]),
    ("Filosofia 11º — Estatuto da Ciência", "Popper e Kuhn (11.º ano)",
     "Estatuto da ciência — Popper e Kuhn", [
        _mcq("estatuto-ciencia",
             "Para Popper, o que demarca uma teoria científica é ela ser:",
             ["Verificável", "Falsificável", "Consensual", "Imediatamente útil"],
             1, "O critério de demarcação de Popper é a falsificabilidade."),
        _open("estatuto-ciencia",
              "Compara o falsificacionismo de Popper com a ideia de paradigmas e revoluções científicas de Kuhn quanto ao modo como a ciência progride.", 3, 70),
    ]),
    ("Filosofia 12º — Metafísica e Religião", "Existência e o problema de Deus (12.º ano)",
     "Metafísica e religião — síntese", [
        _mcq("filosofia-religiao",
             "O argumento cosmológico para a existência de Deus parte sobretudo:",
             ["Da ideia de perfeição", "Da existência e causalidade do mundo",
              "Da ordem e finalidade da natureza", "De uma experiência mística"],
             1, "O argumento cosmológico parte da existência/causalidade do mundo para uma causa primeira."),
        _open("filosofia-religiao",
              "Apresenta um argumento a favor e um contra a existência de Deus e avalia, com razões, qual te parece mais forte.", 3, 70),
        _open("metafisica",
              "Que diferença há entre perguntar 'o que existe?' e 'o que é existir?'. Ilustra porque a metafísica não se reduz às ciências.", 3, 65),
    ]),
    ("Filosofia 12º — Mente e Existência", "Mente-corpo e existencialismo (12.º ano)",
     "Mente e existência — síntese", [
        _open("filosofia-mente",
              "Expõe o problema mente-corpo: explica a posição dualista e formula uma objeção materialista a essa posição.", 3, 70),
        _open("fenomenologia-existencialismo",
              "Sartre afirma que 'a existência precede a essência'. Explica o que significa e que tipo de responsabilidade isso implica para o ser humano.", 3, 70),
    ]),
]


# test title -> (primary concept key, material title) from the seed definition
_TITLE_INFO = {title: (questions[0]["concept"], mat_title) for title, _d, mat_title, questions in TESTS}

_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["mcq", "reasoning"]},
                    "prompt": {"type": "string"},
                    "stem": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer_index": {"type": "integer"},
                    "why": {"type": "string"},
                },
                "required": ["kind"],
            },
        }
    },
    "required": ["questions"],
}


async def fill_questions(db: AsyncSession, provider, target: int = 100, batch: int = 10) -> dict:
    """Top every Filosofia test up to `target` original questions via the LLM,
    grounded on the test's reference material. Idempotent: skips tests already full."""
    from mecateca.adapters.llm.base import LLMMessage, LLMRequest
    from mecateca.contexts.catalog.models import Material, QuestionTemplate, Test
    from mecateca.contexts.identity.service import get_by_identifier

    try:
        sv = await catalog_service.current_version(db, "philosophy")
    except NotFound:
        return {"skipped": "philosophy not loaded"}
    admin = await get_by_identifier(db, "admin")  # noqa: F841 (kept for parity)

    tests = list((await db.execute(select(Test).where(Test.subject_version_id == sv.id))).scalars())
    report: dict = {}
    for t in tests:
        qs = list((await db.execute(
            select(QuestionTemplate).where(QuestionTemplate.test_id == t.id)
        )).scalars())
        if len(qs) >= target:
            report[t.title] = len(qs)
            continue
        # concept + material from the seed definition (by title), independent of existing questions
        info = _TITLE_INFO.get(t.title)
        concept = None
        if qs and qs[0].concept_id:
            concept = await db.get(Concept, qs[0].concept_id)
        if concept is None and info:
            concept = (await db.execute(select(Concept).where(
                Concept.subject_version_id == sv.id, Concept.key == info[0]))).scalar_one_or_none()
        if concept is None:
            report[t.title] = f"no concept ({len(qs)})"
            continue
        material = None
        mid = next((q.material_id for q in qs if q.material_id), None)
        if mid:
            material = await db.get(Material, mid)
        elif info:
            material = (await db.execute(select(Material).where(
                Material.subject_version_id == sv.id, Material.title == info[1]))).scalar_one_or_none()
        ref = (material.body if material else "")[:4000]

        seen = set()
        for q in qs:
            key = (q.payload.get("prompt") or q.payload.get("stem") or "").strip().lower()
            if key:
                seen.add(key)

        system = (
            "És um professor de Filosofia (programa português, 10.º–12.º). Geras perguntas "
            "ORIGINAIS em português de Portugal sobre o tema dado, com dificuldade variada. "
            "Mistura 'mcq' (escolha múltipla: stem + 4 options + answer_index 0-3 + why) e "
            "'reasoning' (pergunta aberta: prompt). NUNCA repitas perguntas. Devolve só JSON."
        )
        rounds = 0
        while len(seen) < target and rounds < (target // batch) + 8:
            rounds += 1
            n = min(batch, target - len(seen))
            user = (f"Tema: {t.title} — {concept.name}.\nMaterial de referência:\n{ref}\n\n"
                    f"Gera {n} perguntas novas, diferentes das anteriores.")
            try:
                out, _u = await provider.parse(
                    LLMRequest(task="generate_question", system=system,
                               messages=[LLMMessage("user", user)], max_tokens=2000),
                    _BATCH_SCHEMA,
                )
            except Exception:
                break
            added = 0
            for q in (out or {}).get("questions", []):
                kind = q.get("kind")
                text = (q.get("prompt") or q.get("stem") or "").strip()
                k = text.lower()
                if not text or k in seen:
                    continue
                if kind == "mcq":
                    opts = [o for o in (q.get("options") or []) if o]
                    ai = q.get("answer_index")
                    if len(opts) < 2 or ai is None or ai >= len(opts):
                        continue
                    data = AddQuestionIn(concept=concept.key, kind="mcq", difficulty=2, ep_award=30,
                                         stem=q.get("stem", ""), options=opts, answer_index=ai, why=q.get("why", ""))
                else:
                    data = AddQuestionIn(concept=concept.key, kind="reasoning", difficulty=2, ep_award=50,
                                         prompt=text, material=str(material.id) if material else None)
                await catalog_service._create_question(db, sv.id, data, test_id=t.id)
                seen.add(k); added += 1
            await db.flush()
            if added == 0:
                break
        report[t.title] = len(seen)
    return report


async def seed(db: AsyncSession) -> dict:
    """Idempotently insert curriculum concepts + original tests into Filosofia."""
    try:
        sv = await catalog_service.current_version(db, "philosophy")
    except NotFound:
        return {"skipped": "philosophy subject not loaded"}

    admin = await get_by_identifier(db, "admin")
    created_by = admin.id if admin else None

    # ---- concepts ----
    existing = {c.key: c for c in (
        await db.execute(select(Concept).where(Concept.subject_version_id == sv.id))
    ).scalars()}
    new_concepts = 0
    for key, name, diff, _pre in CONCEPTS:
        if key in existing:
            continue
        c = Concept(subject_version_id=sv.id, key=key, name=name, summary="",
                    difficulty=diff, objectives=[], misconceptions=[], tutor={})
        db.add(c)
        existing[key] = c
        new_concepts += 1
    await db.flush()

    # ---- prerequisite edges ----
    have_edges = {
        (e.parent_concept_id, e.child_concept_id) for e in (
            await db.execute(select(ConceptEdge).where(ConceptEdge.subject_version_id == sv.id))
        ).scalars()
    }
    for key, _n, _d, prereqs in CONCEPTS:
        child = existing.get(key)
        for p in prereqs:
            parent = existing.get(p)
            if parent and child and (parent.id, child.id) not in have_edges:
                db.add(ConceptEdge(subject_version_id=sv.id,
                                   parent_concept_id=parent.id, child_concept_id=child.id))
                have_edges.add((parent.id, child.id))
    await db.flush()
    if new_concepts:
        await catalog_service.rebuild_closure(db, sv.id)

    # ---- reference material (idempotent by title) ----
    from mecateca.contexts.catalog.models import Material
    mat_by_title = {m.title: m for m in (
        await db.execute(select(Material).where(Material.subject_version_id == sv.id))
    ).scalars()}
    new_materials = 0
    for mtitle, mbody in MATERIALS.items():
        if mtitle in mat_by_title:
            continue
        m = Material(subject_version_id=sv.id, title=mtitle, body=mbody,
                     created_by=created_by, teacher_approved=True)
        db.add(m)
        mat_by_title[mtitle] = m
        new_materials += 1
    await db.flush()

    # ---- tests + questions (open questions grounded on the theme material) ----
    have_titles = {t.title for t in (
        await db.execute(select(Test).where(Test.subject_version_id == sv.id))
    ).scalars()}
    new_tests = 0
    for title, desc, mat_title, questions in TESTS:
        if title in have_titles:
            continue
        mat = mat_by_title.get(mat_title)
        t = Test(subject_version_id=sv.id, title=title, description=desc,
                 created_by=created_by, teacher_approved=True, is_public=True, ai_generated=False)
        db.add(t)
        await db.flush()
        for q in questions:
            material = str(mat.id) if (mat and q["kind"] != "mcq") else None
            await catalog_service._create_question(
                db, sv.id,
                AddQuestionIn(concept=q["concept"], kind=q["kind"], difficulty=q["difficulty"],
                              ep_award=q.get("ep_award"), ep_wrong=q.get("ep_wrong", 0),
                              stem=q.get("stem"), options=q.get("options", []),
                              answer_index=q.get("answer_index"), why=q.get("why", ""),
                              prompt=q.get("prompt"), material=material),
                test_id=t.id,
            )
        new_tests += 1
    return {"concepts_added": new_concepts, "materials_added": new_materials, "tests_added": new_tests}

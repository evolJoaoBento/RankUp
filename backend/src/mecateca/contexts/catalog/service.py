from __future__ import annotations

import uuid

import re

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog.models import (
    Concept,
    ConceptClosure,
    ConceptEdge,
    Material,
    MaterialAsset,
    MaterialFavorite,
    QuestionTemplate,
    Rubric,
    Subject,
    SubjectVersion,
    Test,
)
from mecateca.shared.errors import AppError, Conflict, NotFound

_DEFAULT_RUBRIC = [
    {"key": "understanding", "weight": 0.4, "descriptor": "Identifica o conceito central"},
    {"key": "reasoning", "weight": 0.4, "descriptor": "Justifica com raciocínio próprio"},
    {"key": "application", "weight": 0.2, "descriptor": "Aplica a um caso novo"},
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


async def get_subject(db: AsyncSession, key: str) -> Subject:
    row = (await db.execute(select(Subject).where(Subject.key == key))).scalar_one_or_none()
    if row is None:
        raise NotFound(f"subject '{key}' not found")
    return row


async def current_version(db: AsyncSession, key: str) -> SubjectVersion:
    subject = await get_subject(db, key)
    if subject.current_version_id is None:
        raise NotFound(f"subject '{key}' has no active version")
    sv = await db.get(SubjectVersion, subject.current_version_id)
    if sv is None:
        raise NotFound("active version missing")
    return sv


async def list_subjects(db: AsyncSession) -> list[Subject]:
    return list((await db.execute(select(Subject))).scalars())


async def get_concept(db: AsyncSession, concept_id: uuid.UUID) -> Concept:
    row = await db.get(Concept, concept_id)
    if row is None:
        raise NotFound("concept not found")
    return row


async def concept_by_key(db: AsyncSession, sv_id, key: str) -> Concept:
    c = (
        await db.execute(
            select(Concept).where(Concept.subject_version_id == sv_id, Concept.key == key)
        )
    ).scalar_one_or_none()
    if c is None:
        raise NotFound(f"concept '{key}' not in subject")
    return c


# ---------- admin content management ----------


async def create_subject(db: AsyncSession, key: str, name: str, profile: str, icon: str = "") -> SubjectVersion:
    if (await db.execute(select(Subject).where(Subject.key == key))).scalar_one_or_none():
        raise Conflict(f"subject '{key}' already exists")
    subject = Subject(key=key, name=name, icon=icon)
    db.add(subject)
    await db.flush()
    sv = SubjectVersion(
        subject_id=subject.id, version="1.0.0", locale="pt-PT", progression_profile=profile
    )
    db.add(sv)
    await db.flush()
    subject.current_version_id = sv.id
    await db.flush()
    return sv


async def update_subject(db: AsyncSession, key: str, name: str | None, icon: str | None) -> Subject:
    s = await get_subject(db, key)
    if name is not None:
        s.name = name
    if icon is not None:
        s.icon = icon
    await db.flush()
    return s


async def rebuild_closure(db: AsyncSession, sv_id) -> None:
    concepts = list((await db.execute(select(Concept).where(Concept.subject_version_id == sv_id))).scalars())
    edges = list((await db.execute(select(ConceptEdge).where(ConceptEdge.subject_version_id == sv_id))).scalars())
    ids = [c.id for c in concepts]
    if ids:
        await db.execute(delete(ConceptClosure).where(ConceptClosure.descendant_id.in_(ids)))
    parents: dict = {}
    for e in edges:
        parents.setdefault(e.child_concept_id, set()).add(e.parent_concept_id)

    def ancestors(cid, seen):
        out = set()
        for p in parents.get(cid, set()):
            if p in seen:
                continue
            seen.add(p); out.add(p); out |= ancestors(p, seen)
        return out

    rows = []
    for cid in ids:
        rows.append(ConceptClosure(ancestor_id=cid, descendant_id=cid, depth=0))
        for anc in ancestors(cid, set()):
            rows.append(ConceptClosure(ancestor_id=anc, descendant_id=cid, depth=1))
    db.add_all(rows)
    await db.flush()


async def add_concept(db: AsyncSession, subject_key: str, data) -> Concept:
    sv = await current_version(db, subject_key)
    if (await db.execute(
        select(Concept).where(Concept.subject_version_id == sv.id, Concept.key == data.key)
    )).scalar_one_or_none():
        raise Conflict(f"concept '{data.key}' already exists")
    concept = Concept(
        subject_version_id=sv.id, key=data.key, name=data.name, summary=data.summary,
        difficulty=data.difficulty, objectives=data.objectives, misconceptions=[], tutor={},
    )
    db.add(concept)
    await db.flush()
    for pre in data.prerequisites:
        parent = await concept_by_key(db, sv.id, pre)
        db.add(ConceptEdge(subject_version_id=sv.id, parent_concept_id=parent.id, child_concept_id=concept.id))
    await db.flush()
    await rebuild_closure(db, sv.id)
    return concept


async def add_material(db: AsyncSession, subject_key: str, data, user) -> Material:
    sv = await current_version(db, subject_key)
    concept_id = None
    if data.concept:
        concept_id = (await concept_by_key(db, sv.id, data.concept)).id
    approved = user.role in ("teacher", "admin")  # teacher-submitted = auto-approved
    m = Material(
        subject_version_id=sv.id, concept_id=concept_id, title=data.title, body=data.body,
        created_by=user.id, teacher_approved=approved, approved_by=user.id if approved else None,
    )
    db.add(m)
    await db.flush()
    return m


async def approve_material(db: AsyncSession, material_id, approver) -> Material:
    """Teacher/admin approves a student-submitted material (route enforces role)."""
    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material not found")
    m.teacher_approved = True
    m.approved_by = approver.id
    await db.flush()
    return m


async def list_material(db: AsyncSession, subject_key: str, concept_key: str | None = None) -> list[Material]:
    sv = await current_version(db, subject_key)
    q = select(Material).where(Material.subject_version_id == sv.id).order_by(Material.created_at)
    if concept_key:
        c = await concept_by_key(db, sv.id, concept_key)
        q = q.where(Material.concept_id == c.id)
    return list((await db.execute(q)).scalars())


async def favorites_for(db: AsyncSession, user_id, material_ids: list) -> set:
    ids = [i for i in material_ids if i]
    if not ids:
        return set()
    rows = (await db.execute(
        select(MaterialFavorite.material_id).where(
            MaterialFavorite.user_id == user_id, MaterialFavorite.material_id.in_(ids)
        )
    )).scalars()
    return set(rows)


async def toggle_favorite(db: AsyncSession, user_id, material_id) -> bool:
    fav = await db.get(MaterialFavorite, (user_id, material_id))
    if fav:
        await db.delete(fav); await db.flush(); return False
    if await db.get(Material, material_id) is None:
        raise NotFound("material not found")
    db.add(MaterialFavorite(user_id=user_id, material_id=material_id))
    await db.flush()
    return True


# ---------- tests marketplace ----------


async def create_test(db: AsyncSession, subject_key: str, data, user) -> Test:
    sv = await current_version(db, subject_key)
    approved = user.role in ("teacher", "admin")
    t = Test(
        subject_version_id=sv.id, title=data.title, description=data.description,
        created_by=user.id, teacher_approved=approved, approved_by=user.id if approved else None,
        is_public=getattr(data, "is_public", False),
    )
    db.add(t)
    await db.flush()
    return t


async def get_test(db: AsyncSession, test_id) -> Test:
    t = await db.get(Test, test_id)
    if t is None:
        raise NotFound("test not found")
    return t


async def set_test_visibility(db: AsyncSession, test_id, is_public: bool, user) -> Test:
    t = await get_test(db, test_id)
    if user.role != "admin" and t.created_by != user.id:
        from mecateca.shared.errors import Forbidden
        raise Forbidden("not your test")
    t.is_public = is_public
    await db.flush()
    return t


async def list_tests(db: AsyncSession, subject_key: str, user) -> list[tuple[Test, int]]:
    from sqlalchemy import func, or_
    sv = await current_version(db, subject_key)
    q = (
        select(Test, func.count(QuestionTemplate.id))
        .outerjoin(QuestionTemplate, QuestionTemplate.test_id == Test.id)
        .where(Test.subject_version_id == sv.id)
        .group_by(Test.id)
        .order_by(Test.created_at.desc())
    )
    if user.role != "admin":  # students/teachers: public, or own private drafts
        q = q.where(or_(Test.is_public.is_(True), Test.created_by == user.id))
    rows = (await db.execute(q)).all()
    return [(t, int(n)) for t, n in rows]


async def generate_test(db: AsyncSession, subject_key: str, data, user, provider) -> tuple[Test, int]:
    """AI-generate a private draft test of reasoning questions about a topic."""
    from mecateca.adapters.llm.base import LLMMessage, LLMRequest
    from mecateca.contexts.catalog.schemas import AddQuestionIn

    sv = await current_version(db, subject_key)
    concepts = list((await db.execute(select(Concept).where(Concept.subject_version_id == sv.id))).scalars())
    if not concepts:
        raise AppError("a disciplina ainda não tem conceitos")
    concept = next((c for c in concepts if c.key == data.concept), concepts[0])
    n = max(1, min(8, data.count))

    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]},
            }
        },
        "required": ["questions"],
    }
    system = (
        "És um professor que cria perguntas de raciocínio (pt-PT). "
        f"Gera exatamente {n} perguntas abertas, profundas, sobre o tópico dado. "
        "Cada pergunta exige raciocínio próprio, não factos. Devolve só JSON."
    )
    req = LLMRequest(task="generate_question", system=system,
                     messages=[LLMMessage("user", f"Tópico: {data.topic}\nConceito: {concept.name}")],
                     max_tokens=1200)
    out, _usage = await provider.parse(req, schema)
    qs = (out or {}).get("questions", [])[:n]
    if not qs:
        raise AppError("a IA não devolveu perguntas")

    _approved = user.role in ("teacher", "admin")
    t = Test(
        subject_version_id=sv.id, title=data.topic,
        description=f"{concept.name}",
        created_by=user.id, teacher_approved=_approved, approved_by=user.id if _approved else None,
        is_public=False, ai_generated=True,
    )
    db.add(t)
    await db.flush()
    for q in qs:
        prompt = (q.get("prompt") or "").strip()
        if not prompt:
            continue
        await _create_question(
            db, sv.id,
            AddQuestionIn(concept=concept.key, kind="reasoning", difficulty=data.difficulty,
                          prompt=prompt, ep_award=50, ep_wrong=0),
            test_id=t.id,
        )
    cnt = len([q for q in qs if (q.get("prompt") or "").strip()])
    return t, cnt


async def material_test_links(db: AsyncSession, material_ids: list) -> dict:
    ids = [i for i in material_ids if i]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(QuestionTemplate.material_id, Test.title)
            .join(Test, Test.id == QuestionTemplate.test_id)
            .where(QuestionTemplate.material_id.in_(ids))
        )
    ).all()
    out: dict = {}
    for mid, title in rows:
        out.setdefault(mid, set()).add(title)
    return {k: sorted(v) for k, v in out.items()}


async def test_material_links(db: AsyncSession, test_ids: list) -> dict:
    """test_id -> [(material_id, title)] deduped."""
    ids = [i for i in test_ids if i]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(QuestionTemplate.test_id, Material.id, Material.title)
            .join(Material, Material.id == QuestionTemplate.material_id)
            .where(QuestionTemplate.test_id.in_(ids))
        )
    ).all()
    out: dict = {}
    for tid, mid, title in rows:
        out.setdefault(tid, {})[mid] = title
    return {k: list(v.items()) for k, v in out.items()}


def _upload_root():
    from pathlib import Path
    from mecateca.config import get_settings
    root = Path(get_settings().upload_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[4] / root  # backend/<upload_dir>
    return root


def _detect_kind(filename: str, content_type: str) -> str:
    f = filename.lower()
    if f.endswith((".md", ".markdown")) or "markdown" in content_type:
        return "markdown"
    if f.endswith(".pdf") or content_type == "application/pdf":
        return "pdf"
    return "file"


def _extract_text(kind: str, data: bytes) -> str:
    if kind == "markdown":
        return data.decode("utf-8", "ignore")[:20000]
    if kind == "pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)[:20000]
        except Exception:
            return ""
    return ""


async def add_asset(db: AsyncSession, material_id, filename: str, content_type: str, data: bytes, user) -> "MaterialAsset":
    import re as _re

    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material not found")
    if user.role != "admin" and m.created_by != user.id:
        from mecateca.shared.errors import Forbidden
        raise Forbidden("not your material")
    kind = _detect_kind(filename, content_type)
    asset = MaterialAsset(material_id=m.id, kind=kind, filename=filename[:255],
                          content_type=content_type[:128], size=len(data), storage_path="",
                          extracted_text=_extract_text(kind, data))
    db.add(asset)
    await db.flush()  # get id
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "file"
    rel = f"{m.id}/{asset.id}__{safe}"
    dest = _upload_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    asset.storage_path = rel
    await db.flush()
    return asset


async def list_assets(db: AsyncSession, material_id) -> list["MaterialAsset"]:
    return list((await db.execute(
        select(MaterialAsset).where(MaterialAsset.material_id == material_id).order_by(MaterialAsset.created_at)
    )).scalars())


async def get_asset(db: AsyncSession, material_id, asset_id) -> "MaterialAsset":
    a = await db.get(MaterialAsset, asset_id)
    if a is None or a.material_id != material_id:
        raise NotFound("asset not found")
    return a


async def delete_asset(db: AsyncSession, material_id, asset_id, user) -> None:
    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material not found")
    if user.role != "admin" and m.created_by != user.id:
        from mecateca.shared.errors import Forbidden
        raise Forbidden("not your material")
    a = await get_asset(db, material_id, asset_id)
    try:
        (_upload_root() / a.storage_path).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(a)
    await db.flush()


async def material_full_text(db: AsyncSession, material: Material) -> str:
    """Body + extracted text of all attachments — used to ground tutoring/grading."""
    parts = [material.body or ""]
    for a in await list_assets(db, material.id):
        if a.extracted_text:
            parts.append(f"[{a.filename}]\n{a.extracted_text}")
    return "\n\n".join(p for p in parts if p.strip())


async def update_material(db: AsyncSession, material_id, data, user) -> Material:
    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material not found")
    if user.role != "admin" and m.created_by != user.id:
        from mecateca.shared.errors import Forbidden
        raise Forbidden("not your material")
    if data.title is not None:
        m.title = data.title
    if data.body is not None:
        m.body = data.body
    await db.flush()
    return m


def _own_or_admin(t, user):
    if user.role != "admin" and t.created_by != user.id:
        from mecateca.shared.errors import Forbidden
        raise Forbidden("not your test")


async def add_test_question(db: AsyncSession, test_id, data, user) -> QuestionTemplate:
    t = await get_test(db, test_id)
    _own_or_admin(t, user)
    return await _create_question(db, t.subject_version_id, data, test_id=t.id)


async def test_cards(db: AsyncSession, test_id) -> tuple[Test, list[dict]]:
    """Question fronts for flashcard practice — answers stripped."""
    t = await get_test(db, test_id)
    qs = list((await db.execute(
        select(QuestionTemplate).where(QuestionTemplate.test_id == t.id).order_by(QuestionTemplate.created_at)
    )).scalars())
    cards = []
    for q in qs:
        p = q.payload or {}
        cards.append({"id": q.id, "kind": q.kind,
                      "text": p.get("prompt") or p.get("stem") or "",
                      "options": p.get("options", []) if q.kind == "mcq" else []})
    return t, cards


async def test_full(db: AsyncSession, test_id, user) -> tuple[Test, list[tuple[QuestionTemplate, str | None]]]:
    t = await get_test(db, test_id)
    _own_or_admin(t, user)
    qs = list((await db.execute(
        select(QuestionTemplate).where(QuestionTemplate.test_id == t.id).order_by(QuestionTemplate.created_at)
    )).scalars())
    # concept id -> key
    cids = {q.concept_id for q in qs}
    keys = {}
    if cids:
        for c in (await db.execute(select(Concept).where(Concept.id.in_(cids)))).scalars():
            keys[c.id] = c.key
    return t, [(q, keys.get(q.concept_id)) for q in qs]


async def update_test_meta(db: AsyncSession, test_id, data, user) -> Test:
    t = await get_test(db, test_id)
    _own_or_admin(t, user)
    if data.is_public is not None:
        t.is_public = data.is_public
    if data.title is not None:
        t.title = data.title
    if data.description is not None:
        t.description = data.description
    await db.flush()
    return t


async def update_question(db: AsyncSession, test_id, qid, data, user) -> QuestionTemplate:
    import uuid as _uuid

    t = await get_test(db, test_id)
    _own_or_admin(t, user)
    q = await db.get(QuestionTemplate, qid)
    if q is None or q.test_id != t.id:
        raise NotFound("question not in test")
    concept = await concept_by_key(db, t.subject_version_id, data.concept)
    q.concept_id = concept.id
    q.kind = data.kind
    q.difficulty = data.difficulty
    q.ep_award = data.ep_award
    q.ep_wrong = data.ep_wrong
    if data.kind == "mcq":
        if data.answer_index is None or not data.options:
            raise AppError("mcq needs options and answer_index")
        q.payload = {"stem": data.stem or "", "options": data.options,
                     "answer_index": data.answer_index, "why": data.why}
        q.rubric_id = None
    else:
        q.payload = {"prompt": data.prompt or data.stem or ""}
        if q.rubric_id is None:  # ensure a rubric exists for AI grading
            r = Rubric(subject_version_id=t.subject_version_id,
                       key=f"r-{_slug(data.concept)}-{_uuid.uuid4().hex[:6]}", criteria=_DEFAULT_RUBRIC)
            db.add(r); await db.flush(); q.rubric_id = r.id
    q.material_id = _uuid.UUID(data.material) if data.material else None
    await db.flush()
    return q


async def delete_question(db: AsyncSession, test_id, qid, user) -> None:
    t = await get_test(db, test_id)
    _own_or_admin(t, user)
    q = await db.get(QuestionTemplate, qid)
    if q is None or q.test_id != t.id:
        raise NotFound("question not in test")
    await db.delete(q)
    await db.flush()


async def add_question(db: AsyncSession, subject_key: str, data) -> QuestionTemplate:
    sv = await current_version(db, subject_key)
    return await _create_question(db, sv.id, data)


async def _create_question(db: AsyncSession, sv_id, data, test_id=None) -> QuestionTemplate:
    import uuid as _uuid

    sv = await db.get(SubjectVersion, sv_id)
    concept = await concept_by_key(db, sv.id, data.concept)

    rubric_id = None
    if data.kind in ("reasoning", "short"):
        crit = data.rubric or _DEFAULT_RUBRIC
        r = Rubric(subject_version_id=sv.id, key=f"r-{_slug(data.concept)}-{_uuid.uuid4().hex[:6]}", criteria=crit)
        db.add(r); await db.flush(); rubric_id = r.id

    if data.kind == "mcq":
        if data.answer_index is None or not data.options:
            raise AppError("mcq needs options and answer_index")
        payload = {"stem": data.stem or "", "options": data.options,
                   "answer_index": data.answer_index, "why": data.why}
    else:
        payload = {"prompt": data.prompt or data.stem or ""}

    mat_id = None
    if data.material:
        try:
            mat_id = _uuid.UUID(data.material)
        except ValueError:
            raise AppError("invalid material id")

    q = QuestionTemplate(
        subject_version_id=sv.id, key=f"q-{_slug(data.concept)}-{_uuid.uuid4().hex[:6]}",
        concept_id=concept.id, kind=data.kind, difficulty=data.difficulty,
        source="static", payload=payload, rubric_id=rubric_id,
        ep_award=data.ep_award, ep_wrong=data.ep_wrong, material_id=mat_id, test_id=test_id,
    )
    db.add(q)
    await db.flush()
    return q


async def graph(db: AsyncSession, key: str) -> tuple[SubjectVersion, list[Concept], list[ConceptEdge]]:
    sv = await current_version(db, key)
    concepts = list(
        (await db.execute(select(Concept).where(Concept.subject_version_id == sv.id))).scalars()
    )
    edges = list(
        (await db.execute(select(ConceptEdge).where(ConceptEdge.subject_version_id == sv.id))).scalars()
    )
    return sv, concepts, edges

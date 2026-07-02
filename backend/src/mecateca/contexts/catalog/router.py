from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog import pack_loader, service
from mecateca.contexts.catalog.schemas import (
    AddConceptIn,
    AddMaterialIn,
    AddQuestionIn,
    CardOut,
    ConceptOut,
    CreateSubjectIn,
    CreateTestIn,
    EdgeOut,
    GenerateTestIn,
    GraphOut,
    MaterialAssetOut,
    MaterialOut,
    MaterialRef,
    PatchMaterialIn,
    PatchSubjectIn,
    PatchTestIn,
    QuestionFullOut,
    QuestionOut,
    SubjectOut,
    TestFullOut,
    TestOut,
)
from mecateca.contexts.identity.models import User
from mecateca.db.session import get_db
from mecateca.deps import current_user, get_llm_provider, require_role
from mecateca.shared.errors import NotFound


async def _authors(db: AsyncSession, ids: list) -> dict:
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    from sqlalchemy import select as _select
    rows = (await db.execute(_select(User.id, User.display_name).where(User.id.in_(ids)))).all()
    return {i: n for i, n in rows}

router = APIRouter(tags=["catalog"])


def _subject_out(subject, version) -> SubjectOut:
    return SubjectOut(
        key=subject.key,
        name=subject.name,
        version=version.version if version else None,
        locale=version.locale if version else None,
        icon=subject.icon or None,
    )


@router.get("/subjects", response_model=list[SubjectOut], dependencies=[Depends(current_user)])
async def list_subjects(db: AsyncSession = Depends(get_db)):
    from mecateca.contexts.catalog.models import SubjectVersion

    out = []
    for s in await service.list_subjects(db):
        sv = await db.get(SubjectVersion, s.current_version_id) if s.current_version_id else None
        out.append(
            SubjectOut(
                key=s.key,
                name=s.name,
                version=getattr(sv, "version", None),
                locale=getattr(sv, "locale", None),
                icon=s.icon or None,
            )
        )
    return out


@router.get("/subjects/{key}", response_model=SubjectOut, dependencies=[Depends(current_user)])
async def get_subject(key: str, db: AsyncSession = Depends(get_db)):
    subject = await service.get_subject(db, key)
    sv = await service.current_version(db, key)
    return _subject_out(subject, sv)


@router.get("/subjects/{key}/graph", response_model=GraphOut, dependencies=[Depends(current_user)])
async def get_graph(key: str, db: AsyncSession = Depends(get_db)):
    sv, concepts, edges = await service.graph(db, key)
    return GraphOut(
        subject=key,
        version=sv.version,
        concepts=[
            ConceptOut(
                id=c.id, key=c.key, name=c.name, summary=c.summary,
                difficulty=c.difficulty, objectives=c.objectives,
            )
            for c in concepts
        ],
        edges=[EdgeOut(parent=e.parent_concept_id, child=e.child_concept_id) for e in edges],
    )


@router.get("/concepts/{concept_id}", response_model=ConceptOut, dependencies=[Depends(current_user)])
async def get_concept(concept_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    c = await service.get_concept(db, concept_id)
    return ConceptOut(
        id=c.id, key=c.key, name=c.name, summary=c.summary,
        difficulty=c.difficulty, objectives=c.objectives,
    )


def _mat_out(m, authors, favs=None) -> MaterialOut:
    return MaterialOut(id=m.id, title=m.title, body=m.body, concept_id=m.concept_id,
                       teacher_approved=m.teacher_approved, author=authors.get(m.created_by),
                       approver=authors.get(m.approved_by) if m.approved_by else None,
                       favorited=m.id in (favs or set()))


# ---- material marketplace (anyone can add; teacher = approved) ----
@router.get("/subjects/{key}/material", response_model=list[MaterialOut])
async def list_material(key: str, concept: str | None = None, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    mats = await service.list_material(db, key, concept)
    authors = await _authors(db, [m.created_by for m in mats] + [m.approved_by for m in mats])
    favs = await service.favorites_for(db, user.id, [m.id for m in mats])
    return [_mat_out(m, authors, favs) for m in mats]


@router.post("/materials/{material_id}/approve", response_model=MaterialOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def approve_material(material_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    m = await service.approve_material(db, material_id, user)
    authors = await _authors(db, [m.created_by, m.approved_by])
    return _mat_out(m, authors)


@router.post("/subjects/{key}/material", response_model=MaterialOut)
async def add_material(key: str, body: AddMaterialIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    m = await service.add_material(db, key, body, user)
    return _mat_out(m, {user.id: user.display_name})


@router.patch("/materials/{material_id}", response_model=MaterialOut)
async def edit_material(material_id: uuid.UUID, body: PatchMaterialIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    m = await service.update_material(db, material_id, body, user)
    authors = await _authors(db, [m.created_by, m.approved_by])
    return _mat_out(m, authors)


@router.post("/materials/{material_id}/favorite")
async def toggle_favorite(material_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return {"favorited": await service.toggle_favorite(db, user.id, material_id)}


def _asset_out(a) -> MaterialAssetOut:
    return MaterialAssetOut(id=a.id, kind=a.kind, filename=a.filename, content_type=a.content_type, size=a.size)


@router.get("/materials/{material_id}", response_model=MaterialOut)
async def get_material(material_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from mecateca.contexts.catalog.models import Material
    m = await db.get(Material, material_id)
    if m is None:
        raise NotFound("material not found")
    authors = await _authors(db, [m.created_by, m.approved_by])
    favs = await service.favorites_for(db, user.id, [m.id])
    out = _mat_out(m, authors, favs)
    out.assets = [_asset_out(a) for a in await service.list_assets(db, m.id)]
    return out


@router.post("/materials/{material_id}/assets", response_model=MaterialAssetOut)
async def upload_asset(material_id: uuid.UUID, file: UploadFile = File(...),
                       user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from mecateca.config import get_settings
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        from mecateca.shared.errors import AppError
        raise AppError("ficheiro demasiado grande")
    a = await service.add_asset(db, material_id, file.filename or "ficheiro",
                                file.content_type or "", data, user)
    return _asset_out(a)


@router.get("/materials/{material_id}/assets/{asset_id}/download")
async def download_asset(material_id: uuid.UUID, asset_id: uuid.UUID,
                         user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    a = await service.get_asset(db, material_id, asset_id)
    path = service._upload_root() / a.storage_path
    return FileResponse(str(path), filename=a.filename, media_type=a.content_type or "application/octet-stream")


@router.delete("/materials/{material_id}/assets/{asset_id}", status_code=204)
async def remove_asset(material_id: uuid.UUID, asset_id: uuid.UUID,
                       user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.delete_asset(db, material_id, asset_id, user)


# ---- test marketplace (teachers create; students browse) ----
@router.get("/subjects/{key}/tests", response_model=list[TestOut])
async def list_tests(key: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = await service.list_tests(db, key, user)
    authors = await _authors(db, [t.created_by for t, _ in rows] + [t.approved_by for t, _ in rows])
    mats = await service.test_material_links(db, [t.id for t, _ in rows])
    return [TestOut(id=t.id, title=t.title, description=t.description, question_count=n,
                    teacher_approved=t.teacher_approved, is_public=t.is_public,
                    is_mine=(t.created_by == user.id), ai_generated=t.ai_generated,
                    author=authors.get(t.created_by),
                    approver=authors.get(t.approved_by) if t.approved_by else None,
                    materials=[MaterialRef(id=mid, title=tt) for mid, tt in mats.get(t.id, [])]) for t, n in rows]


@router.post("/subjects/{key}/tests", response_model=TestOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def create_test(key: str, body: CreateTestIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    t = await service.create_test(db, key, body, user)
    return TestOut(id=t.id, title=t.title, description=t.description, question_count=0,
                   teacher_approved=t.teacher_approved, is_public=t.is_public, is_mine=True,
                   author=user.display_name, approver=user.display_name if t.approved_by else None)


@router.post("/subjects/{key}/tests/generate", response_model=TestOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def generate_test(key: str, body: GenerateTestIn, user: User = Depends(current_user),
                        provider=Depends(get_llm_provider), db: AsyncSession = Depends(get_db)):
    t, n = await service.generate_test(db, key, body, user, provider)
    return TestOut(id=t.id, title=t.title, description=t.description, question_count=n,
                   teacher_approved=t.teacher_approved, is_public=t.is_public, is_mine=True,
                   ai_generated=t.ai_generated, author=user.display_name,
                   approver=user.display_name if t.approved_by else None)


@router.patch("/tests/{test_id}", response_model=TestOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def patch_test(test_id: uuid.UUID, body: PatchTestIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    t = await service.update_test_meta(db, test_id, body, user)
    return TestOut(id=t.id, title=t.title, description=t.description, question_count=0,
                   teacher_approved=t.teacher_approved, is_public=t.is_public, is_mine=True,
                   ai_generated=t.ai_generated, author=user.display_name,
                   approver=user.display_name if t.approved_by else None)


def _q_full(q, ckey) -> QuestionFullOut:
    p = q.payload or {}
    return QuestionFullOut(
        id=q.id, concept_id=q.concept_id, concept=ckey, kind=q.kind, difficulty=q.difficulty,
        ep_award=q.ep_award, ep_wrong=q.ep_wrong, material_id=q.material_id,
        stem=p.get("stem"), options=p.get("options", []), answer_index=p.get("answer_index"),
        why=p.get("why", ""), prompt=p.get("prompt"),
    )


@router.get("/tests/{test_id}/full", response_model=TestFullOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def get_test_full(test_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    t, qs = await service.test_full(db, test_id, user)
    return TestFullOut(id=t.id, title=t.title, description=t.description, is_public=t.is_public,
                       ai_generated=t.ai_generated, questions=[_q_full(q, ck) for q, ck in qs])


@router.patch("/tests/{test_id}/questions/{qid}", response_model=QuestionOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def edit_test_question(test_id: uuid.UUID, qid: uuid.UUID, body: AddQuestionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    q = await service.update_question(db, test_id, qid, body, user)
    return QuestionOut(id=q.id, key=q.key, concept_id=q.concept_id, kind=q.kind, difficulty=q.difficulty,
                       ep_award=q.ep_award, ep_wrong=q.ep_wrong, material_id=q.material_id)


@router.delete("/tests/{test_id}/questions/{qid}", status_code=204, dependencies=[Depends(require_role("teacher", "admin"))])
async def remove_test_question(test_id: uuid.UUID, qid: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await service.delete_question(db, test_id, qid, user)


@router.get("/tests/{test_id}/cards", response_model=list[CardOut], dependencies=[Depends(current_user)])
async def test_cards(test_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    _t, cards = await service.test_cards(db, test_id)
    return [CardOut(**c) for c in cards]


@router.post("/tests/{test_id}/questions", response_model=QuestionOut, dependencies=[Depends(require_role("teacher", "admin"))])
async def add_test_question(test_id: uuid.UUID, body: AddQuestionIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    q = await service.add_test_question(db, test_id, body, user)
    return QuestionOut(id=q.id, key=q.key, concept_id=q.concept_id, kind=q.kind, difficulty=q.difficulty,
                       ep_award=q.ep_award, ep_wrong=q.ep_wrong, material_id=q.material_id)


# ---- admin: structural (disciplines + concepts) ----
@router.post("/admin/subjects", response_model=SubjectOut, dependencies=[Depends(require_role("admin"))])
async def create_subject(body: CreateSubjectIn, db: AsyncSession = Depends(get_db)):
    sv = await service.create_subject(db, body.key, body.name, body.progression_profile, body.icon)
    return SubjectOut(key=body.key, name=body.name, version=sv.version, locale=sv.locale, icon=body.icon or None)


@router.patch("/admin/subjects/{key}", response_model=SubjectOut, dependencies=[Depends(require_role("admin"))])
async def edit_subject(key: str, body: PatchSubjectIn, db: AsyncSession = Depends(get_db)):
    s = await service.update_subject(db, key, body.name, body.icon)
    sv = await service.current_version(db, key)
    return _subject_out(s, sv)


@router.post("/admin/subjects/{key}/concepts", response_model=ConceptOut, dependencies=[Depends(require_role("admin"))])
async def add_concept(key: str, body: AddConceptIn, db: AsyncSession = Depends(get_db)):
    c = await service.add_concept(db, key, body)
    return ConceptOut(id=c.id, key=c.key, name=c.name, summary=c.summary, difficulty=c.difficulty, objectives=c.objectives)


@router.post("/admin/subjects/import", dependencies=[Depends(require_role("admin"))])
async def import_pack(file: UploadFile, db: AsyncSession = Depends(get_db)):
    import yaml

    from mecateca.contexts.catalog.schemas import SubjectPack

    data = yaml.safe_load((await file.read()).decode("utf-8"))
    sv = await pack_loader.import_pack(db, SubjectPack.model_validate(data))
    return {"subject_version_id": str(sv.id), "version": sv.version}

from __future__ import annotations

import uuid
from pathlib import Path

import yaml
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from mecateca.contexts.catalog.models import (
    Concept,
    ConceptClosure,
    ConceptEdge,
    QuestionTemplate,
    Rubric,
    Subject,
    SubjectVersion,
)
from mecateca.contexts.catalog.schemas import SubjectPack
from mecateca.shared.errors import AppError


def parse_pack(path: str | Path) -> SubjectPack:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SubjectPack.model_validate(data)


async def import_pack(db: AsyncSession, pack: SubjectPack) -> SubjectVersion:
    meta = pack.subject

    subject = (
        await db.execute(select(Subject).where(Subject.key == meta.key))
    ).scalar_one_or_none()
    if subject is None:
        subject = Subject(key=meta.key, name=meta.name)
        db.add(subject)
        await db.flush()

    existing = (
        await db.execute(
            select(SubjectVersion).where(
                SubjectVersion.subject_id == subject.id, SubjectVersion.version == meta.version
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        # idempotent re-import: wipe its content and rebuild
        await _wipe_version(db, existing.id)
        sv = existing
    else:
        sv = SubjectVersion(
            subject_id=subject.id,
            version=meta.version,
            pack_schema_version=pack.pack_schema_version,
            locale=meta.locale,
            progression_profile=meta.progression_profile,
        )
        db.add(sv)
        await db.flush()

    # rubrics
    rubric_ids: dict[str, uuid.UUID] = {}
    for r in pack.rubrics:
        row = Rubric(subject_version_id=sv.id, key=r.key, criteria=r.criteria)
        db.add(row)
        await db.flush()
        rubric_ids[r.key] = row.id

    # concepts
    concept_ids: dict[str, uuid.UUID] = {}
    for c in pack.concepts:
        row = Concept(
            subject_version_id=sv.id,
            key=c.key,
            name=c.name,
            summary=c.summary,
            difficulty=c.difficulty,
            objectives=c.objectives,
            misconceptions=[m.model_dump() for m in c.misconceptions],
            tutor=c.tutor,
        )
        db.add(row)
        await db.flush()
        concept_ids[c.key] = row.id

    # edges
    for c in pack.concepts:
        for pre in c.prerequisites:
            if pre not in concept_ids:
                raise AppError(f"unknown prerequisite '{pre}' for concept '{c.key}'")
            db.add(
                ConceptEdge(
                    subject_version_id=sv.id,
                    parent_concept_id=concept_ids[pre],
                    child_concept_id=concept_ids[c.key],
                )
            )

    # question templates
    for q in pack.question_templates:
        if q.concept not in concept_ids:
            raise AppError(f"unknown concept '{q.concept}' for question '{q.key}'")
        db.add(
            QuestionTemplate(
                subject_version_id=sv.id,
                key=q.key,
                concept_id=concept_ids[q.concept],
                kind=q.kind,
                difficulty=q.difficulty,
                source=q.source,
                payload=q.payload,
                rubric_id=rubric_ids.get(q.rubric) if q.rubric else None,
            )
        )

    await db.flush()
    await _build_closure(db, sv.id, pack, concept_ids)

    # activate this version
    subject.current_version_id = sv.id
    subject.name = meta.name
    await db.flush()
    return sv


async def _wipe_version(db: AsyncSession, sv_id: uuid.UUID) -> None:
    concept_ids = [
        r[0] for r in (await db.execute(select(Concept.id).where(Concept.subject_version_id == sv_id)))
    ]
    if concept_ids:
        await db.execute(delete(ConceptClosure).where(ConceptClosure.ancestor_id.in_(concept_ids)))
    await db.execute(delete(QuestionTemplate).where(QuestionTemplate.subject_version_id == sv_id))
    await db.execute(delete(ConceptEdge).where(ConceptEdge.subject_version_id == sv_id))
    await db.execute(delete(Rubric).where(Rubric.subject_version_id == sv_id))
    await db.execute(delete(Concept).where(Concept.subject_version_id == sv_id))
    await db.flush()


async def _build_closure(
    db: AsyncSession, sv_id: uuid.UUID, pack: SubjectPack, ids: dict[str, uuid.UUID]
) -> None:
    """Transitive closure of the prerequisite DAG (in-memory; small graphs)."""
    adj: dict[str, set[str]] = {c.key: set(c.prerequisites) for c in pack.concepts}

    def ancestors(key: str, seen: set[str]) -> set[str]:
        out: set[str] = set()
        for p in adj.get(key, set()):
            if p in seen:
                continue
            seen.add(p)
            out.add(p)
            out |= ancestors(p, seen)
        return out

    rows: list[ConceptClosure] = []
    for key, cid in ids.items():
        rows.append(ConceptClosure(ancestor_id=cid, descendant_id=cid, depth=0))
        for anc in ancestors(key, set()):
            rows.append(ConceptClosure(ancestor_id=ids[anc], descendant_id=cid, depth=1))
    db.add_all(rows)
    await db.flush()


async def load_from_path(db: AsyncSession, path: str | Path) -> SubjectVersion:
    return await import_pack(db, parse_pack(path))

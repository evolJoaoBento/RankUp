from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mecateca.db.base import Base, PkMixin, TimestampMixin


class Subject(PkMixin, TimestampMixin, Base):
    __tablename__ = "subject"
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    icon: Mapped[str] = mapped_column(String(16), default="")  # emoji shown next to the discipline
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(default=None)


class SubjectVersion(PkMixin, TimestampMixin, Base):
    __tablename__ = "subject_version"
    __table_args__ = (UniqueConstraint("subject_id", "version"),)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subject.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(32))
    pack_schema_version: Mapped[str] = mapped_column(String(16), default="1")
    locale: Mapped[str] = mapped_column(String(8), default="pt-PT")
    progression_profile: Mapped[str] = mapped_column(String(64), default="standard")


class Concept(PkMixin, TimestampMixin, Base):
    __tablename__ = "concept"
    __table_args__ = (UniqueConstraint("subject_version_id", "key"),)
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(2000), default="")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    objectives: Mapped[list] = mapped_column(JSONB, default=list)
    misconceptions: Mapped[list] = mapped_column(JSONB, default=list)
    tutor: Mapped[dict] = mapped_column(JSONB, default=dict)


class ConceptEdge(Base):
    __tablename__ = "concept_edge"
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    parent_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concept.id", ondelete="CASCADE"), primary_key=True
    )
    child_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concept.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="prerequisite")


class ConceptClosure(Base):
    __tablename__ = "concept_closure"
    ancestor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concept.id", ondelete="CASCADE"), primary_key=True
    )
    descendant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("concept.id", ondelete="CASCADE"), primary_key=True
    )
    depth: Mapped[int] = mapped_column(Integer, default=0)


class Rubric(PkMixin, TimestampMixin, Base):
    __tablename__ = "rubric"
    __table_args__ = (UniqueConstraint("subject_version_id", "key"),)
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(64))
    criteria: Mapped[list] = mapped_column(JSONB, default=list)


from sqlalchemy import Boolean


class Material(PkMixin, TimestampMixin, Base):
    """Reference material that informs tutoring and grounds test evaluation."""
    __tablename__ = "material"
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("concept.id", ondelete="SET NULL"), default=None, index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )
    teacher_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )


class MaterialAsset(PkMixin, TimestampMixin, Base):
    """A file attached to a material (pdf/markdown/other). Text is extracted for context."""
    __tablename__ = "material_asset"
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16), default="file")  # markdown | pdf | file
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(512))  # relative to upload_dir
    extracted_text: Mapped[str] = mapped_column(Text, default="")  # markdown / pdf text for grounding


class MaterialFavorite(Base):
    """Per-user favourite materials."""
    __tablename__ = "material_favorite"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material.id", ondelete="CASCADE"), primary_key=True
    )


class Announcement(PkMixin, TimestampMixin, Base):
    """Teacher broadcast for a discipline — shows on every student's Learn view."""

    __tablename__ = "announcement"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )
    text: Mapped[str] = mapped_column(String(500))


class Test(PkMixin, TimestampMixin, Base):
    """A marketplace test = a named set of questions, authored by a teacher."""
    __tablename__ = "test"
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )
    teacher_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # private draft until published
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)


class QuestionTemplate(PkMixin, TimestampMixin, Base):
    __tablename__ = "question_template"
    __table_args__ = (UniqueConstraint("subject_version_id", "key"),)
    subject_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subject_version.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(128))
    concept_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # mcq | short | reasoning
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(16), default="static")  # static | ai
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubric.id", ondelete="SET NULL"), default=None
    )
    ep_award: Mapped[int | None] = mapped_column(Integer, default=None)   # EP on correct (overrides profile base)
    ep_wrong: Mapped[int] = mapped_column(Integer, default=0)             # EP on wrong (can be negative)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("material.id", ondelete="SET NULL"), default=None
    )
    test_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("test.id", ondelete="CASCADE"), default=None, index=True
    )

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

# ---------- Subject Pack schema (the import format) ----------


class PackMisconception(BaseModel):
    id: str
    text: str


class PackConcept(BaseModel):
    key: str
    name: str
    summary: str = ""
    difficulty: int = 1
    prerequisites: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    misconceptions: list[PackMisconception] = Field(default_factory=list)
    tutor: dict = Field(default_factory=dict)


class PackQuestion(BaseModel):
    key: str
    concept: str
    kind: str  # mcq | short | reasoning
    difficulty: int = 1
    source: str = "static"  # static | ai
    payload: dict = Field(default_factory=dict)
    rubric: str | None = None


class PackRubric(BaseModel):
    key: str
    criteria: list[dict]


class PackMeta(BaseModel):
    key: str
    name: str
    version: str
    locale: str = "pt-PT"
    progression_profile: str = "standard"


class SubjectPack(BaseModel):
    subject: PackMeta
    concepts: list[PackConcept]
    question_templates: list[PackQuestion] = Field(default_factory=list)
    rubrics: list[PackRubric] = Field(default_factory=list)
    pack_schema_version: str = "1"


# ---------- API output ----------


class SubjectOut(BaseModel):
    key: str
    name: str
    version: str | None
    locale: str | None
    icon: str | None = None


class ConceptOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    summary: str
    difficulty: int
    objectives: list


class EdgeOut(BaseModel):
    parent: uuid.UUID
    child: uuid.UUID


class GraphOut(BaseModel):
    subject: str
    version: str
    concepts: list[ConceptOut]
    edges: list[EdgeOut]


class ActivateIn(BaseModel):
    version: str


# ---------- admin content management ----------


class CreateSubjectIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    progression_profile: str = "standard"
    icon: str = Field(default="", max_length=16)


class PatchSubjectIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    icon: str | None = Field(default=None, max_length=16)


class AddConceptIn(BaseModel):
    key: str
    name: str
    summary: str = ""
    difficulty: int = 1
    prerequisites: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)


class AddMaterialIn(BaseModel):
    title: str
    body: str
    concept: str | None = None  # concept key, optional


class MaterialAssetOut(BaseModel):
    id: uuid.UUID
    kind: str
    filename: str
    content_type: str
    size: int


class MaterialOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    concept_id: uuid.UUID | None
    teacher_approved: bool = False
    author: str | None = None
    approver: str | None = None
    favorited: bool = False
    assets: list[MaterialAssetOut] = Field(default_factory=list)


class PatchMaterialIn(BaseModel):
    title: str | None = None
    body: str | None = None


class MaterialRef(BaseModel):
    id: uuid.UUID
    title: str


class CardOut(BaseModel):
    id: uuid.UUID
    kind: str                 # mcq | short | reasoning
    text: str                 # the question
    options: list[str] = Field(default_factory=list)  # mcq only


class CreateTestIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    is_public: bool = False


class GenerateTestIn(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    concept: str | None = None     # concept key to attach (else first)
    count: int = Field(3, ge=1, le=15)
    difficulty: int = Field(2, ge=1, le=3)


class PatchTestIn(BaseModel):
    is_public: bool | None = None
    title: str | None = None
    description: str | None = None


class QuestionFullOut(BaseModel):
    id: uuid.UUID
    concept_id: uuid.UUID
    concept: str | None = None   # concept key
    kind: str
    difficulty: int
    ep_award: int | None
    ep_wrong: int
    material_id: uuid.UUID | None
    stem: str | None = None
    options: list[str] = Field(default_factory=list)
    answer_index: int | None = None
    why: str = ""
    prompt: str | None = None


class TestFullOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    is_public: bool
    ai_generated: bool
    questions: list[QuestionFullOut] = Field(default_factory=list)


class TestOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    question_count: int
    teacher_approved: bool
    is_public: bool = False
    is_mine: bool = False
    ai_generated: bool = False
    materials: list[MaterialRef] = Field(default_factory=list)  # materials this test grounds on
    author: str | None = None
    approver: str | None = None


class AddQuestionIn(BaseModel):
    concept: str                      # concept key
    kind: str                         # mcq | reasoning | short
    difficulty: int = 2
    # mcq: stem, options[], answer_index   |   reasoning/short: prompt
    stem: str | None = None
    options: list[str] = Field(default_factory=list)
    answer_index: int | None = None
    why: str = ""
    prompt: str | None = None
    rubric: list[dict] | None = None  # criteria; default applied if omitted for reasoning
    ep_award: int | None = None
    ep_wrong: int = 0
    material: str | None = None       # material id (uuid str) to ground grading


class QuestionOut(BaseModel):
    id: uuid.UUID
    key: str
    concept_id: uuid.UUID
    kind: str
    difficulty: int
    ep_award: int | None
    ep_wrong: int
    material_id: uuid.UUID | None

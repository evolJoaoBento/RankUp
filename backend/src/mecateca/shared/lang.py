from __future__ import annotations

"""User-interface language plumbing for AI output.

The SPA sends its active locale in an `X-Lang` header; endpoints that produce
AI text meant for ONE student (tutor replies, grading feedback) thread it into
the prompt so the AI answers in the student's language. Content shared by two
players (duel judge reasons) stays in the platform default.
"""

SUPPORTED = {"pt", "en"}
DEFAULT = "pt"

_REPLY_LINE = {
    "pt": "Respondes em português de Portugal.",
    "en": "Reply in English.",
}


def norm_lang(raw: str | None) -> str:
    code = (raw or DEFAULT).strip().lower()[:2]
    return code if code in SUPPORTED else DEFAULT


def reply_language_line(lang: str) -> str:
    return _REPLY_LINE.get(lang, _REPLY_LINE[DEFAULT])

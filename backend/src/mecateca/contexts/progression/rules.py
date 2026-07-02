from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass(frozen=True)
class Rank:
    name: str
    xp: int


@dataclass(frozen=True)
class ProgressionProfile:
    key: str
    ranks: tuple[Rank, ...]
    correct_base: int
    streak_bonus_per: int
    reasoning_multiplier: float
    wrong: int

    def xp_for(
        self,
        correct: bool,
        reasoning_score: float,
        streak_after: int,
        base_override: int | None = None,
        wrong_override: int | None = None,
    ) -> int:
        if not correct:
            return wrong_override if wrong_override is not None else self.wrong
        base = base_override if base_override is not None else self.correct_base
        streak_bonus = self.streak_bonus_per * max(0, streak_after - 1)
        reasoning_bonus = round(self.reasoning_multiplier * reasoning_score * base)
        return base + streak_bonus + reasoning_bonus

    def rank_for(self, xp: int) -> str:
        name = self.ranks[0].name
        for r in self.ranks:
            if xp >= r.xp:
                name = r.name
        return name


@lru_cache
def load_profile(key: str) -> ProgressionProfile:
    data = yaml.safe_load((_PROFILES_DIR / f"{key}.yaml").read_text(encoding="utf-8"))
    rules = data["xp_rules"]
    return ProgressionProfile(
        key=data["key"],
        ranks=tuple(Rank(r["name"], int(r["xp"])) for r in data["ranks"]),
        correct_base=int(rules["correct_base"]),
        streak_bonus_per=int(rules["streak_bonus_per"]),
        reasoning_multiplier=float(rules["reasoning_multiplier"]),
        wrong=int(rules["wrong"]),
    )

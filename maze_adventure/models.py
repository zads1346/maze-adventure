from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


Position = tuple[int, int]
Grid = list[list[str]]


@dataclass
class MazeGenerationResult:
    method: str
    grid: Grid
    frames: list[str] = field(default_factory=list)


@dataclass
class ResourcePlan:
    max_value: int
    path: list[Position]
    walk: list[Position]
    collected: set[Position]


@dataclass(frozen=True)
class Skill:
    name: str
    damage: int
    cooldown: int = 0


@dataclass(frozen=True)
class SkillUse:
    round_no: int
    skill: str
    target: int
    damage: int
    remaining_hp: tuple[int, ...]


@dataclass
class BossPlan:
    min_rounds: int
    sequence: list[SkillUse]
    limited_rounds: int
    revive_coin: int


@dataclass
class GreedyDecision:
    target: Optional[Position]
    value: int
    path: list[Position]
    score: float
    visualization: str


@dataclass
class ExplorationResult:
    reached_end: bool
    remaining_value: int
    coins: int
    steps: int
    value_step_ratio: float
    walk: list[Position]
    frames: list[str]
    boss_plan: Optional[BossPlan] = None

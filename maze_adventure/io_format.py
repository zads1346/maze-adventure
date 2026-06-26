from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .core import BOSS, COIN, END, PATH, START, TRAP, WALL
from .models import Grid, Skill


AI_COIN = "G"
AI_PATH = " "

INTERNAL_TO_AI = {
    WALL: WALL,
    PATH: AI_PATH,
    START: START,
    END: END,
    COIN: AI_COIN,
    TRAP: TRAP,
    BOSS: BOSS,
}

AI_TO_INTERNAL = {
    WALL: WALL,
    AI_PATH: PATH,
    PATH: PATH,
    START: START,
    END: END,
    AI_COIN: COIN,
    COIN: COIN,
    TRAP: TRAP,
    BOSS: BOSS,
}


def to_ai_grid(grid: Grid) -> Grid:
    return [[INTERNAL_TO_AI.get(cell, cell) for cell in row] for row in grid]


def from_ai_grid(grid: Sequence[Sequence[str]]) -> Grid:
    if not grid:
        raise ValueError("maze 不能为空")
    width = len(grid[0])
    if width == 0:
        raise ValueError("maze 每一行不能为空")
    normalized: Grid = []
    for row in grid:
        if len(row) != width:
            raise ValueError("maze 每一行长度必须相同")
        normalized.append([AI_TO_INTERNAL.get(cell, cell) for cell in row])
    return normalized


def skills_to_json(skills: Sequence[Skill]) -> list[list[int]]:
    return [[skill.damage, skill.cooldown] for skill in skills]


def skills_from_json(raw_skills: Sequence[Sequence[int]]) -> tuple[Skill, ...]:
    skills: list[Skill] = []
    for index, raw in enumerate(raw_skills):
        if len(raw) != 2:
            raise ValueError("PlayerSkills 中每个技能必须是 [伤害, 冷却时间]")
        damage, cooldown = raw
        skills.append(Skill(f"技能{index}", damage=int(damage), cooldown=int(cooldown)))
    return tuple(skills)


def to_ai_json_payload(
    grid: Grid,
    boss_hp: Sequence[int],
    player_skills: Sequence[Skill],
    min_rounds: int,
    coin_consumption: int,
) -> dict[str, Any]:
    return {
        "maze": to_ai_grid(grid),
        "B": [int(value) for value in boss_hp],
        "PlayerSkills": skills_to_json(player_skills),
        "minRouds": int(min_rounds),
        "CoinConsumption": int(coin_consumption),
    }


def from_ai_json_payload(payload: dict[str, Any]) -> tuple[Grid, tuple[int, ...], tuple[Skill, ...], int, int]:
    required = {"maze", "B", "PlayerSkills", "minRouds", "CoinConsumption"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"JSON 缺少字段：{', '.join(sorted(missing))}")

    grid = from_ai_grid(payload["maze"])
    boss_hp = tuple(int(value) for value in payload["B"])
    skills = skills_from_json(payload["PlayerSkills"])
    min_rounds = int(payload["minRouds"])
    coin_consumption = int(payload["CoinConsumption"])
    return grid, boss_hp, skills, min_rounds, coin_consumption


def dumps_ai_json(payload: dict[str, Any]) -> str:
    if "mazes" in payload:
        lines = ["{", "    \"mazes\": {"]
        items = list(payload["mazes"].items())
        for index, (method, maze_payload) in enumerate(items):
            comma = "," if index + 1 < len(items) else ""
            rendered = _dumps_single_ai_payload(maze_payload, indent=8).splitlines()
            lines.append(f"        \"{method}\": {rendered[0].lstrip()}")
            lines.extend(rendered[1:-1])
            lines.append(f"{rendered[-1]}{comma}")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)
    return _dumps_single_ai_payload(payload)


def _dumps_single_ai_payload(payload: dict[str, Any], indent: int = 0) -> str:
    prefix = " " * indent
    field_indent = " " * (indent + 4)
    row_indent = " " * (indent + 8)
    lines = [prefix + "{"]
    lines.append(f"{field_indent}\"maze\": [")
    maze = payload["maze"]
    for index, row in enumerate(maze):
        comma = "," if index + 1 < len(maze) else ""
        lines.append(f"{row_indent}{json.dumps(row, ensure_ascii=False)}{comma}")
    lines.append(f"{field_indent}],")
    lines.append(f"{field_indent}\"B\": {json.dumps(payload['B'], ensure_ascii=False)},")
    lines.append(f"{field_indent}\"PlayerSkills\": {json.dumps(payload['PlayerSkills'], ensure_ascii=False)},")
    lines.append(f"{field_indent}\"minRouds\": {int(payload['minRouds'])},")
    lines.append(f"{field_indent}\"CoinConsumption\": {int(payload['CoinConsumption'])}")
    lines.append(prefix + "}")
    return "\n".join(lines)


def load_ai_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_ai_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(dumps_ai_json(payload) + "\n", encoding="utf-8")

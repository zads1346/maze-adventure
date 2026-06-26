from __future__ import annotations

from typing import Iterable, Sequence

from .boss import DEFAULT_SKILLS, optimize_boss_fight
from .core import (
    BOSS,
    COIN,
    END,
    PATH,
    START,
    TRAP,
    clone_grid,
    find_cell,
    in_bounds,
    render_grid,
    resource_value,
    shortest_path,
)
from .models import ExplorationResult, GreedyDecision, Grid, Position, Skill
from .resources import best_resource_path


def greedy_pickup(
    grid: Grid,
    position: Position,
    triggered_traps: Iterable[Position] | None = None,
    coin_value: int = 50,
    trap_value: int = -30,
) -> GreedyDecision:
    triggered = set(triggered_traps or [])
    best_target: Position | None = None
    best_path: list[Position] = [position]
    best_value = 0
    best_score = 0.0

    for target in _local_view_positions(grid, position):
        r, c = target
        cell = grid[r][c]
        if cell == TRAP and target in triggered:
            continue
        value = resource_value(cell, coin_value, trap_value)
        if value == 0:
            continue

        path = shortest_path(grid, position, target)
        if not path:
            continue
        distance = max(1, len(path) - 1)
        score = value / distance
        if score > best_score:
            best_score = score
            best_value = value
            best_target = target
            best_path = path

    visualization = render_grid(grid, path=best_path, current=position)
    return GreedyDecision(
        target=best_target,
        value=best_value,
        path=best_path,
        score=best_score,
        visualization=visualization,
    )


def explore_maze(
    grid: Grid,
    boss_hp: int | Sequence[int] = 30,
    skills: Sequence[Skill] = DEFAULT_SKILLS,
    coin_value: int = 50,
    trap_value: int = -30,
    max_frames: int = 60,
) -> ExplorationResult:
    working = clone_grid(grid)
    start = find_cell(working, START)
    end = find_cell(working, END)
    plan = best_resource_path(working, coin_value=coin_value, trap_value=trap_value)
    walk = plan.walk

    if not walk or walk[0] != start or walk[-1] != end:
        raise ValueError("resource plan does not travel from start to end")

    remaining_value = 0
    coins = 0
    steps = 0
    collected: set[Position] = set()
    boss_plan = None
    frames: list[str] = []
    frame_stride = max(1, len(walk) // max(1, max_frames))
    visited: list[Position] = []

    for index, pos in enumerate(walk):
        if index > 0:
            steps += 1
        visited.append(pos)

        r, c = pos
        cell = working[r][c]
        if pos not in collected and cell in {COIN, TRAP}:
            remaining_value += resource_value(cell, coin_value, trap_value)
            if cell == COIN:
                coins += coin_value
            elif cell == TRAP:
                coins += trap_value
            collected.add(pos)
            working[r][c] = PATH
        elif cell == BOSS and boss_plan is None:
            boss_plan = optimize_boss_fight(boss_hp, skills=skills)

        if index == 0 or index == len(walk) - 1 or index % frame_stride == 0:
            frames.append(render_grid(working, current=pos, visited=visited))

    ratio = remaining_value / steps if steps else 0.0
    return ExplorationResult(
        reached_end=walk[-1] == end,
        remaining_value=remaining_value,
        coins=coins,
        steps=steps,
        value_step_ratio=ratio,
        walk=walk,
        frames=frames[:max_frames],
        boss_plan=boss_plan,
    )


def _local_view_positions(grid: Grid, position: Position) -> list[Position]:
    r0, c0 = position
    result: list[Position] = []
    for r in range(r0 - 1, r0 + 2):
        for c in range(c0 - 1, c0 + 2):
            pos = (r, c)
            if in_bounds(grid, pos):
                result.append(pos)
    return result

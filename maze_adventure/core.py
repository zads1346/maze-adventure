from __future__ import annotations

from collections import deque
from typing import Iterable, Optional

from .models import Grid, Position


WALL = "#"
PATH = "."
START = "S"
END = "E"
COIN = "C"
TRAP = "T"
BOSS = "B"
AI_PATH = " "
AI_COIN = "G"

WALKABLE = {PATH, AI_PATH, START, END, COIN, AI_COIN, TRAP, BOSS}
RESOURCE_VALUES = {COIN: 50, AI_COIN: 50, TRAP: -30}


def clone_grid(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def ensure_square_size(n: int) -> int:
    if n < 5:
        raise ValueError("maze size must be at least 5")
    return n


def room_coordinates(n: int) -> list[int]:
    ensure_square_size(n)
    coords = list(range(1, n - 1, 2))
    if not coords:
        raise ValueError("maze size is too small for room carving")
    return coords


def in_bounds(grid: Grid, pos: Position) -> bool:
    r, c = pos
    return 0 <= r < len(grid) and 0 <= c < len(grid[0])


def is_walkable(cell: str) -> bool:
    return cell in WALKABLE


def neighbors4(pos: Position) -> Iterable[Position]:
    r, c = pos
    yield r - 1, c
    yield r + 1, c
    yield r, c - 1
    yield r, c + 1


def walkable_neighbors(grid: Grid, pos: Position) -> list[Position]:
    return [
        nb
        for nb in neighbors4(pos)
        if in_bounds(grid, nb) and is_walkable(grid[nb[0]][nb[1]])
    ]


def find_cell(grid: Grid, target: str) -> Position:
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == target:
                return r, c
    raise ValueError(f"cell {target!r} not found")


def all_walkable_positions(grid: Grid) -> list[Position]:
    return [
        (r, c)
        for r, row in enumerate(grid)
        for c, cell in enumerate(row)
        if is_walkable(cell)
    ]


def build_graph(grid: Grid) -> dict[Position, list[Position]]:
    return {pos: walkable_neighbors(grid, pos) for pos in all_walkable_positions(grid)}


def shortest_path(
    grid: Grid,
    start: Optional[Position] = None,
    end: Optional[Position] = None,
) -> list[Position]:
    if start is None:
        start = find_cell(grid, START)
    if end is None:
        end = find_cell(grid, END)

    queue: deque[Position] = deque([start])
    parent: dict[Position, Optional[Position]] = {start: None}

    while queue:
        current = queue.popleft()
        if current == end:
            break
        for nb in walkable_neighbors(grid, current):
            if nb not in parent:
                parent[nb] = current
                queue.append(nb)

    if end not in parent:
        return []

    path: list[Position] = []
    current: Optional[Position] = end
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def is_connected(grid: Grid) -> bool:
    positions = all_walkable_positions(grid)
    if not positions:
        return False

    seen = {positions[0]}
    queue: deque[Position] = deque([positions[0]])
    while queue:
        current = queue.popleft()
        for nb in walkable_neighbors(grid, current):
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return len(seen) == len(positions)


def is_perfect_maze(grid: Grid) -> bool:
    positions = all_walkable_positions(grid)
    if not positions or not is_connected(grid):
        return False
    edge_count = sum(len(walkable_neighbors(grid, pos)) for pos in positions) // 2
    return edge_count == len(positions) - 1


def resource_value(cell: str, coin_value: int = 50, trap_value: int = -30) -> int:
    if cell in {COIN, AI_COIN}:
        return coin_value
    if cell == TRAP:
        return trap_value
    return 0


def score_walk(
    grid: Grid,
    walk: list[Position],
    coin_value: int = 50,
    trap_value: int = -30,
) -> int:
    collected: set[Position] = set()
    total = 0
    for pos in walk:
        if pos in collected:
            continue
        r, c = pos
        value = resource_value(grid[r][c], coin_value, trap_value)
        if value:
            total += value
            collected.add(pos)
    return total


def render_grid(
    grid: Grid,
    path: Optional[Iterable[Position]] = None,
    current: Optional[Position] = None,
    visited: Optional[Iterable[Position]] = None,
) -> str:
    rendered = clone_grid(grid)

    if visited is not None:
        for r, c in visited:
            if rendered[r][c] in {PATH, AI_PATH}:
                rendered[r][c] = "+"

    if path is not None:
        for r, c in path:
            if rendered[r][c] in {PATH, AI_PATH}:
                rendered[r][c] = "*"

    if current is not None:
        r, c = current
        if in_bounds(rendered, current) and rendered[r][c] not in {START, END}:
            rendered[r][c] = "@"

    return "\n".join("".join(row) for row in rendered)


def path_to_string(path: list[Position]) -> str:
    return " -> ".join(f"({r},{c})" for r, c in path)

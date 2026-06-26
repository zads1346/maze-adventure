from __future__ import annotations

import heapq
import random
from itertools import count
from typing import Callable

from .core import (
    BOSS,
    COIN,
    END,
    PATH,
    START,
    TRAP,
    WALL,
    build_graph,
    clone_grid,
    find_cell,
    render_grid,
    room_coordinates,
    shortest_path,
)
from .models import Grid, MazeGenerationResult, Position


Generator = Callable[[int, random.Random, bool, int], tuple[Grid, list[str]]]


def generate_maze(
    n: int,
    method: str = "dfs",
    seed: int | None = None,
    decorate: bool = True,
    record: bool = False,
    max_frames: int = 80,
    coin_count: int | None = None,
    trap_count: int | None = None,
) -> MazeGenerationResult:
    rng = random.Random(seed)
    normalized = method.lower().replace("-", "_")
    aliases = {
        "backtracking": "dfs",
        "recursive_backtracking": "dfs",
        "prim": "mst",
        "minimum_spanning_tree": "mst",
        "divide": "division",
        "divide_and_conquer": "division",
        "recursive_division": "division",
        "branch_bound": "bfs_branch_bound",
        "branch_and_bound": "bfs_branch_bound",
        "bfs": "bfs_branch_bound",
    }
    normalized = aliases.get(normalized, normalized)

    generators: dict[str, Generator] = {
        "dfs": _generate_dfs,
        "mst": _generate_mst,
        "division": _generate_division,
        "bfs_branch_bound": _generate_bfs_branch_bound,
    }
    if normalized not in generators:
        valid = ", ".join(sorted(generators))
        raise ValueError(f"unknown generation method {method!r}; valid methods: {valid}")

    grid, frames = generators[normalized](n, rng, record, max_frames)
    _place_start_end(grid)
    if decorate:
        grid = decorate_maze(grid, seed=seed, coin_count=coin_count, trap_count=trap_count)
    if record:
        _record_frame(frames, grid, max_frames, force=True)
    return MazeGenerationResult(method=normalized, grid=grid, frames=frames)


def generate_all_methods(
    n: int,
    seed: int | None = None,
    decorate: bool = True,
    record: bool = False,
    max_frames: int = 300,
) -> dict[str, MazeGenerationResult]:
    return {
        method: generate_maze(
            n,
            method=method,
            seed=seed,
            decorate=decorate,
            record=record,
            max_frames=max_frames,
        )
        for method in ("division", "mst", "dfs", "bfs_branch_bound")
    }


def decorate_maze(
    grid: Grid,
    seed: int | None = None,
    coin_count: int | None = None,
    trap_count: int | None = None,
) -> Grid:
    result = clone_grid(grid)
    rng = random.Random(seed)
    start = find_cell(result, START)
    end = find_cell(result, END)
    main_path = shortest_path(result, start, end)

    if len(main_path) >= 3:
        boss_pos = main_path[-2]
        if boss_pos not in {start, end}:
            result[boss_pos[0]][boss_pos[1]] = BOSS

    graph = build_graph(result)
    candidates = [
        pos
        for pos, neighbors in graph.items()
        if pos not in {start, end}
        and result[pos[0]][pos[1]] == PATH
        and len(neighbors) > 0
    ]
    if not candidates:
        return result

    dead_ends = [pos for pos in candidates if len(graph[pos]) == 1]
    ordinary = [pos for pos in candidates if pos not in set(dead_ends)]
    rng.shuffle(dead_ends)
    rng.shuffle(ordinary)

    default_coins = max(1, len(candidates) // 8)
    default_traps = max(1, len(candidates) // 14)
    coin_count = default_coins if coin_count is None else max(0, coin_count)
    trap_count = default_traps if trap_count is None else max(0, trap_count)

    coin_pool = dead_ends + ordinary
    coin_positions = coin_pool[: min(coin_count, len(coin_pool))]

    used = set(coin_positions)
    trap_pool = [pos for pos in ordinary + dead_ends if pos not in used]
    rng.shuffle(trap_pool)
    trap_positions = trap_pool[: min(trap_count, len(trap_pool))]

    for r, c in coin_positions:
        result[r][c] = COIN
    for r, c in trap_positions:
        result[r][c] = TRAP
    return result


def _new_grid(n: int) -> Grid:
    room_coordinates(n)
    return [[WALL for _ in range(n)] for _ in range(n)]


def _place_start_end(grid: Grid) -> None:
    coords = room_coordinates(len(grid))
    start = (coords[0], coords[0])
    end = (coords[-1], coords[-1])
    grid[start[0]][start[1]] = START
    grid[end[0]][end[1]] = END


def _room_neighbors(pos: Position, coord_set: set[int]) -> list[Position]:
    r, c = pos
    neighbors: list[Position] = []
    for nr, nc in ((r - 2, c), (r + 2, c), (r, c - 2), (r, c + 2)):
        if nr in coord_set and nc in coord_set:
            neighbors.append((nr, nc))
    return neighbors


def _carve_room(grid: Grid, pos: Position) -> None:
    r, c = pos
    grid[r][c] = PATH


def _carve_between(grid: Grid, a: Position, b: Position) -> None:
    ar, ac = a
    br, bc = b
    grid[(ar + br) // 2][(ac + bc) // 2] = PATH
    grid[br][bc] = PATH


def _record_frame(frames: list[str], grid: Grid, max_frames: int, force: bool = False) -> None:
    if force or len(frames) < max_frames:
        frames.append(render_grid(grid))


def _generate_dfs(
    n: int,
    rng: random.Random,
    record: bool,
    max_frames: int,
) -> tuple[Grid, list[str]]:
    coords = room_coordinates(n)
    coord_set = set(coords)
    grid = _new_grid(n)
    frames: list[str] = []
    start = (coords[0], coords[0])
    _carve_room(grid, start)

    stack = [start]
    visited = {start}
    if record:
        _record_frame(frames, grid, max_frames)

    while stack:
        current = stack[-1]
        choices = [nb for nb in _room_neighbors(current, coord_set) if nb not in visited]
        if choices:
            nxt = rng.choice(choices)
            _carve_between(grid, current, nxt)
            visited.add(nxt)
            stack.append(nxt)
            if record:
                _record_frame(frames, grid, max_frames)
        else:
            stack.pop()
    return grid, frames


def _generate_mst(
    n: int,
    rng: random.Random,
    record: bool,
    max_frames: int,
) -> tuple[Grid, list[str]]:
    coords = room_coordinates(n)
    coord_set = set(coords)
    grid = _new_grid(n)
    frames: list[str] = []
    start = (coords[0], coords[0])
    _carve_room(grid, start)

    visited = {start}
    frontier: list[tuple[float, int, Position, Position]] = []
    sequence = count()

    def push_edges(pos: Position) -> None:
        for nb in _room_neighbors(pos, coord_set):
            if nb not in visited:
                heapq.heappush(frontier, (rng.random(), next(sequence), pos, nb))

    push_edges(start)
    if record:
        _record_frame(frames, grid, max_frames)

    while frontier:
        _, _, parent, current = heapq.heappop(frontier)
        if current in visited:
            continue
        _carve_between(grid, parent, current)
        visited.add(current)
        push_edges(current)
        if record:
            _record_frame(frames, grid, max_frames)
    return grid, frames


def _generate_division(
    n: int,
    rng: random.Random,
    record: bool,
    max_frames: int,
) -> tuple[Grid, list[str]]:
    coords = room_coordinates(n)
    grid = _new_grid(n)
    frames: list[str] = []

    for r in coords:
        for c in coords:
            grid[r][c] = PATH
    if record:
        _record_frame(frames, grid, max_frames)

    def divide(r0: int, r1: int, c0: int, c1: int) -> None:
        height = r1 - r0 + 1
        width = c1 - c0 + 1
        if height == 1 and width == 1:
            return

        split_horizontal = height > 1 and (height >= width or width == 1)
        if split_horizontal:
            split = rng.randrange(r0, r1)
            divide(r0, split, c0, c1)
            divide(split + 1, r1, c0, c1)
            bridge_col = rng.randrange(c0, c1 + 1)
            a = (coords[split], coords[bridge_col])
            b = (coords[split + 1], coords[bridge_col])
        else:
            split = rng.randrange(c0, c1)
            divide(r0, r1, c0, split)
            divide(r0, r1, split + 1, c1)
            bridge_row = rng.randrange(r0, r1 + 1)
            a = (coords[bridge_row], coords[split])
            b = (coords[bridge_row], coords[split + 1])

        _carve_between(grid, a, b)
        if record:
            _record_frame(frames, grid, max_frames)

    divide(0, len(coords) - 1, 0, len(coords) - 1)
    return grid, frames


def _generate_bfs_branch_bound(
    n: int,
    rng: random.Random,
    record: bool,
    max_frames: int,
) -> tuple[Grid, list[str]]:
    coords = room_coordinates(n)
    coord_set = set(coords)
    grid = _new_grid(n)
    frames: list[str] = []
    start = (coords[0], coords[0])
    goal = (coords[-1], coords[-1])
    _carve_room(grid, start)

    visited = {start}
    frontier: list[tuple[float, int, int, Position, Position]] = []
    sequence = count()

    def bound(candidate: Position, depth: int) -> float:
        dist_to_goal = abs(candidate[0] - goal[0]) + abs(candidate[1] - goal[1])
        branch_penalty = sum(1 for nb in _room_neighbors(candidate, coord_set) if nb in visited)
        return depth + 0.05 * dist_to_goal + 0.25 * branch_penalty + rng.random() * 0.01

    def push_edges(pos: Position, depth: int) -> None:
        for nb in _room_neighbors(pos, coord_set):
            if nb not in visited:
                heapq.heappush(frontier, (bound(nb, depth + 1), depth + 1, next(sequence), pos, nb))

    push_edges(start, 0)
    if record:
        _record_frame(frames, grid, max_frames)

    while frontier:
        _, depth, _, parent, current = heapq.heappop(frontier)
        if current in visited:
            continue
        _carve_between(grid, parent, current)
        visited.add(current)
        push_edges(current, depth)
        if record:
            _record_frame(frames, grid, max_frames)
    return grid, frames

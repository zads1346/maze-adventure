from __future__ import annotations

from collections import deque
from functools import lru_cache

from .core import (
    END,
    START,
    build_graph,
    find_cell,
    is_perfect_maze,
    resource_value,
    score_walk,
    shortest_path,
)
from .models import Grid, Position, ResourcePlan


def best_resource_path(
    grid: Grid,
    coin_value: int = 50,
    trap_value: int = -30,
) -> ResourcePlan:
    start = find_cell(grid, START)
    end = find_cell(grid, END)
    graph = build_graph(grid)

    if is_perfect_maze(grid):
        tree = graph
        spine = shortest_path(grid, start, end)
    else:
        tree = _bfs_spanning_tree(graph, start)
        spine = _tree_path(tree, start, end)

    if not spine:
        raise ValueError("end is unreachable from start")

    spine_set = set(spine)

    @lru_cache(maxsize=None)
    def branch_gain(node: Position, parent: Position) -> int:
        r, c = node
        total = resource_value(grid[r][c], coin_value, trap_value)
        for nb in tree[node]:
            if nb == parent or nb in spine_set:
                continue
            child_gain = branch_gain(nb, node)
            if child_gain > 0:
                total += child_gain
        return total

    def selected_branch(parent: Position, node: Position) -> bool:
        return branch_gain(node, parent) > 0

    def branch_tour(parent: Position, node: Position) -> list[Position]:
        tour = [node]
        children = sorted(
            nb for nb in tree[node] if nb != parent and nb not in spine_set
        )
        for child in children:
            if selected_branch(node, child):
                tour.extend(branch_tour(node, child))
        tour.append(parent)
        return tour

    walk: list[Position] = [spine[0]]
    max_value = 0

    for index, node in enumerate(spine):
        r, c = node
        max_value += resource_value(grid[r][c], coin_value, trap_value)

        previous_node = spine[index - 1] if index > 0 else None
        next_node = spine[index + 1] if index + 1 < len(spine) else None
        off_spine = [
            nb
            for nb in sorted(tree[node])
            if nb not in {previous_node, next_node} and nb not in spine_set
        ]
        for child in off_spine:
            gain = branch_gain(child, node)
            if gain > 0:
                max_value += gain
                walk.extend(branch_tour(node, child))

        if next_node is not None:
            walk.append(next_node)

    collected = _collected_resources(grid, walk, coin_value, trap_value)
    checked_value = score_walk(grid, walk, coin_value, trap_value)
    if checked_value != max_value:
        max_value = checked_value

    inner_path = [pos for pos in walk if pos not in {start, end}]
    return ResourcePlan(
        max_value=max_value,
        path=inner_path,
        walk=walk,
        collected=collected,
    )


def _bfs_spanning_tree(
    graph: dict[Position, list[Position]],
    start: Position,
) -> dict[Position, list[Position]]:
    tree = {pos: [] for pos in graph}
    queue: deque[Position] = deque([start])
    seen = {start}
    while queue:
        current = queue.popleft()
        for nb in graph[current]:
            if nb in seen:
                continue
            seen.add(nb)
            tree[current].append(nb)
            tree[nb].append(current)
            queue.append(nb)
    return tree


def _tree_path(
    tree: dict[Position, list[Position]],
    start: Position,
    end: Position,
) -> list[Position]:
    queue: deque[Position] = deque([start])
    parent: dict[Position, Position | None] = {start: None}
    while queue:
        current = queue.popleft()
        if current == end:
            break
        for nb in tree[current]:
            if nb not in parent:
                parent[nb] = current
                queue.append(nb)

    if end not in parent:
        return []

    path: list[Position] = []
    current: Position | None = end
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def _collected_resources(
    grid: Grid,
    walk: list[Position],
    coin_value: int,
    trap_value: int,
) -> set[Position]:
    collected: set[Position] = set()
    for r, c in walk:
        if resource_value(grid[r][c], coin_value, trap_value):
            collected.add((r, c))
    return collected

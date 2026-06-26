from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable

from .ai import explore_maze
from .core import BOSS, COIN, END, PATH, START, TRAP, WALL, find_cell
from .generation import generate_maze
from .models import Grid, Position
from .resources import best_resource_path
from .visual_fonts import get_font


METHOD_LABELS = {
    "division": "分治法",
    "mst": "贪心最小生成树",
    "dfs": "回溯 / DFS",
    "bfs_branch_bound": "分支限界 / BFS",
}
GENERATION_METHODS = ("division", "mst", "dfs", "bfs_branch_bound")


@dataclass
class PygameDemoConfig:
    size: int = 15
    method: str = "dfs"
    seed: int = 7
    mode: str = "explore"
    cell_size: int = 34
    fps: int = 8
    auto_quit: bool = False


def run_pygame_demo(config: PygameDemoConfig) -> None:
    try:
        import pygame
    except ImportError as exc:
        raise RuntimeError(
            "pygame 尚未安装，请运行：uv venv && uv pip install -e ."
        ) from exc

    if config.mode == "generate":
        _run_generation_demo(pygame, config)
        return

    if config.method == "all":
        raise ValueError("explore/resource 模式只能选择单个生成算法，all 仅用于 generate 模式")

    maze_result = generate_maze(
        config.size,
        method=config.method,
        seed=config.seed,
        decorate=True,
        record=False,
    )
    grid = maze_result.grid
    path, title, stats = _build_animation(config.mode, grid, [])

    pygame.init()
    pygame.display.set_caption("迷宫探险游戏 - 可视化")
    font = get_font(pygame, 18)
    small_font = get_font(pygame, 14)

    rows = len(grid)
    cols = len(grid[0])
    margin = 18
    hud_height = 86
    cell_size = max(18, config.cell_size)
    width = cols * cell_size + margin * 2
    height = rows * cell_size + margin * 2 + hud_height
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    frame_index = 0
    paused = False
    speed = max(1, config.fps)
    running = True
    last_advance = 0

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in {pygame.K_ESCAPE, pygame.K_q}:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    frame_index = 0
                    paused = False
                elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                    frame_index = min(frame_index + 1, len(path) - 1)
                    paused = True
                elif event.key in {pygame.K_LEFT, pygame.K_a}:
                    frame_index = max(frame_index - 1, 0)
                    paused = True
                elif event.key in {pygame.K_EQUALS, pygame.K_PLUS}:
                    speed = min(speed + 2, 60)
                elif event.key in {pygame.K_MINUS, pygame.K_UNDERSCORE}:
                    speed = max(speed - 2, 1)

        interval_ms = max(16, int(1000 / speed))
        if not paused and now - last_advance >= interval_ms:
            frame_index = min(frame_index + 1, len(path) - 1)
            last_advance = now

        screen.fill((238, 238, 232))
        _draw_hud(
            pygame,
            screen,
            font,
            small_font,
            title,
            stats,
            frame_index,
            len(path),
            speed,
            paused,
            margin,
        )
        _draw_maze(
            pygame,
            screen,
            grid,
            path[: frame_index + 1],
            margin,
            margin + hud_height,
            cell_size,
            font,
        )
        pygame.display.flip()
        if config.auto_quit and frame_index >= len(path) - 1:
            running = False
        clock.tick(60)

    pygame.quit()


def _run_generation_demo(pygame, config: PygameDemoConfig) -> None:
    methods = GENERATION_METHODS if config.method == "all" else (config.method,)
    results = [
        generate_maze(
            config.size,
            method=method,
            seed=config.seed,
            decorate=False,
            record=True,
            max_frames=500,
        )
        for method in methods
    ]
    frame_sets = [[_grid_from_frame(frame) for frame in result.frames] for result in results]
    if any(not frames for frames in frame_sets):
        raise RuntimeError("生成过程帧为空，请检查生成算法的 record 参数")

    pygame.init()
    pygame.display.set_caption("迷宫生成过程 - 四算法可视化")
    font = get_font(pygame, 18)
    small_font = get_font(pygame, 14)

    rows = config.size
    cols = config.size
    margin = 18
    hud_height = 104
    cell_size = max(18, config.cell_size)
    width = cols * cell_size + margin * 2
    height = rows * cell_size + margin * 2 + hud_height
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    method_index = 0
    frame_index = 0
    paused = False
    speed = max(1, config.fps)
    running = True
    last_advance = 0

    while running:
        now = pygame.time.get_ticks()
        current_frames = frame_sets[method_index]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in {pygame.K_ESCAPE, pygame.K_q}:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    method_index = 0
                    frame_index = 0
                    paused = False
                elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                    if frame_index < len(current_frames) - 1:
                        frame_index += 1
                    elif method_index < len(frame_sets) - 1:
                        method_index += 1
                        frame_index = 0
                    paused = True
                elif event.key in {pygame.K_LEFT, pygame.K_a}:
                    if frame_index > 0:
                        frame_index -= 1
                    elif method_index > 0:
                        method_index -= 1
                        frame_index = len(frame_sets[method_index]) - 1
                    paused = True
                elif event.key == pygame.K_n and method_index < len(frame_sets) - 1:
                    method_index += 1
                    frame_index = 0
                    paused = True
                elif event.key == pygame.K_p and method_index > 0:
                    method_index -= 1
                    frame_index = 0
                    paused = True
                elif event.key in {pygame.K_EQUALS, pygame.K_PLUS}:
                    speed = min(speed + 2, 60)
                elif event.key in {pygame.K_MINUS, pygame.K_UNDERSCORE}:
                    speed = max(speed - 2, 1)

        current_frames = frame_sets[method_index]
        interval_ms = max(16, int(1000 / speed))
        if not paused and now - last_advance >= interval_ms:
            if frame_index < len(current_frames) - 1:
                frame_index += 1
            elif method_index < len(frame_sets) - 1:
                method_index += 1
                frame_index = 0
            last_advance = now

        current_method = results[method_index].method
        current_frames = frame_sets[method_index]
        screen.fill((238, 238, 232))
        _draw_generation_hud(
            screen,
            font,
            small_font,
            current_method,
            method_index,
            len(frame_sets),
            frame_index,
            len(current_frames),
            speed,
            paused,
            margin,
        )
        _draw_maze(
            pygame,
            screen,
            current_frames[frame_index],
            [],
            margin,
            margin + hud_height,
            cell_size,
            font,
        )
        pygame.display.flip()
        if config.auto_quit and method_index == len(frame_sets) - 1 and frame_index >= len(current_frames) - 1:
            running = False
        clock.tick(60)

    pygame.quit()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="迷宫探险游戏 pygame 可视化")
    parser.add_argument("-n", "--size", type=int, default=15, help="迷宫尺寸")
    parser.add_argument(
        "-m",
        "--method",
        default="dfs",
        choices=["all", "division", "mst", "dfs", "bfs_branch_bound"],
        help="迷宫生成算法；generate 模式可使用 all 播放四种算法",
    )
    parser.add_argument(
        "--mode",
        default="explore",
        choices=["explore", "resource", "generate"],
        help="可视化模式：explore 探险，resource 资源路径，generate 生成过程",
    )
    parser.add_argument("--seed", type=int, default=7, help="随机种子")
    parser.add_argument("--cell-size", type=int, default=34, help="每个格子的像素大小")
    parser.add_argument("--fps", type=int, default=8, help="动画速度")
    parser.add_argument("--auto-quit", action="store_true", help="动画结束后自动退出")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    run_pygame_demo(
        PygameDemoConfig(
            size=args.size,
            method=args.method,
            seed=args.seed,
            mode=args.mode,
            cell_size=args.cell_size,
            fps=args.fps,
            auto_quit=args.auto_quit,
        )
    )


def _build_animation(
    mode: str,
    grid: Grid,
    generation_frames: list[str],
) -> tuple[list[Position], str, list[str]]:
    if mode == "resource":
        plan = best_resource_path(grid)
        return (
            plan.walk,
            "动态规划资源收集路径",
            [f"最多资源：{plan.max_value}", f"行走步数：{max(0, len(plan.walk) - 1)}"],
        )

    result = explore_maze(grid)
    return (
        result.walk,
        "AI迷宫探险过程",
        [
            f"资源：{result.remaining_value}",
            f"步数：{result.steps}",
            f"得分：{result.value_step_ratio:.3f}",
        ],
    )


def _draw_hud(
    pygame,
    screen,
    font,
    small_font,
    title: str,
    stats: list[str],
    frame_index: int,
    frame_count: int,
    speed: int,
    paused: bool,
    margin: int,
) -> None:
    title_surface = font.render(title, True, (38, 42, 50))
    screen.blit(title_surface, (margin, 14))

    status = "已暂停" if paused else "播放中"
    details = " | ".join(
        stats
        + [
            f"帧：{frame_index + 1}/{frame_count}",
            f"速度：{speed} fps",
            status,
        ]
    )
    details_surface = small_font.render(details, True, (72, 78, 88))
    screen.blit(details_surface, (margin, 42))

    controls = "空格暂停  R重播  方向键/A/D单步  +/-调速  Esc/Q退出"
    controls_surface = small_font.render(controls, True, (96, 101, 111))
    screen.blit(controls_surface, (margin, 64))


def _draw_generation_hud(
    screen,
    font,
    small_font,
    method: str,
    method_index: int,
    method_count: int,
    frame_index: int,
    frame_count: int,
    speed: int,
    paused: bool,
    margin: int,
) -> None:
    title = f"任务一：迷宫生成过程 - {METHOD_LABELS.get(method, method)}"
    screen.blit(font.render(title, True, (38, 42, 50)), (margin, 14))
    status = "已暂停" if paused else "播放中"
    details = (
        f"算法：{method_index + 1}/{method_count} | "
        f"帧：{frame_index + 1}/{frame_count} | 速度：{speed} fps | {status}"
    )
    screen.blit(small_font.render(details, True, (72, 78, 88)), (margin, 44))
    controls = "空格暂停  R重播全部  方向键/A/D单步  N/P切换算法  +/-调速  Esc/Q退出"
    screen.blit(small_font.render(controls, True, (96, 101, 111)), (margin, 70))


def _draw_maze(
    pygame,
    screen,
    grid: Grid,
    visited: Iterable[Position],
    left: int,
    top: int,
    cell_size: int,
    font,
) -> None:
    visited_list = list(visited)
    visited_set = set(visited_list)
    current = visited_list[-1] if visited_list else None

    colors = {
        WALL: (43, 45, 52),
        PATH: (248, 248, 244),
        START: (43, 137, 82),
        END: (52, 105, 190),
        COIN: (238, 185, 65),
        TRAP: (189, 68, 61),
        BOSS: (120, 77, 161),
    }

    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            rect = pygame.Rect(
                left + c * cell_size,
                top + r * cell_size,
                cell_size,
                cell_size,
            )
            pygame.draw.rect(screen, colors.get(cell, colors[PATH]), rect)
            if (r, c) in visited_set and cell not in {WALL, START, END}:
                inner = rect.inflate(-cell_size * 0.38, -cell_size * 0.38)
                pygame.draw.rect(screen, (89, 145, 194), inner, border_radius=3)
            pygame.draw.rect(screen, (211, 211, 204), rect, 1)

            if cell in {START, END, COIN, TRAP, BOSS}:
                _draw_cell_label(pygame, screen, font, cell, rect)

    if current is not None:
        r, c = current
        cx = left + c * cell_size + cell_size // 2
        cy = top + r * cell_size + cell_size // 2
        pygame.draw.circle(screen, (28, 28, 28), (cx, cy), max(6, cell_size // 4))
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), max(3, cell_size // 9))


def _draw_cell_label(pygame, screen, font, cell: str, rect) -> None:
    labels = {START: "S", END: "E", COIN: "$", TRAP: "!", BOSS: "B"}
    label = labels.get(cell)
    if not label:
        return
    color = (255, 255, 255) if cell in {START, END, TRAP, BOSS} else (56, 45, 16)
    surface = font.render(label, True, color)
    surface_rect = surface.get_rect(center=rect.center)
    screen.blit(surface, surface_rect)


def _frames_to_current_positions(frames: list[str], grid: Grid) -> list[Position]:
    if not frames:
        return [find_cell(grid, START)]

    positions: list[Position] = []
    opened: set[Position] = set()
    for frame in frames:
        current_opened: set[Position] = set()
        for r, line in enumerate(frame.splitlines()):
            for c, cell in enumerate(line):
                if cell != WALL:
                    current_opened.add((r, c))
        for pos in sorted(current_opened - opened):
            positions.append(pos)
        opened = current_opened

    if not positions:
        positions.append(find_cell(grid, START))
    return positions


def _grid_from_frame(frame: str) -> Grid:
    return [list(line) for line in frame.splitlines() if line]

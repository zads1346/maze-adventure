from __future__ import annotations

import argparse
from dataclasses import dataclass

from .boss import optimize_boss_fight
from .models import BossPlan, Skill, SkillUse
from .visual_fonts import get_font


VISUAL_SKILLS = (
    Skill("普通攻击", damage=5, cooldown=0),
    Skill("大招", damage=10, cooldown=2),
)


@dataclass
class BossDemoConfig:
    boss_hp: tuple[int, ...] = (30,)
    fps: int = 2
    coins: int = 100
    min_rounds: int = 20
    revive_coin: int = 5
    auto_quit: bool = False


def run_boss_demo(config: BossDemoConfig) -> None:
    try:
        import pygame
    except ImportError as exc:
        raise RuntimeError(
            "pygame 尚未安装，请运行：uv venv && uv pip install -e ."
        ) from exc

    round_limit = max(1, config.min_rounds)
    plan = optimize_boss_fight(
        config.boss_hp,
        VISUAL_SKILLS,
        revive_coin=max(0, config.revive_coin),
    )
    hp_frames = [config.boss_hp] + [use.remaining_hp for use in plan.sequence]

    pygame.init()
    pygame.display.set_caption("迷宫探险游戏 - BOSS战")
    screen = pygame.display.set_mode((920, 590))
    clock = pygame.time.Clock()
    title_font = get_font(pygame, 28, bold=True)
    font = get_font(pygame, 20)
    small_font = get_font(pygame, 16)

    frame_index = 0
    rounds_since_revive = 0
    paused = False
    waiting_revive = False
    game_over = False
    victory = False
    speed = max(1, config.fps)
    running = True
    last_advance = 0
    coins = max(0, config.coins)
    revive_count = 0
    message = f"BOSS不会反击；每轮最多 {round_limit} 回合，超出后需要确认复活。"
    revive_rect = pygame.Rect(632, 466, 232, 48)

    def reset_battle() -> None:
        nonlocal frame_index, rounds_since_revive, paused, waiting_revive, game_over, victory
        nonlocal coins, revive_count, message
        frame_index = 0
        rounds_since_revive = 0
        paused = False
        waiting_revive = False
        game_over = False
        victory = False
        coins = max(0, config.coins)
        revive_count = 0
        message = "已重新开始BOSS战模拟。"

    def confirm_revive() -> None:
        nonlocal coins, revive_count, rounds_since_revive, waiting_revive, paused, game_over, message
        if not waiting_revive:
            message = "当前还没有超过规定回合数，不需要复活。"
            return
        if coins < plan.revive_coin:
            game_over = True
            message = f"金币不足：当前 {coins}，复活需要 {plan.revive_coin}，GAME OVER。"
            return
        coins -= plan.revive_coin
        revive_count += 1
        rounds_since_revive = 0
        waiting_revive = False
        paused = False
        game_over = False
        message = f"复活成功：消耗 {plan.revive_coin} 金币，剩余金币 {coins}，BOSS当前血量保持不变。"

    def advance_round() -> None:
        nonlocal frame_index, rounds_since_revive, waiting_revive, paused, game_over, victory, message
        if waiting_revive or game_over or victory:
            return
        if frame_index >= len(plan.sequence):
            victory = True
            paused = True
            message = "BOSS已被击败，战斗胜利。"
            return

        use = plan.sequence[frame_index]
        frame_index += 1
        rounds_since_revive += 1
        current_boss_hp = hp_frames[frame_index]
        if all(value <= 0 for value in current_boss_hp):
            victory = True
            paused = True
            message = f"第 {use.round_no} 回合：{use.skill} 击败BOSS，战斗胜利。"
            return

        message = (
            f"第 {use.round_no} 回合：{use.skill} 攻击BOSS {use.target}，"
            f"本轮已用 {rounds_since_revive}/{round_limit} 回合。"
        )
        if rounds_since_revive >= round_limit:
            waiting_revive = True
            paused = True
            if coins >= plan.revive_coin:
                message += f" 未在规定回合内击败全部BOSS，请点击确认复活（消耗 {plan.revive_coin} 金币）。"
            else:
                game_over = True
                message += " 金币不足，无法复活，GAME OVER。"

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if revive_rect.collidepoint(event.pos):
                    confirm_revive()
            elif event.type == pygame.KEYDOWN:
                if event.key in {pygame.K_ESCAPE, pygame.K_q}:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if not waiting_revive and not game_over and not victory:
                        paused = not paused
                elif event.key == pygame.K_r:
                    reset_battle()
                elif event.key in {pygame.K_RIGHT, pygame.K_d}:
                    advance_round()
                    paused = True
                elif event.key in {pygame.K_LEFT, pygame.K_a}:
                    frame_index = max(frame_index - 1, 0)
                    paused = True
                    message = "已回退显示帧；仅用于观察BOSS血量，复活计数不回滚。"
                elif event.key in {pygame.K_EQUALS, pygame.K_PLUS}:
                    speed = min(speed + 1, 30)
                elif event.key in {pygame.K_MINUS, pygame.K_UNDERSCORE}:
                    speed = max(speed - 1, 1)

        if config.auto_quit and waiting_revive:
            if coins >= plan.revive_coin:
                confirm_revive()
            else:
                running = False

        interval_ms = max(33, int(1000 / speed))
        if not paused and not waiting_revive and not game_over and not victory and now - last_advance >= interval_ms:
            advance_round()
            last_advance = now

        screen.fill((238, 238, 232))
        _draw_boss_scene(
            pygame,
            screen,
            title_font,
            font,
            small_font,
            plan,
            config.boss_hp,
            hp_frames[frame_index],
            frame_index,
            round_limit,
            rounds_since_revive,
            speed,
            paused,
            coins,
            message,
            revive_rect,
            revive_count,
            waiting_revive,
            game_over,
            victory,
        )
        pygame.display.flip()
        if config.auto_quit and (victory or game_over):
            running = False
        clock.tick(60)

    pygame.quit()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BOSS战 pygame 可视化")
    parser.add_argument(
        "--boss-hp",
        type=int,
        nargs="+",
        default=[30],
        help="一个或多个BOSS血量",
    )
    parser.add_argument("--coins", type=int, default=100, help="玩家初始金币")
    parser.add_argument("--min-rounds", "--round-limit", dest="min_rounds", type=int, default=20, help="规定回合数，对应 JSON 字段 minRouds")
    parser.add_argument("--revive-coin", "--coin-consumption", dest="revive_coin", type=int, default=5, help="每次复活消耗的金币，对应 CoinConsumption")
    parser.add_argument("--fps", type=int, default=2, help="动画速度")
    parser.add_argument("--auto-quit", action="store_true", help="动画结束后自动退出")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    run_boss_demo(
        BossDemoConfig(
            boss_hp=tuple(max(0, value) for value in args.boss_hp),
            fps=args.fps,
            coins=args.coins,
            min_rounds=args.min_rounds,
            revive_coin=args.revive_coin,
            auto_quit=args.auto_quit,
        )
    )


def _draw_boss_scene(
    pygame,
    screen,
    title_font,
    font,
    small_font,
    plan: BossPlan,
    initial_hp: tuple[int, ...],
    current_hp: tuple[int, ...],
    frame_index: int,
    round_limit: int,
    rounds_since_revive: int,
    speed: int,
    paused: bool,
    coins: int,
    message: str,
    revive_rect,
    revive_count: int,
    waiting_revive: bool,
    game_over: bool,
    victory: bool,
) -> None:
    _draw_text(screen, title_font, "BOSS战：限定回合与金币复活", 36, 24, (35, 38, 46))
    if game_over:
        status = "失败"
    elif victory:
        status = "胜利"
    elif waiting_revive:
        status = "等待复活"
    else:
        status = "已暂停" if paused else "播放中"
    summary = (
        f"最少回合：{plan.min_rounds} | 规定回合：{round_limit} | "
        f"本轮回合：{rounds_since_revive}/{round_limit} | 每次复活：{plan.revive_coin}金币 | "
        f"当前金币：{coins} | 已复活：{revive_count}次 | 速度：{speed} fps | {status}"
    )
    _draw_text(screen, small_font, summary, 38, 62, (78, 83, 94))
    _draw_text(
        screen,
        small_font,
        "空格暂停  R重新开始  方向键/A/D单步  +/-调速  鼠标点击确认复活  Esc/Q退出",
        38,
        88,
        (96, 101, 111),
    )

    panel = pygame.Rect(36, 124, 558, 410)
    pygame.draw.rect(screen, (248, 248, 244), panel, border_radius=8)
    pygame.draw.rect(screen, (205, 205, 198), panel, 1, border_radius=8)

    for index, (start_hp, hp) in enumerate(zip(initial_hp, current_hp)):
        y = 164 + index * 76
        _draw_text(screen, font, f"BOSS {index}", 70, y - 30, (48, 50, 58))
        _draw_hp_bar(pygame, screen, small_font, 70, y, 480, 30, hp, max(1, start_hp), (189, 68, 61))

    rule_rect = pygame.Rect(70, 354, 480, 42)
    pygame.draw.rect(screen, (238, 241, 232), rule_rect, border_radius=6)
    pygame.draw.rect(screen, (196, 202, 188), rule_rect, 1, border_radius=6)
    _draw_text(screen, small_font, "规则：BOSS不造成伤害；超出规定回合后复活，BOSS血量保留。", 88, 366, (56, 72, 58))

    current_use = plan.sequence[frame_index - 1] if frame_index > 0 else None
    action_rect = pygame.Rect(70, 424, 480, 66)
    pygame.draw.rect(screen, (232, 238, 244), action_rect, border_radius=6)
    pygame.draw.rect(screen, (190, 201, 211), action_rect, 1, border_radius=6)
    _draw_text(
        screen,
        small_font,
        _format_action(current_use),
        action_rect.x + 18,
        action_rect.y + 18,
        (40, 45, 54),
    )

    list_panel = pygame.Rect(620, 124, 264, 410)
    pygame.draw.rect(screen, (248, 248, 244), list_panel, border_radius=8)
    pygame.draw.rect(screen, (205, 205, 198), list_panel, 1, border_radius=8)
    _draw_text(screen, font, "最优技能序列", 642, 146, (48, 50, 58))
    for row, use in enumerate(plan.sequence[:8]):
        color = (39, 108, 70) if row == frame_index - 1 else (69, 74, 84)
        line = f"{use.round_no}. {use.skill} -> B{use.target}，伤害{use.damage}"
        _draw_text(screen, small_font, line, 642, 184 + row * 28, color)

    _draw_text(screen, small_font, message, 642, 418, (78, 83, 94))
    can_revive = waiting_revive and coins >= plan.revive_coin
    button_color = (43, 137, 82) if can_revive else (136, 136, 136)
    pygame.draw.rect(screen, button_color, revive_rect, border_radius=7)
    pygame.draw.rect(screen, (35, 38, 46), revive_rect, 1, border_radius=7)
    if can_revive:
        button_text = f"确认复活（-{plan.revive_coin}金币）"
    elif waiting_revive:
        button_text = "金币不足，无法复活"
    elif victory:
        button_text = "战斗胜利"
    else:
        button_text = "未到复活条件"
    label = small_font.render(button_text, True, (255, 255, 255))
    screen.blit(label, label.get_rect(center=revive_rect.center))


def _draw_hp_bar(
    pygame,
    screen,
    font,
    x: int,
    y: int,
    width: int,
    height: int,
    hp: int,
    max_hp: int,
    fill_color: tuple[int, int, int],
) -> None:
    outer = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, (64, 67, 76), outer, border_radius=5)
    ratio = max(0.0, min(1.0, hp / max_hp))
    inner_width = max(0, int((width - 6) * ratio))
    inner = pygame.Rect(x + 3, y + 3, inner_width, height - 6)
    color = (189, 68, 61) if ratio <= 0.25 else fill_color
    pygame.draw.rect(screen, color, inner, border_radius=4)
    pygame.draw.rect(screen, (35, 38, 46), outer, 2, border_radius=5)
    _draw_text(screen, font, f"{hp}/{max_hp}", x + width - 82, y + 7, (255, 255, 255))


def _format_action(use: SkillUse | None) -> str:
    if use is None:
        return "第 0 回合：战斗开始"
    return f"第 {use.round_no} 回合：{use.skill} 攻击 BOSS {use.target}，伤害 {use.damage}"


def _draw_text(screen, font, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))


from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from maze_adventure import (
    DEFAULT_SKILLS,
    Skill,
    best_resource_path,
    generate_all_methods,
    generate_maze,
    is_perfect_maze,
    path_to_string,
    render_grid,
)
from maze_adventure.boss import estimate_boss_revives, optimize_boss_fight
from maze_adventure.io_format import dump_ai_json_file, dumps_ai_json, from_ai_json_payload, load_ai_json, to_ai_json_payload

METHOD_NAMES = {
    "division": "分治法",
    "mst": "贪心最小生成树",
    "dfs": "回溯 / DFS",
    "bfs_branch_bound": "分支限界 / BFS",
}

DEFAULT_CN_SKILLS = (
    Skill("普通攻击", damage=5, cooldown=0),
    Skill("大招", damage=10, cooldown=2),
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="算法驱动的迷宫探险游戏：迷宫设计任务命令行入口",
    )
    subparsers = parser.add_subparsers(dest="task", required=True, title="三个子任务")

    maze_parser = subparsers.add_parser(
        "maze",
        aliases=["task1", "任务一"],
        help="任务一：生成迷宫并对比四类算法",
        description="任务一：分别采用分治、贪心最小生成树、回溯/DFS、分支限界/BFS生成迷宫。",
    )
    maze_parser.add_argument("-n", "--size", type=int, default=15, help="迷宫尺寸，表示 n x n")
    maze_parser.add_argument(
        "-m",
        "--method",
        default="all",
        choices=["all", "division", "mst", "dfs", "bfs_branch_bound"],
        help="生成算法，all 表示四种算法全部生成",
    )
    maze_parser.add_argument("--seed", type=int, default=7, help="随机种子")
    maze_parser.add_argument("--no-resources", action="store_true", help="不放置金币、陷阱和BOSS")
    maze_parser.add_argument("--record", action="store_true", help="记录生成过程帧数")
    maze_parser.add_argument("--json", action="store_true", help="按照 AI 玩家输入 JSON 格式输出迷宫")
    maze_parser.add_argument("--json-file", type=Path, help="将 AI 玩家输入 JSON 写入文件")
    maze_parser.add_argument("--boss-hp", type=int, nargs="+", default=[30], help="JSON 输出中的 BOSS 血量数组 B")
    maze_parser.add_argument("--min-rounds", type=int, default=20, help="JSON 输出中的 minRouds 字段")
    maze_parser.add_argument("--coin-consumption", type=int, default=5, help="JSON 输出中的 CoinConsumption 字段")
    maze_parser.add_argument(
        "--skill",
        action="append",
        type=parse_skill,
        metavar="??:??:??",
        help="???????????????--skill ????:5:0 --skill ??:10:2",
    )
    maze_parser.set_defaults(handler=run_maze_task)

    resource_parser = subparsers.add_parser(
        "resource",
        aliases=["task2", "任务二"],
        help="任务二：动态规划求最优资源收集路径",
        description="任务二：输入迷宫矩阵，设定金币和陷阱价值，输出最多资源和最优资源路径。",
    )
    resource_parser.add_argument("--maze-file", type=Path, help="可选：从文本文件读取迷宫矩阵")
    resource_parser.add_argument("-n", "--size", type=int, default=15, help="未提供文件时生成的迷宫尺寸")
    resource_parser.add_argument(
        "-m",
        "--method",
        default="dfs",
        choices=["division", "mst", "dfs", "bfs_branch_bound"],
        help="未提供文件时使用的迷宫生成算法",
    )
    resource_parser.add_argument("--seed", type=int, default=7, help="未提供文件时使用的随机种子")
    resource_parser.add_argument("--coin-value", type=int, default=50, help="金币价值")
    resource_parser.add_argument("--trap-value", type=int, default=-30, help="陷阱价值")
    resource_parser.add_argument("--show-walk", action="store_true", help="显示包含回退的完整行走路径")
    resource_parser.set_defaults(handler=run_resource_task)

    boss_parser = subparsers.add_parser(
        "boss",
        aliases=["task3", "任务三"],
        help="任务三：分支限界优化BOSS战策略",
        description="任务三：输入BOSS血量和技能，输出最少回合数、最优技能序列、限定回合数和复活金币。",
    )
    boss_parser.add_argument("--boss-hp", type=int, nargs="+", default=[30], help="一个或多个BOSS血量")
    boss_parser.add_argument("--min-rounds", "--round-limit", dest="min_rounds", type=int, default=20, help="规定回合数，对应 JSON 字段 minRouds")
    boss_parser.add_argument("--revive-coin", "--coin-consumption", dest="revive_coin", type=int, default=5, help="每次复活需要消耗的金币数，对应 CoinConsumption")
    boss_parser.add_argument("--coins", type=int, default=100, help="玩家初始金币 (指定 --maze-file 时自动从迷宫计算，忽略此值)")
    boss_parser.add_argument("--maze-file", type=Path, help="从 AI 玩家 JSON 文件读取迷宫并自动计算初始金币")
    boss_parser.add_argument(
        "--skill",
        action="append",
        type=parse_skill,
        metavar="名称:伤害:冷却",
        help="自定义技能，可重复填写，例如：--skill 普通攻击:5:0 --skill 大招:10:2",
    )
    boss_parser.set_defaults(handler=run_boss_task)

    return parser

def parse_skill(spec: str) -> Skill:
    spec = spec.strip()
    if spec.startswith("[") and spec.endswith("]"):
        arr = [int(x) for x in spec.strip("[]").split(",")]
        if len(arr) != 2:
            raise argparse.ArgumentTypeError("skill format: [damage,cooldown] e.g. [5,0]")
        return Skill("skill", damage=int(arr[0]), cooldown=int(arr[1]))
    parts = spec.split(":")
    if len(parts) == 2:
        return Skill("skill", damage=int(parts[0]), cooldown=int(parts[1]))
    if len(parts) == 3:
        name, dmg, cd = parts
        return Skill(name, damage=int(dmg), cooldown=int(cd))
    raise argparse.ArgumentTypeError("skill format: name:damage:cooldown or damage:cooldown or [damage,cooldown]")

def run_maze_task(args: argparse.Namespace) -> None:
    decorate = not args.no_resources
    if not args.json:
        print("【任务一：迷宫生成与算法对比】")
        print(f"迷宫尺寸：{args.size} x {args.size}")
        print(f"随机种子：{args.seed}")
        print(f"是否放置资源和BOSS：{yes_no(decorate)}")

    if args.method == "all":
        results = generate_all_methods(args.size, seed=args.seed, decorate=decorate, record=args.record)
    else:
        result = generate_maze(
            args.size,
            method=args.method,
            seed=args.seed,
            decorate=decorate,
            record=args.record,
        )
        results = {result.method: result}

    if args.json or args.json_file:
        payloads = {
            method: to_ai_json_payload(
                result.grid,
                boss_hp=args.boss_hp,
                player_skills=args.skill if args.skill else DEFAULT_SKILLS,
                min_rounds=args.min_rounds,
                coin_consumption=args.coin_consumption,
            )
            for method, result in results.items()
        }
        output_payload = next(iter(payloads.values())) if len(payloads) == 1 else {"mazes": payloads}
        if args.json_file:
            dump_ai_json_file(args.json_file, output_payload)
            print(f"AI玩家输入JSON已写入：{args.json_file}")
        if args.json:
            print(dumps_ai_json(output_payload))
        if args.json:
            return

    for method, result in results.items():
        print(f"\n--- {METHOD_NAMES.get(method, method)}（接口名：{method}）---")
        print("迷宫矩阵：")
        print(render_grid(result.grid))
        print(f"连通且存在唯一通路（完美迷宫）：{yes_no(is_perfect_maze(result.grid))}")
        if result.frames:
            print(f"生成过程可视化帧数：{len(result.frames)}")

    print("\n说明：#为墙，.为通路，S为起点，E为终点，C为金币，T为陷阱，B为BOSS。")
    print("生成过程可视化命令：")
    if args.method == "all":
        print(f".venv/bin/python visualize_pygame.py --mode generate --method all --size {args.size} --seed {args.seed}")
    else:
        print(f".venv/bin/python visualize_pygame.py --mode generate --method {args.method} --size {args.size} --seed {args.seed}")

def run_resource_task(args: argparse.Namespace) -> None:
    print("【任务二：动态规划资源收集路径规划】")
    print(f"金币价值：{args.coin_value}")
    print(f"陷阱价值：{args.trap_value}")

    if args.maze_file:
        grid = read_grid_file(args.maze_file)
        print(f"迷宫来源：文件 {args.maze_file}")
    else:
        generated = generate_maze(args.size, method=args.method, seed=args.seed, decorate=True)
        grid = generated.grid
        print(f"迷宫来源：自动生成，算法={METHOD_NAMES.get(args.method, args.method)}，尺寸={args.size} x {args.size}，随机种子={args.seed}")

    print("\n输入迷宫矩阵：")
    print(render_grid(grid))

    plan = best_resource_path(grid, coin_value=args.coin_value, trap_value=args.trap_value)
    print("\n动态规划输出：")
    print(f"最多可获得资源值：{plan.max_value}")
    print("最优资源收集路径（不包含起点和终点）：")
    print(path_to_string(plan.path) if plan.path else "无")
    print(f"实际收集到的资源格子数量：{len(plan.collected)}")
    if args.show_walk:
        print("包含回退的完整行走路径：")
        print(path_to_string(plan.walk))

def run_boss_task(args: argparse.Namespace) -> None:
    skills: Sequence[Skill] = tuple(args.skill) if args.skill else DEFAULT_CN_SKILLS

    # 如果指定了 --maze-file，从迷宫自动计算金币和BOSS配置
    if args.maze_file:
        payload = load_ai_json(args.maze_file)
        grid, file_boss_hp, file_skills, file_min_rounds, file_coin_cost = from_ai_json_payload(payload)
        args.boss_hp = list(file_boss_hp)
        skills = file_skills if not args.skill else skills
        args.min_rounds = file_min_rounds
        args.revive_coin = file_coin_cost
        plan = best_resource_path(grid)
        from maze_adventure.core import COIN, TRAP
        g_count = sum(1 for r, c in plan.collected if grid[r][c] == COIN)
        t_count = sum(1 for r, c in plan.collected if grid[r][c] == TRAP)
        args.coins = g_count * 50 + t_count * (-30)
        print(f"【从迷宫文件自动计算】G={g_count}个 x50 + T={t_count}个 x(-30) = {args.coins} 金币")

    round_limit = max(1, args.min_rounds)
    plan = optimize_boss_fight(args.boss_hp, skills=skills, revive_coin=args.revive_coin)

    print("【任务三：分支限界BOSS战策略优化】")
    print(f"BOSS血量：{format_hp(tuple(args.boss_hp))}")
    print(f"规定回合数 minRouds：{round_limit}")
    print(f"玩家初始金币：{args.coins}")
    print(f"每次复活消耗 CoinConsumption：{plan.revive_coin}")
    print("战斗规则：BOSS不会反击；若未在规定回合数内全部击败BOSS，玩家死亡并需要确认复活，复活后BOSS当前血量保持不变。")
    print("AI玩家技能：")
    for skill in skills:
        print(f"  - {skill.name}：伤害 {skill.damage}，冷却 {skill.cooldown} 回合")

    print("\n分支限界输出：")
    print(f"最少回合数：{plan.min_rounds}")
    print(f"规定回合数：{round_limit}")
    print(f"每次复活消耗金币：{plan.revive_coin}")
    print("最优技能序列：")
    for use in plan.sequence:
        print(
            f"  第 {use.round_no} 回合：{use.skill} -> BOSS {use.target}，"
            f"造成 {use.damage} 点伤害，剩余血量：{format_hp(use.remaining_hp)}"
        )

    revive_summary = estimate_boss_revives(plan, round_limit=round_limit, coins=args.coins)
    total_rounds = revive_summary["total_rounds"]
    actual_round_limit = revive_summary["round_limit"]
    required_revives = revive_summary["required_revives"]
    spent_coins = revive_summary["spent_coins"]
    remaining_coins = revive_summary["remaining_coins"]
    survived = revive_summary["survived"]
    print("\n超回合复活估算：")
    print(f"战斗总回合数：{total_rounds}")
    print(f"每轮规定回合数：{actual_round_limit}")
    print(f"预计复活次数：{required_revives}")
    print(f"预计复活消耗金币：{spent_coins}")
    print(f"战后剩余金币：{remaining_coins}")
    print(f"金币是否足以完成战斗：{yes_no(bool(survived))}")
    print()
    print("【提示】explore_maze() 自动从迷宫G收集金币传入BOSS战，打通全流程。")

    hp_args = " ".join(str(value) for value in args.boss_hp)
    print("\n可视化提示：BOSS战窗口提供“确认复活”按钮，点击后会消耗金币并从当前BOSS血量继续战斗。")
    print(f"启动命令：.venv/bin/python visualize_boss.py --boss-hp {hp_args} --min-rounds {round_limit} --revive-coin {plan.revive_coin} --coins {args.coins}")

def read_grid_file(path: Path) -> list[list[str]]:
    if path.suffix.lower() == ".json":
        payload = load_ai_json(path)
        if "maze" not in payload:
            raise ValueError("JSON 文件必须包含 maze 字段")
        grid, _, _, _, _ = from_ai_json_payload(payload)
        return grid

    lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError("迷宫文件为空")
    width = len(lines[0])
    if any(len(line) != width for line in lines):
        raise ValueError("迷宫文件每一行长度必须相同")
    return [list(line) for line in lines]

def format_hp(hp: tuple[int, ...]) -> str:
    return "，".join(f"BOSS {index}: {value}" for index, value in enumerate(hp))

def yes_no(value: bool) -> str:
    return "是" if value else "否"

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)

if __name__ == "__main__":
    main()

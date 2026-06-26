#!/usr/bin/env python3
"""
完整流程测试：迷宫 → 资源收集 → BOSS 战 → 金币结算
"""
import sys
sys.path.insert(0, ".")

from pathlib import Path
from maze_adventure import (
    generate_maze, load_ai_json, from_ai_json_payload,
    explore_maze, render_grid, path_to_string
)
from maze_adventure.boss import estimate_boss_revives

SEP = "=" * 70

# ============================================
# 1. 选择迷宫
# ============================================
print(SEP)
print("  1. 迷宫来源")
print(SEP)

maze_file = Path("E:/maze_15_15.json")
if maze_file.exists():
    ext = load_ai_json(maze_file)
    grid, boss_hp, skills, min_rounds, coin_cost = from_ai_json_payload(ext)
    print(f"  外部文件: E:/maze_15_15.json")
else:
    print(f"  外部文件不存在，自动生成迷宫...")
    result = generate_maze(15, method="dfs", seed=7, decorate=True)
    grid = result.grid
    boss_hp = [11, 13, 9, 15]
    skills = tuple([
        type("S", (), {"name": f"技能{i}", "damage": d, "cooldown": c})()
        for i, (d, c) in enumerate([(8,4),(2,0),(4,2),(6,3)])
    ])
    min_rounds = 20
    coin_cost = 5

print(f"  BOSS HP: {list(boss_hp)}")
print(f"  技能: {[(s.name, s.damage, s.cooldown) for s in skills]}")
print(f"  minRouds: {min_rounds}")
print(f"  CoinConsumption: {coin_cost}")
print()
print(render_grid(grid))

# ============================================
# 2. 全流程探险
# ============================================
print(SEP)
print("  2. 迷宫探险 (explore_maze)")
print(SEP)

explore = explore_maze(grid, boss_hp=boss_hp, skills=skills)
plan = explore.boss_plan

print(f"  是否到达终点 E: {explore.reached_end}")
print(f"  总步数: {explore.steps}")
print(f"  剩余价值(金币-陷阱): {explore.remaining_value}")
print(f"  玩家实际金币: {explore.coins}")
print(f"  行走路径: {path_to_string(explore.walk[:5])} ... {path_to_string(explore.walk[-3:])}")

# ============================================
# 3. BOSS 战
# ============================================
print()
print(SEP)
print("  3. BOSS 战最优策略")
print(SEP)

print(f"  最少回合数: {plan.min_rounds}")
print(f"  技能序列:")
for u in plan.sequence:
    print(f"    R{u.round_no:2d}: {u.skill} -> Boss{u.target}, -{u.damage}, 剩余HP={list(u.remaining_hp)}")

# ============================================
# 4. 金币结算
# ============================================
print()
print(SEP)
print("  4. 金币结算")
print(SEP)

summary = estimate_boss_revives(plan, round_limit=min_rounds, coins=explore.coins)
print(f"  玩家初始金币 (来自迷宫): {explore.coins}")
print(f"  minRouds: {min_rounds}")
print(f"  BOSS 战总回合: {summary['total_rounds']}")
print(f"  需要复活: {summary['required_revives']} 次")
print(f"  消耗金币: {summary['spent_coins']}")
print(f"  剩余金币: {summary['remaining_coins']}")
print(f"  金币足够存活: {summary['survived']}")

# 如果金币不够, 试试不同 minRouds
if not summary["survived"]:
    print()
    print("  [!] 金币不足! 尝试不同 minRouds:")
    for rl in [5, 10, 15, 20]:
        s = estimate_boss_revives(plan, round_limit=rl, coins=explore.coins)
        print(f"    minRouds={rl:2d}: 复活{s['required_revives']}次, 消耗{s['spent_coins']}, 剩余{s['remaining_coins']}, {'存活' if s['survived'] else '破产'}")

# ============================================
# 5. 总结
# ============================================
print()
print(SEP)
print("  5. 总结")
print(SEP)
print(f"  迷宫 G 收集: {sum(1 for r,c in explore.walk if grid[r][c] == 'G')} 个")

from maze_adventure import TRAP, COIN
g_count = sum(1 for r,c in explore.walk if grid[r][c] == COIN)
t_count = sum(1 for r,c in explore.walk if grid[r][c] == TRAP)
print(f"  迷宫 T 踩到: {t_count} 个")
print(f"  金币公式: {g_count} x 50 + ({t_count}) x (-30) = {explore.coins}")
print(f"  BOSS 战结果: {summary['total_rounds']} 回合, 消耗{summary['spent_coins']}金币, 剩余{summary['remaining_coins']}")

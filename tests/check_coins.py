import sys
sys.path.insert(0, ".")

from pathlib import Path
from maze_adventure import (
    explore_maze, best_resource_path,
    load_ai_json, from_ai_json_payload,
    COIN, TRAP
)
from maze_adventure.boss import estimate_boss_revives

ext = load_ai_json(Path("E:/maze_15_15.json"))
grid, boss_hp, skills, min_rounds, coin_cost = from_ai_json_payload(ext)

print("=== 最优资源路径 ===")
plan = best_resource_path(grid)
print(f"  最大资源值: {plan.max_value}")
print(f"  收集格子数: {len(plan.collected)}")

g_count = t_count = 0
for r, c in plan.collected:
    cell = grid[r][c]
    if cell == COIN:
        g_count += 1
    elif cell == TRAP:
        t_count += 1
coin_wallet = g_count * 50
print(f"  其中金币G: {g_count} 个 -> {coin_wallet} 金币")
print(f"  其中陷阱T: {t_count} 个 -> {t_count * -30} 价值")

print()
print("=== 探索结果 ===")
explore = explore_maze(grid, boss_hp=boss_hp, skills=skills)
print(f"  剩余价值: {explore.remaining_value}")
print(f"  BOSS 最少回合: {explore.boss_plan.min_rounds}")

print()
print("=== BOSS 复活估算 ===")
summary = estimate_boss_revives(explore.boss_plan, round_limit=20, coins=coin_wallet)
print(f"  初始金币(来自迷宫G): {coin_wallet}")
print(f"  复活消耗: {summary['spent_coins']}")
print(f"  剩余金币: {summary['remaining_coins']}")
print(f"  能否存活: {summary['survived']}")

# ===== 现在对比：如果用 CLI 默认 --coins 100 =====
print()
print("=== 对比: CLI 默认 --coins 100 ===")
summary2 = estimate_boss_revives(explore.boss_plan, round_limit=20, coins=100)
print(f"  初始金币(硬编码): 100")
print(f"  复活消耗: {summary2['spent_coins']}")
print(f"  剩余金币: {summary2['remaining_coins']}")

# ===== 如果 minRouds 很小 =====
print()
print("=== minRouds=3, 金币来自迷宫 ===")
summary3 = estimate_boss_revives(explore.boss_plan, round_limit=3, coins=coin_wallet)
print(f"  初始金币(来自迷宫G): {coin_wallet}")
print(f"  总回合: {summary3['total_rounds']}, 复活: {summary3['required_revives']}")
print(f"  消耗金币: {summary3['spent_coins']}")
print(f"  剩余金币: {summary3['remaining_coins']}")
print(f"  能否存活: {summary3['survived']}")

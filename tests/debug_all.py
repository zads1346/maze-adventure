"""迷宫探险项目 — 全功能调试脚本"""
import sys
sys.path.insert(0, r"C:\Users\lenovo\Desktop\al")

import json, math, os
from pathlib import Path
from maze_adventure import (
    BOSS, COIN, END, PATH, START, TRAP, WALL,
    best_resource_path, decorate_maze, dumps_ai_json, explore_maze,
    from_ai_json_payload, generate_all_methods, generate_maze,
    greedy_pickup, is_connected, is_perfect_maze, load_ai_json,
    optimize_boss_fight, path_to_string, render_grid, shortest_path,
    to_ai_json_payload,
)
from maze_adventure.boss import estimate_boss_revives, DEFAULT_SKILLS
from maze_adventure.core import (
    all_walkable_positions, build_graph, clone_grid, find_cell,
    resource_value, score_walk, walkable_neighbors,
)
from maze_adventure.models import Skill

_SEP = "=" * 70
_SUB = "-" * 50
_PASS = "PASS"
_FAIL = "FAIL"

def heading(title):
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)

def subheading(title):
    print(f"\n{_SUB}")
    print(f"  {title}")
    print(_SUB)

def check(ok, msg):
    status = _PASS if ok else _FAIL
    print(f"  [{status}] {msg}")
    return ok

all_ok = True

# ===== 1. Maze Generation =====
heading("1. Maze Generation (4 algorithms)")
for method in ("division", "mst", "dfs", "bfs_branch_bound"):
    subheading(f"Method: {method}")
    result = generate_maze(15, method=method, seed=7, decorate=False)
    g = result.grid
    s = find_cell(g, START)
    e = find_cell(g, END)
    perfect = is_perfect_maze(g)
    connected = is_connected(g)
    all_ok &= check(len(g)==15 and len(g[0])==15, f"Size 15x15")
    all_ok &= check(perfect, f"Perfect maze (no loops)")
    all_ok &= check(connected, f"All walkable cells connected")
    all_ok &= check(g[s[0]][s[1]]==START, f"Start S at {s}")
    all_ok &= check(g[e[0]][e[1]]==END, f"End E at {e}")
    if method == "dfs":
        print(render_grid(g))

subheading("Decorated maze (coins + traps)")
deco = generate_maze(15, method="dfs", seed=7, decorate=True).grid
coins = sum(row.count(COIN) for row in deco)
traps = sum(row.count(TRAP) for row in deco)
all_ok &= check(coins>0, f"Coin count: {coins}")
all_ok &= check(traps>0, f"Trap count: {traps}")
print(render_grid(deco))

subheading("generate_all_methods()")
all_results = generate_all_methods(11, seed=3, decorate=False)
all_ok &= check(len(all_results)==4, f"Returns 4 methods")
all_ok &= check(set(all_results)=={"division","mst","dfs","bfs_branch_bound"}, f"Method names correct")

# ===== 2. JSON I/O =====
heading("2. JSON I/O Serialization & Parsing")
skills_in = (Skill("S1", damage=5, cooldown=0), Skill("S2", damage=12, cooldown=3))
payload = to_ai_json_payload(deco, [30, 25], skills_in, min_rounds=20, coin_consumption=5)
all_ok &= check(set(payload)=={"maze","B","PlayerSkills","minRouds","CoinConsumption"}, "Field names complete")

grid_out, hp_out, skills_out, rounds_out, coin_out = from_ai_json_payload(payload)
all_ok &= check(hp_out==(30,25), f"B: {hp_out}")
all_ok &= check(rounds_out==20, f"minRouds: {rounds_out}")
all_ok &= check(coin_out==5, f"CoinConsumption: {coin_out}")
all_ok &= check(len(skills_out)==2, f"Skills count: {len(skills_out)}")
all_ok &= check(skills_out[0].damage==5 and skills_out[1].damage==12, "Skill damage correct")

dumped = dumps_ai_json(payload)
all_ok &= check('"minRouds": 20' in dumped, f"dumps contains minRouds")
print(f"  dumps output length: {len(dumped)} chars")

# ===== 3. External JSON loading =====
heading("3. Load External JSON: E:/maze_15_15.json")
ext = load_ai_json(Path(r"E:/maze_15_15.json"))
ext_grid, ext_boss, ext_skills, ext_rounds, ext_coin = from_ai_json_payload(ext)
all_ok &= check(len(ext_grid)==15 and len(ext_grid[0])==15, "15x15 grid")
all_ok &= check(ext_boss==(11,13,9,15), f"Boss HP: {ext_boss}")
all_ok &= check(len(ext_skills)==4, f"Skills count: {len(ext_skills)}")
all_ok &= check(ext_rounds==20, f"minRouds: {ext_rounds}")
all_ok &= check(ext_coin==5, f"CoinConsumption: {ext_coin}")

s_pos = find_cell(ext_grid, START)
e_pos = find_cell(ext_grid, END)
all_ok &= check(s_pos==(0,11), f"S at {s_pos}")
all_ok &= check(e_pos==(14,9), f"E at {e_pos}")
all_ok &= check(is_connected(ext_grid), "Grid fully connected")
print(render_grid(ext_grid))

# ===== 4. Core utilities =====
heading("4. Core Utility Functions")
sp = shortest_path(ext_grid)
all_ok &= check(len(sp)>0, f"Shortest path length: {len(sp)}")
all_ok &= check(sp[0]==s_pos, "Path starts at S")
all_ok &= check(sp[-1]==e_pos, "Path ends at E")
print(f"  Path: {path_to_string(sp[:5])} ... {path_to_string(sp[-3:])}")

graph = build_graph(ext_grid)
all_ok &= check(len(graph)>0, f"Graph nodes: {len(graph)}")

walkable = all_walkable_positions(ext_grid)
all_ok &= check(len(walkable)>0, f"Walkable cells: {len(walkable)}")

rv_c, rv_t, rv_p = resource_value(COIN,50,-30), resource_value(TRAP,50,-30), resource_value(PATH,50,-30)
all_ok &= check(rv_c==50 and rv_t==-30 and rv_p==0, f"Values: coin={rv_c}, trap={rv_t}, path={rv_p}")

rendered = render_grid(ext_grid, path=sp[:10], current=s_pos)
all_ok &= check(len(rendered)>0, "render_grid with path+pos works")

# ===== 5. Resource Path DP =====
heading("5. DP: Optimal Resource Collection Path")
plan = best_resource_path(ext_grid)
all_ok &= check(plan.max_value!=0, f"Max resource value: {plan.max_value}")
all_ok &= check(len(plan.path)>0, f"Path cells: {len(plan.path)}")
all_ok &= check(len(plan.collected)>0, f"Collected items: {len(plan.collected)}")
print(f"  Path: {path_to_string(plan.path[:6])} ...")

deco_plan = best_resource_path(deco)
all_ok &= check(deco_plan.max_value!=0, f"Decorated maze max value: {deco_plan.max_value}")
all_ok &= check(deco_plan.walk[0]==find_cell(deco,START), "Walk starts at S")
all_ok &= check(deco_plan.walk[-1]==find_cell(deco,END), "Walk ends at E")

# ===== 6. Greedy Pickup =====
heading("6. Greedy Pickup")
decision = greedy_pickup(ext_grid, (1,1))
all_ok &= check(decision.value>0, f"Nearby resource value: {decision.value}")
all_ok &= check(decision.target is not None, f"Target: {decision.target}")
all_ok &= check(decision.score>0, f"Score: {decision.score:.2f}")

# ===== 7. Boss Fight Optimization =====
heading("7. Boss Fight: Branch & Bound Optimization")
skills = (Skill("Attack", damage=5, cooldown=0), Skill("Power", damage=10, cooldown=2))

bp = optimize_boss_fight(20, skills=skills)
all_ok &= check(bp.min_rounds==3, f"Single boss 20HP -> min rounds: {bp.min_rounds}")
all_ok &= check(len(bp.sequence)==3, f"Sequence length: {len(bp.sequence)}")
for u in bp.sequence:
    print(f"  R{u.round_no:2d}: {u.skill} -> Boss{u.target}, -{u.damage}, remaining {u.remaining_hp}")

mp = optimize_boss_fight([11,13,9,15], skills=skills)
all_ok &= check(mp.min_rounds>0, f"Multi boss [11,13,9,15] -> min rounds: {mp.min_rounds}")
print(f"  Multi-boss sequence ({mp.min_rounds} rounds):")
for u in mp.sequence:
    print(f"    R{u.round_no:2d}: {u.skill} -> Boss{u.target}, -{u.damage}")

ext_bp = optimize_boss_fight(ext_boss, skills=ext_skills)
all_ok &= check(ext_bp.min_rounds>0, f"External JSON skills -> min rounds: {ext_bp.min_rounds}")

zp = optimize_boss_fight(0, skills=skills)
all_ok &= check(zp.min_rounds==0, f"Zero HP boss -> 0 rounds")

try:
    optimize_boss_fight(10, skills=(Skill("Bad", damage=5, cooldown=1),))
    all_ok &= check(False, "No zero-cooldown skill -> should raise")
except ValueError:
    all_ok &= check(True, "No zero-cooldown skill -> ValueError raised")

# ===== 8. Boss Revive Estimation =====
heading("8. Boss Revive Estimation")
summary = estimate_boss_revives(mp, round_limit=20, coins=100)
all_ok &= check(summary["total_rounds"]==mp.min_rounds, f"Total rounds: {summary['total_rounds']}")
all_ok &= check(summary["spent_coins"]>=0, f"Spent coins: {summary['spent_coins']}")
all_ok &= check(summary["remaining_coins"]>=0, f"Remaining coins: {summary['remaining_coins']}")
print(f"  Boss fight {summary['total_rounds']} rounds, {summary['required_revives']} revives, spent {summary['spent_coins']}, remaining {summary['remaining_coins']}")

poor = estimate_boss_revives(mp, round_limit=2, coins=5)
print(f"  Poor coin scenario: spent={poor['spent_coins']}, survived={poor['survived']}")

# ===== 9. Full AI Exploration =====
heading("9. Full AI Exploration (explore_maze)")
explore = explore_maze(ext_grid, boss_hp=ext_boss, skills=ext_skills)
all_ok &= check(explore.reached_end, "Reached end E")
all_ok &= check(explore.steps>0, f"Total steps: {explore.steps}")
all_ok &= check(explore.remaining_value!=0, f"Collected value: {explore.remaining_value}")
all_ok &= check(len(explore.walk)>0, f"Walk length: {len(explore.walk)}")
all_ok &= check(len(explore.frames)>0, f"Frames: {len(explore.frames)}")
all_ok &= check(explore.boss_plan is not None, "Boss plan generated")
if explore.boss_plan:
    print(f"  Steps: {explore.steps}, value: {explore.remaining_value}, boss min rounds: {explore.boss_plan.min_rounds}")

# ===== 10. Recording & Custom Decoration =====
heading("10. Record Frames & Custom Decoration")
rec = generate_maze(11, method="dfs", seed=5, decorate=False, record=True)
all_ok &= check(len(rec.frames)>1, f"Recorded frames: {len(rec.frames)}")

cust = decorate_maze(rec.grid, seed=5, coin_count=5, trap_count=3)
cc = sum(row.count(COIN) for row in cust)
tc = sum(row.count(TRAP) for row in cust)
all_ok &= check(cc==5, f"Custom coins: {cc}")
all_ok &= check(tc==3, f"Custom traps: {tc}")

# ===== 11. Edge Cases =====
heading("11. Edge & Error Cases")
try:
    optimize_boss_fight(10, skills=[])
    all_ok &= check(False, "Empty skills -> should raise")
except ValueError:
    all_ok &= check(True, "Empty skills -> ValueError")

try:
    optimize_boss_fight(10, skills=(Skill("Bad", damage=-1, cooldown=0),))
    all_ok &= check(False, "Negative damage -> should raise")
except ValueError:
    all_ok &= check(True, "Negative damage -> ValueError")

try:
    optimize_boss_fight(10, skills=(Skill("BadCD", damage=5, cooldown=-1),))
    all_ok &= check(False, "Negative cooldown -> should raise")
except ValueError:
    all_ok &= check(True, "Negative cooldown -> ValueError")

try:
    from_ai_json_payload({"maze":[],"B":[10],"PlayerSkills":[[5,0]],"minRouds":10,"CoinConsumption":1})
    all_ok &= check(False, "Empty maze -> should raise")
except ValueError:
    all_ok &= check(True, "Empty maze -> ValueError")

try:
    from_ai_json_payload({"maze":[["#","S","#"]],"B":[10]})
    all_ok &= check(False, "Missing fields -> should raise")
except ValueError:
    all_ok &= check(True, "Missing fields -> ValueError")

# ===== Summary =====
heading("SUMMARY")
print(f"\n  Overall: {'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")
print(f"  Modules covered:")
print(f"  - Maze generation: 4 algorithms (division/mst/dfs/bfs_branch_bound)")
print(f"  - Maze validation: is_perfect_maze / is_connected")
print(f"  - JSON I/O: serialize / parse / file load")
print(f"  - Core: shortest_path / build_graph / render_grid")
print(f"  - Resources: DP optimal path planning")
print(f"  - Greedy pickup: local decisions")
print(f"  - Boss fight: branch & bound + revive estimation")
print(f"  - AI exploration: full S->E pipeline")
print(f"  - Decoration / recording / edge cases")

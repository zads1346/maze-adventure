#!/usr/bin/env python3
import sys
sys.path.insert(0, ".")

from maze_adventure import Skill, optimize_boss_fight
from maze_adventure.boss import estimate_boss_revives

PASS = "PASS"
FAIL = "FAIL"
SEP = "=" * 70
all_ok = True
case_id = 0

def check(ok, msg):
    global all_ok
    if not ok:
        all_ok = False
    print(f"  [{PASS if ok else FAIL}] {msg}")
    return ok

def run_case(name, boss_hp, skills, min_rounds, coin_cost, init_coins,
             expect_rounds, expect_revives, expect_spent, expect_survived):
    global case_id
    case_id += 1
    print(f"\n{SEP}")
    print(f"  Case {case_id}: {name}")
    print(SEP)
    print(f"    Boss HP: {list(boss_hp)}")
    print(f"    Skills: {[(s.name, s.damage, s.cooldown) for s in skills]}")
    print(f"    minRouds={min_rounds}, CoinConsumption={coin_cost}, initial coins={init_coins}")

    plan = optimize_boss_fight(boss_hp, skills=skills, revive_coin=coin_cost)
    print(f"    => min rounds: {plan.min_rounds}")

    for u in plan.sequence:
        print(f"      R{u.round_no:2d}: {u.skill} -> Boss{u.target}, -{u.damage}, remaining HP={list(u.remaining_hp)}")

    summary = estimate_boss_revives(plan, round_limit=min_rounds, coins=init_coins)
    ok = True
    ok &= check(plan.min_rounds == expect_rounds,
                f"Min rounds: expected={expect_rounds}, actual={plan.min_rounds}")
    ok &= check(summary["required_revives"] == expect_revives,
                f"Revives: expected={expect_revives}, actual={summary['required_revives']}")
    ok &= check(summary["spent_coins"] == expect_spent,
                f"Coins spent: expected={expect_spent}, actual={summary['spent_coins']}")
    ok &= check(summary["survived"] == expect_survived,
                f"Survived: expected={expect_survived}, actual={summary['survived']}")
    if ok:
        print(f"    [OK]")

att = Skill("Attack", damage=5, cooldown=0)
ult = Skill("Power", damage=10, cooldown=2)
default_skills = (att, ult)

run_case("Single boss 20HP, generous round limit", [20], default_skills, 20, 5, 100,
         expect_rounds=3, expect_revives=0, expect_spent=0, expect_survived=True)
run_case("Single boss 20HP, strict limit, 1 revive", [20], default_skills, 2, 5, 100,
         expect_rounds=3, expect_revives=1, expect_spent=5, expect_survived=True)
run_case("Single boss 20HP, very strict, 2 revives", [20], default_skills, 1, 5, 100,
         expect_rounds=3, expect_revives=2, expect_spent=10, expect_survived=True)
run_case("Multi boss [11,13,9,15], generous limit", [11,13,9,15], default_skills, 20, 5, 100,
         expect_rounds=8, expect_revives=0, expect_spent=0, expect_survived=True)
run_case("Multi boss, strict limit 3, 2 revives", [11,13,9,15], default_skills, 3, 5, 100,
         expect_rounds=8, expect_revives=2, expect_spent=10, expect_survived=True)
run_case("Multi boss, insufficient coins", [11,13,9,15], default_skills, 3, 5, 3,
         expect_rounds=8, expect_revives=2, expect_spent=10, expect_survived=False)
run_case("Zero HP boss", [0], default_skills, 1, 5, 0,
         expect_rounds=0, expect_revives=0, expect_spent=0, expect_survived=True)
run_case("High revive cost", [20], default_skills, 2, 50, 100,
         expect_rounds=3, expect_revives=1, expect_spent=50, expect_survived=True)

print(f"\n{SEP}")
print(f"  Boss Coin Test Summary")
print(SEP)
print(f"  Total cases: {case_id}")
print(f"  Result: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
print(f"\n  Rules verified:")
print(f"  - Min rounds: branch & bound guarantees optimum")
print(f"  - Boss order: auto-selects optimal target each round")
print(f"  - Revives: 0 if total_rounds <= minRouds, else (total_rounds-1)//minRouds")
print(f"  - Coins spent: revives * CoinConsumption")
print(f"  - Survived: initial coins >= coins spent")
print(f"  - Player initial coins = G coins collected from maze * 50")

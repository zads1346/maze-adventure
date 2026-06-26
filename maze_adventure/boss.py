from __future__ import annotations

import heapq
import math
from itertools import count
from typing import Sequence

from .models import BossPlan, Skill, SkillUse


DEFAULT_SKILLS = (
    Skill("Attack", damage=5, cooldown=0),
    Skill("Power", damage=10, cooldown=2),
)


def optimize_boss_fight(
    boss_hp: int | Sequence[int],
    skills: Sequence[Skill] = DEFAULT_SKILLS,
    revive_coin: int = 50,
) -> BossPlan:
    hp = _normalize_hp(boss_hp)
    skills = tuple(skills)
    _validate_skills(skills)

    if all(value <= 0 for value in hp):
        return BossPlan(min_rounds=0, sequence=[], limited_rounds=0, revive_coin=revive_coin)

    max_damage = max(skill.damage for skill in skills)
    cooldown_start = tuple(0 for _ in skills)
    sequence_counter = count()

    def lower_bound(rounds: int, remaining_hp: tuple[int, ...]) -> int:
        total_hp = sum(max(0, value) for value in remaining_hp)
        return rounds + math.ceil(total_hp / max_damage)

    start_bound = lower_bound(0, hp)
    heap: list[tuple[int, int, int, tuple[int, ...], tuple[int, ...], list[SkillUse]]] = [
        (start_bound, 0, next(sequence_counter), hp, cooldown_start, [])
    ]
    best_state_rounds: dict[tuple[tuple[int, ...], tuple[int, ...]], int] = {
        (hp, cooldown_start): 0
    }
    best_sequence: list[SkillUse] | None = None
    best_rounds = math.inf

    while heap:
        bound, rounds, _, current_hp, cooldowns, sequence = heapq.heappop(heap)
        if bound >= best_rounds:
            continue
        if all(value <= 0 for value in current_hp):
            best_rounds = rounds
            best_sequence = sequence
            continue

        available = [
            index
            for index, cooldown in enumerate(cooldowns)
            if cooldown == 0 and skills[index].damage > 0
        ]
        available.sort(key=lambda index: (-skills[index].damage, skills[index].cooldown))

        # BOSS 可选择任意存活目标攻击，优化总回合数
        alive_indices = [index for index, target_hp in enumerate(current_hp) if target_hp > 0]

        for target_index in alive_indices:
            target_hp = current_hp[target_index]
            for skill_index in available:
                skill = skills[skill_index]
                next_hp = list(current_hp)
                next_hp[target_index] = max(0, target_hp - skill.damage)
                next_hp_tuple = tuple(next_hp)
                next_rounds = rounds + 1
                next_cooldowns = _advance_cooldowns(cooldowns, skills, skill_index)
                use = SkillUse(
                    round_no=next_rounds,
                    skill=skill.name,
                    target=target_index,
                    damage=skill.damage,
                    remaining_hp=next_hp_tuple,
                )
                next_sequence = sequence + [use]

                if all(value <= 0 for value in next_hp_tuple):
                    if next_rounds < best_rounds:
                        best_rounds = next_rounds
                        best_sequence = next_sequence
                    continue

                next_bound = lower_bound(next_rounds, next_hp_tuple)
                if next_bound >= best_rounds:
                    continue

                state = (next_hp_tuple, next_cooldowns)
                if best_state_rounds.get(state, math.inf) <= next_rounds:
                    continue
                best_state_rounds[state] = next_rounds
                heapq.heappush(
                    heap,
                    (
                        next_bound,
                        next_rounds,
                        next(sequence_counter),
                        next_hp_tuple,
                        next_cooldowns,
                        next_sequence,
                    ),
                )

    if best_sequence is None:
        raise RuntimeError("no winning boss strategy found")

    min_rounds = int(best_rounds)
    limited_rounds = min_rounds + max(1, math.ceil(min_rounds * 0.2))
    return BossPlan(
        min_rounds=min_rounds,
        sequence=best_sequence,
        limited_rounds=limited_rounds,
        revive_coin=revive_coin,
    )


def estimate_boss_revives(
    plan: BossPlan,
    round_limit: int,
    coins: int,
) -> dict[str, int | bool]:
    if round_limit <= 0:
        raise ValueError("round limit must be positive")
    if coins < 0:
        raise ValueError("coins cannot be negative")

    total_rounds = len(plan.sequence)
    required_revives = 0 if total_rounds == 0 else (total_rounds - 1) // round_limit
    spent_coins = required_revives * plan.revive_coin
    return {
        "survived": coins >= spent_coins,
        "required_revives": required_revives,
        "spent_coins": spent_coins,
        "remaining_coins": max(0, coins - spent_coins),
        "total_rounds": total_rounds,
        "round_limit": round_limit,
    }


def estimate_boss_survival(
    plan: BossPlan,
    player_hp: int = 15,
    boss_damage: int = 6,
    coins: int = 100,
) -> dict[str, int | bool]:
    return estimate_boss_revives(plan, round_limit=max(1, plan.limited_rounds), coins=coins)


def boss_counter_damage(remaining_hp: Sequence[int], boss_damage: int) -> int:
    return 0


def _normalize_hp(boss_hp: int | Sequence[int]) -> tuple[int, ...]:
    if isinstance(boss_hp, int):
        return (max(0, boss_hp),)
    hp = tuple(max(0, int(value)) for value in boss_hp)
    if not hp:
        raise ValueError("at least one boss hp value is required")
    return hp


def _validate_skills(skills: Sequence[Skill]) -> None:
    if not skills:
        raise ValueError("at least one skill is required")
    if not any(skill.damage > 0 and skill.cooldown == 0 for skill in skills):
        raise ValueError("at least one positive-damage skill must have zero cooldown")
    for skill in skills:
        if skill.damage < 0:
            raise ValueError("skill damage cannot be negative")
        if skill.cooldown < 0:
            raise ValueError("skill cooldown cannot be negative")


def _advance_cooldowns(
    cooldowns: tuple[int, ...],
    skills: Sequence[Skill],
    used_index: int,
) -> tuple[int, ...]:
    next_values: list[int] = []
    for index, cooldown in enumerate(cooldowns):
        if index == used_index:
            next_values.append(skills[index].cooldown)
        else:
            next_values.append(max(0, cooldown - 1))
    return tuple(next_values)

from __future__ import annotations

import unittest

from maze_adventure import (
    BOSS,
    generate_all_methods,
    COIN,
    END,
    PATH,
    START,
    TRAP,
    Skill,
    best_resource_path,
    explore_maze,
    generate_maze,
    greedy_pickup,
    is_perfect_maze,
    optimize_boss_fight,
    to_ai_json_payload,
    dumps_ai_json,
    from_ai_json_payload,
)
from maze_adventure.boss import estimate_boss_revives
from maze_adventure.boss_visualizer import build_arg_parser as build_boss_arg_parser
from maze_adventure.pygame_visualizer import _frames_to_current_positions, _grid_from_frame, build_arg_parser
from main import build_parser as build_main_parser


class MazeAdventureTests(unittest.TestCase):
    def test_generators_create_perfect_mazes(self) -> None:
        for method in ("division", "mst", "dfs", "bfs_branch_bound"):
            with self.subTest(method=method):
                result = generate_maze(11, method=method, seed=3, decorate=True)
                self.assertTrue(is_perfect_maze(result.grid))

    def test_all_generators_record_generation_frames(self) -> None:
        results = generate_all_methods(11, seed=3, decorate=False, record=True)
        self.assertEqual(set(results), {"division", "mst", "dfs", "bfs_branch_bound"})
        for result in results.values():
            self.assertGreater(len(result.frames), 1)
            self.assertEqual(_grid_from_frame(result.frames[-1]), result.grid)

    def test_ai_json_payload_matches_required_format(self) -> None:
        grid = [
            list("#####"),
            ["#", START, PATH, COIN, "#"],
            ["#", TRAP, BOSS, END, "#"],
            list("#####"),
        ]
        skills = (Skill("普通攻击", damage=5, cooldown=0), Skill("大招", damage=10, cooldown=2))
        payload = to_ai_json_payload(grid, [30, 25], skills, min_rounds=20, coin_consumption=5)
        self.assertEqual(set(payload), {"maze", "B", "PlayerSkills", "minRouds", "CoinConsumption"})
        self.assertEqual(payload["maze"][1][2], " ")
        self.assertEqual(payload["maze"][1][3], "G")
        self.assertEqual(payload["B"], [30, 25])
        self.assertEqual(payload["PlayerSkills"], [[5, 0], [10, 2]])
        self.assertEqual(payload["minRouds"], 20)
        self.assertEqual(payload["CoinConsumption"], 5)
        json_text = dumps_ai_json(payload)
        self.assertIn("        [\"#\", \"S\", \" \", \"G\", \"#\"],", json_text)
        self.assertIn("    \"B\": [30, 25],", json_text)
        self.assertIn("    \"PlayerSkills\": [[5, 0], [10, 2]],", json_text)
        self.assertNotIn("\n            \"#\"", json_text)

        normalized_grid, boss_hp, parsed_skills, min_rounds, coin_consumption = from_ai_json_payload(payload)
        self.assertEqual(normalized_grid, grid)
        self.assertEqual(boss_hp, (30, 25))
        self.assertEqual([(skill.damage, skill.cooldown) for skill in parsed_skills], [(5, 0), (10, 2)])
        self.assertEqual(min_rounds, 20)
        self.assertEqual(coin_consumption, 5)

    def test_resource_dp_skips_negative_branch(self) -> None:
        grid = [
            list("#######"),
            [START, PATH, COIN, PATH, PATH, END, "#"],
            list("##.####"),
            ["#", "#", TRAP, "#", "#", "#", "#"],
            list("#######"),
        ]
        plan = best_resource_path(grid)
        self.assertEqual(plan.max_value, 50)
        self.assertIn((1, 2), plan.collected)
        self.assertNotIn((3, 2), plan.collected)

    def test_resource_dp_collects_profitable_branch(self) -> None:
        grid = [
            list("#######"),
            [START, PATH, COIN, PATH, PATH, END, "#"],
            list("##.####"),
            ["#", "#", COIN, "#", "#", "#", "#"],
            list("#######"),
        ]
        plan = best_resource_path(grid)
        self.assertEqual(plan.max_value, 100)
        self.assertIn((3, 2), plan.collected)

    def test_boss_branch_bound_finds_min_rounds(self) -> None:
        skills = (Skill("Attack", damage=5, cooldown=0), Skill("Power", damage=10, cooldown=2))
        plan = optimize_boss_fight(20, skills)
        self.assertEqual(plan.min_rounds, 3)
        self.assertEqual(len(plan.sequence), 3)

    def test_greedy_pickup_prefers_visible_coin(self) -> None:
        grid = [
            list("#####"),
            [START, PATH, COIN, "#", "#"],
            ["#", TRAP, PATH, "#", "#"],
            ["#", "#", END, "#", "#"],
            list("#####"),
        ]
        decision = greedy_pickup(grid, (1, 1))
        self.assertEqual(decision.target, (1, 2))
        self.assertEqual(decision.value, 50)

    def test_explore_maze_reaches_end(self) -> None:
        result = generate_maze(11, method="dfs", seed=5, decorate=True)
        exploration = explore_maze(result.grid, boss_hp=20)
        self.assertTrue(exploration.reached_end)
        self.assertGreater(exploration.steps, 0)


    def test_pygame_visualizer_helpers_do_not_require_display(self) -> None:
        args = build_arg_parser().parse_args(["--size", "9", "--mode", "generate", "--method", "all"])
        self.assertEqual(args.size, 9)
        self.assertEqual(args.mode, "generate")
        self.assertEqual(args.method, "all")

        frames = ["###\n#.#\n###", "###\n#..\n###"]
        positions = _frames_to_current_positions(frames, [list("#S#")])
        self.assertEqual(positions, [(1, 1), (1, 2)])


    def test_boss_visualizer_parser_accepts_multiple_bosses(self) -> None:
        args = build_boss_arg_parser().parse_args(
            [
                "--boss-hp",
                "30",
                "25",
                "--min-rounds",
                "2",
                "--revive-coin",
                "40",
            ]
        )
        self.assertEqual(args.boss_hp, [30, 25])
        self.assertEqual(args.min_rounds, 2)
        self.assertEqual(args.revive_coin, 40)


    def test_boss_revive_estimates_round_limit_cost(self) -> None:
        skills = (Skill("Attack", damage=5, cooldown=0), Skill("Power", damage=10, cooldown=2))
        plan = optimize_boss_fight(20, skills, revive_coin=50)
        summary = estimate_boss_revives(plan, round_limit=2, coins=100)
        self.assertTrue(summary["survived"])
        self.assertEqual(summary["total_rounds"], 3)
        self.assertEqual(summary["round_limit"], 2)
        self.assertEqual(summary["required_revives"], 1)
        self.assertEqual(summary["spent_coins"], 50)
        self.assertEqual(summary["remaining_coins"], 50)


    def test_main_parser_supports_three_task_aliases(self) -> None:
        task1 = build_main_parser().parse_args(["任务一", "--size", "9"])
        task2 = build_main_parser().parse_args(["任务二", "--size", "9"])
        task3 = build_main_parser().parse_args(["任务三", "--boss-hp", "30"])
        self.assertEqual(task1.size, 9)
        self.assertEqual(task2.size, 9)
        self.assertEqual(task3.boss_hp, [30])


if __name__ == "__main__":
    unittest.main()

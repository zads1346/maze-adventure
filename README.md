# Maze Adventure Course Project

Algorithm-driven maze adventure: generate mazes, collect resources, and fight bosses
with branch-and-bound optimal strategies.

## Quick Start

```bash
pip install -e .
```

## Task 1: Maze Generation (4 Algorithms)

### Compare All

```bash
python3 main.py maze --size 15 --method all --seed 7
```

### Individual Methods

```bash
python3 main.py maze --size 15 --method division --seed 7           # Divide & Conquer
python3 main.py maze --size 15 --method mst --seed 7                # MST / Prim
python3 main.py maze --size 15 --method dfs --seed 7                # Backtracking / DFS
python3 main.py maze --size 15 --method bfs_branch_bound --seed 7   # Branch & Bound / BFS
```

| Algorithm | Flag | Style |
|-----------|------|-------|
| Divide & Conquer | `division` | Recursive room carving, grid-like |
| MST / Prim | `mst` | Random Prim, even branches |
| Backtracking / DFS | `dfs` | Long corridors, deep dead ends |
| Branch & Bound / BFS | `bfs_branch_bound` | Goal-oriented with heuristic |

### Export as JSON

```bash
# Print JSON to stdout
python3 main.py maze --size 15 --method dfs --seed 7 --json

# Write to file (with custom boss/skills/rounds)
python3 main.py maze --size 15 --method dfs --seed 7 \
  --boss-hp 11 13 9 15 \
  --min-rounds 20 \
  --coin-consumption 5 \
  --skill [8,4] --skill [2,0] --skill [4,2] --skill [6,3] \
  --json-file output.json
```

`--skill` accepts three formats: `[8,4]`, `8:4`, or `大招:10:2`.

## Task 2: Resource Path Planning (DP)

```bash
# Auto-generated maze
python3 main.py resource --size 15 --method dfs --seed 7 --show-walk

# From JSON file
python3 main.py resource --maze-file output.json --show-walk
```

Finds the optimal path from S to E that maximizes net value:
- `G` (coin) = +50 each
- `T` (trap) = -30 each

## Task 3: Boss Fight Optimization (Branch & Bound)

```bash
# Manual parameters
python3 main.py boss --boss-hp 11 13 9 15 --min-rounds 20 --revive-coin 5 \
  --skill [5,0] --skill [10,2]

# Auto from JSON (inherits all parameters + auto-calculates coins)
python3 main.py boss --maze-file output.json
```

The optimizer **auto-selects the optimal boss target each round** (not fixed order).
Uses branch & bound with admissible heuristic to guarantee minimum rounds.

### Coin System

| Source | Formula |
|--------|---------|
| Player initial coins | `explore.coins` = G_count × 50 + T_count × (-30) |
| Revive cost | `revives × CoinConsumption` |
| Revive count | `(total_rounds - 1) // minRouds` |
| Survived | `coins >= spent_coins` |

Coins are auto-calculated from the maze's optimal resource path when using `--maze-file`.

## Visualization (pygame)

### Maze Generation Process

```bash
# All 4 algorithms side by side
python3 visualize_pygame.py --mode generate --method all --size 15 --seed 7

# Single algorithm
python3 visualize_pygame.py --mode generate --method mst --size 15 --seed 7
python3 visualize_pygame.py --mode generate --method dfs --size 15 --seed 7
python3 visualize_pygame.py --mode generate --method division --size 15 --seed 7
python3 visualize_pygame.py --mode generate --method bfs_branch_bound --size 15 --seed 7
```

### AI Exploration

```bash
python3 visualize_pygame.py --mode explore --method mst --size 15 --seed 7
python3 visualize_pygame.py --mode explore --method dfs --size 15 --seed 7
```

### Resource Path

```bash
python3 visualize_pygame.py --size 15 --method dfs --mode resource
```

### Boss Fight

```bash
python3 visualize_boss.py --boss-hp 30 --min-rounds 20 --revive-coin 5 --coins 100
python3 visualize_boss.py --boss-hp 11 13 9 15 --min-rounds 20 --revive-coin 5 --coins 370
```

## Tests

```bash
# Unit tests (12 cases)
python3 -m unittest discover -s tests -v

# Boss fight + coin economics (8 cases)
python3 tests/test_boss_coins.py

# Full pipeline: maze -> resources -> boss -> settlement
python3 tests/test_full_pipeline.py
```

## API

```python
from maze_adventure import (
    Skill,
    best_resource_path,
    explore_maze,
    generate_maze,
    is_perfect_maze,
    optimize_boss_fight,
    render_grid,
)

# Generate maze
maze = generate_maze(15, method="dfs", seed=7).grid
print(render_grid(maze))
print(is_perfect_maze(maze))  # True

# Resource path DP
plan = best_resource_path(maze)
print(plan.max_value, plan.path)

# Boss fight (auto-selects optimal target each round)
boss = optimize_boss_fight([11, 13, 9, 15],
    skills=[Skill("A", 5, 0), Skill("P", 10, 2)])
print(boss.min_rounds)  # 8

# Full pipeline: explore -> coins -> boss -> revive
result = explore_maze(maze, boss_hp=[30])
print(result.coins, result.steps, result.boss_plan.min_rounds)
```

## Cell Symbols

| Symbol | Value | Meaning |
|--------|-------|---------|
| `#` | - | Wall |
| `S` | - | Start |
| `E` | - | End |
| `B` | - | Boss encounter |
| `G` | +50 | Coin |
| `T` | -30 | Trap |
| `.` | - | Road |

## Data Flow

```
Maze(G,T) --DP--> Optimal Path --walk--> collect coins --coins--> Boss Fight --revive--> Settlement

  coins = G x 50 + T x (-30)               rounds <= minRouds? 0 cost
                                            rounds > minRouds? revive cost
```

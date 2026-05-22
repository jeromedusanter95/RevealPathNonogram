"""Random self-avoiding walk from S to G on a grid.

The walk biases moves to keep the path varied: early moves prefer to wander
away from G, later moves prefer to approach. A cheap reachability check
rejects moves that would cut the path off from G.
"""

from __future__ import annotations

import random
from collections import deque

from rpn.model import Cell, Direction


def _manhattan(a: Cell, b: Cell) -> int:
    return abs(a.col - b.col) + abs(a.row - b.row)


def _can_still_reach(start: Cell, goal: Cell, visited: set[Cell], width: int, height: int) -> bool:
    """BFS from `start`, avoiding `visited`, to determine if `goal` is still reachable."""
    if start == goal:
        return True
    queue: deque[Cell] = deque([start])
    seen: set[Cell] = {start} | visited
    while queue:
        current = queue.popleft()
        for direction in Direction:
            dc, dr = direction.delta
            n = Cell(current.col + dc, current.row + dr)
            if not (0 <= n.col < width and 0 <= n.row < height):
                continue
            if n in seen:
                continue
            if n == goal:
                return True
            seen.add(n)
            queue.append(n)
    return False


def random_path(
    width: int,
    height: int,
    start: Cell,
    goal: Cell,
    target_length: int,
    rng: random.Random,
    max_restarts: int = 200,
) -> list[Cell] | None:
    """Random self-avoiding walk from `start` to `goal` aiming for ~target_length cells.

    Returns the path as a list of cells, or None if no path was found within
    `max_restarts` attempts.

    Strategy: at each step, pick the next cell from unvisited orthogonal
    neighbors that still allow reaching `goal`. Weights bias toward moves
    away from `goal` while path length is below target, toward `goal` once
    we're close enough.
    """
    for _ in range(max_restarts):
        path = _walk_once(width, height, start, goal, target_length, rng)
        if path is not None:
            return path
    return None


def _walk_once(
    width: int,
    height: int,
    start: Cell,
    goal: Cell,
    target_length: int,
    rng: random.Random,
) -> list[Cell] | None:
    path: list[Cell] = [start]
    visited: set[Cell] = {start}

    # Bias schedule: when path length is below target, prefer moves that
    # increase distance from goal. After the target is reached, prefer moves
    # that decrease distance.
    while path[-1] != goal:
        current = path[-1]
        candidates: list[Cell] = []
        for direction in Direction:
            dc, dr = direction.delta
            n = Cell(current.col + dc, current.row + dr)
            if not (0 <= n.col < width and 0 <= n.row < height):
                continue
            if n in visited:
                continue
            if n != goal and not _can_still_reach(n, goal, visited, width, height):
                continue
            candidates.append(n)

        if not candidates:
            return None

        if goal in candidates and len(path) >= target_length:
            # Reached or exceeded target length and the goal is one step away. Take it.
            path.append(goal)
            visited.add(goal)
            break

        weights = [
            _weight(c, goal, len(path), target_length) for c in candidates
        ]
        next_cell = rng.choices(candidates, weights=weights, k=1)[0]
        path.append(next_cell)
        visited.add(next_cell)

        if len(path) > target_length * 4:
            return None  # runaway walk

    return path


def _weight(candidate: Cell, goal: Cell, current_length: int, target_length: int) -> float:
    """Weight a candidate move. Larger weight = more likely to be picked.

    Below target length: prefer moves that stay far from goal (explore).
    At/above target: prefer moves that approach goal (close the path).
    """
    distance = _manhattan(candidate, goal)
    if current_length < target_length:
        return float(distance + 1)
    return 1.0 / float(distance + 1)

"""Puzzle generator.

Pipeline (from `design/02_generator.md`):
  PLACE → DRAW → DERIVE → HINT (dig holes) → VALIDATE → MEASURE → ACCEPT
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from rpn.deduction import solve
from rpn.metrics import perceived_score, player_decision_points
from rpn.model import Cell, Direction, Puzzle, Segment
from rpn.path_walk import random_path
from rpn.uniqueness import UniquenessStatus, check_uniqueness


@dataclass(frozen=True, slots=True)
class DifficultySignal:
    """Difficulty fields persisted with each generated puzzle.

    See rpn.metrics for the score definition. Only player-experience metrics
    are kept here; obsolete solver-perspective scores (clue_ambiguity,
    tier_score, etc.) were removed once playtesting confirmed the
    perceived-score model.
    """
    hint_count: int
    path_length: int
    grid_size: tuple[int, int]
    # n_decisions = count of moves along the solution path where >1 local-rule
    # -passing neighbor exists at the tip. Cell where the player has to choose.
    n_decisions: int
    decision_ratio: float
    # total_decision_weight = sum over decisions of
    #   (n_candidates - 1) * (1 + max_trap_depth),
    # weighting forks by both branching width and how deep the wrong choices
    # go before dead-ending.
    total_decision_weight: int
    # Per-decision detail: tuples of (step, n_candidates, max_trap_depth,
    # weight). step is 1-indexed; the tip cell where the player decides is
    # solution_path[step - 1]. Used by the playtest viewer to highlight
    # decision cells for debugging / score visualization.
    decisions: tuple[tuple[int, int, int, int], ...]
    # Primary ranking key: size + path length + weighted decisions.
    # See rpn.metrics.perceived_score.
    perceived_score: float


@dataclass(frozen=True, slots=True)
class GeneratedPuzzle:
    puzzle: Puzzle
    solution_path: tuple[Cell, ...]
    difficulty: DifficultySignal
    seed: int


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    width: int
    height: int
    target_density: float = 0.55
    min_sg_distance: int | None = None
    max_attempts: int = 100
    # Reject any candidate whose drawn path has fewer cells than this.
    # If None, defaults to max(width, height) so a 5x5 puzzle never has a
    # path shorter than 5 cells.
    min_path_length: int | None = None
    # Target hint count. Two ways to specify:
    #   absolute: an int. The generator lands at exactly that many hints.
    #   fraction: a float in (0, 1]. The generator lands at round(fraction * path_length).
    # If None: leave whatever dig-holes produced (no top-up, hardest possible).
    # If dig-holes leaves more hints than the target, the puzzle is discarded
    # (it needed too many hints to be deduction-solvable).
    target_hints: int | float | None = None
    # Optional: reject any candidate whose row or column clues fall outside
    # this allowed set. Used to forbid trivial clue values (0, 1, line_length)
    # for the hardest difficulty bands.
    allowed_clue_values: frozenset[int] | None = None
    # If True, reject any candidate where the count of S+G cells in some row
    # or column equals that line's clue. Such lines are auto-completed (all
    # remaining cells are forced EMPTY) by trivial deduction from S/G alone,
    # which removes an entire row/column of decision-making for the player.
    # Used by the divinity band.
    forbid_endpoint_auto_lines: bool = False
    # If True, S and G must be placed in different rows AND different columns.
    # Used in combination with `forbid_endpoint_auto_lines` to make divinity
    # feasible: forcing S/G off shared lines avoids the structural collision
    # where S+G in a same-line clue=2 row dominates the candidate space.
    require_diagonal_endpoints: bool = False


def generate(config: GeneratorConfig, seed: int) -> GeneratedPuzzle | None:
    """Generate one puzzle. Returns None if no valid puzzle found in `max_attempts`."""
    rng = random.Random(seed)
    for attempt in range(config.max_attempts):
        result = _try_generate(config, rng)
        if result is not None:
            return GeneratedPuzzle(
                puzzle=result[0],
                solution_path=result[1],
                difficulty=result[2],
                seed=seed,
            )
    return None


def _try_generate(
    config: GeneratorConfig, rng: random.Random
) -> tuple[Puzzle, tuple[Cell, ...], DifficultySignal] | None:
    # 1. PLACE: pick S and G.
    sg = _place_endpoints(config, rng)
    if sg is None:
        return None
    start, goal = sg

    # 2. DRAW: random self-avoiding path.
    target_length = max(2, int(config.width * config.height * config.target_density))
    path = random_path(
        config.width, config.height, start, goal, target_length, rng
    )
    if path is None or len(path) < 2:
        return None

    # Reject paths shorter than the configured minimum (default: max(W, H)).
    min_length = config.min_path_length
    if min_length is None:
        min_length = max(config.width, config.height)
    if len(path) < min_length:
        return None

    # 3. DERIVE: row/column counts.
    row_counts, col_counts = _derive_counts(path, config.width, config.height)

    # Global rule: no row or column may have clue == 0. A zero clue tells the
    # player the entire line is empty in one trivial T2 step, which both
    # shrinks the perceived difficulty and removes a chunk of the player's
    # work for free. clue == line_length is *not* banned here because it does
    # not imply the path runs straight through the line; the path can still
    # zigzag through all cells.
    if any(c == 0 for c in row_counts) or any(c == 0 for c in col_counts):
        return None

    # Optional clue-value filter (used by hardest difficulty bands to ban
    # trivial values like 0, 1, line_length).
    if config.allowed_clue_values is not None:
        allowed = config.allowed_clue_values
        if any(c not in allowed for c in row_counts) or any(
            c not in allowed for c in col_counts
        ):
            return None

    # Optional endpoint-auto-line filter: reject if some row or column has
    # a clue exactly equal to the number of endpoint cells (S, G) it
    # contains. Such lines auto-complete by trivial deduction (the rest is
    # forced EMPTY), which gives the player a free hint.
    if config.forbid_endpoint_auto_lines:
        for r in range(config.height):
            endpoint_count = (1 if start.row == r else 0) + (1 if goal.row == r else 0)
            if endpoint_count > 0 and row_counts[r] == endpoint_count:
                return None
        for c in range(config.width):
            endpoint_count = (1 if start.col == c else 0) + (1 if goal.col == c else 0)
            if endpoint_count > 0 and col_counts[c] == endpoint_count:
                return None

    # 4. HINT: dig holes until barely solvable.
    full_hints = full_hint_set(path)
    base_puzzle_no_hints = Puzzle(
        width=config.width,
        height=config.height,
        start=start,
        goal=goal,
        row_counts=row_counts,
        col_counts=col_counts,
        hints=tuple(full_hints),
    )
    # Sanity check: with all hints the puzzle must be solvable; if not, something
    # very wrong (e.g. our hint derivation disagrees with the path). Skip.
    full_solve = solve(base_puzzle_no_hints)
    if not full_solve.solved or full_solve.path != tuple(path):
        return None

    minimal_hints = _dig_holes(full_hints, base_puzzle_no_hints, rng)

    target_n = _resolve_target_hints(config.target_hints, len(path))
    if target_n is not None:
        if len(minimal_hints) > target_n:
            # Puzzle is too hard for this difficulty target; discard.
            return None
        minimal_hints = _top_up_to(minimal_hints, full_hints, target_n, rng)

    final_puzzle = Puzzle(
        width=config.width,
        height=config.height,
        start=start,
        goal=goal,
        row_counts=row_counts,
        col_counts=col_counts,
        hints=tuple(minimal_hints),
    )

    # 5. VALIDATE: uniqueness check.
    uniq = check_uniqueness(final_puzzle)
    if uniq.status != UniquenessStatus.UNIQUE:
        return None

    # 6. MEASURE: difficulty from the local-rules decision-point walk.
    # Cost: O(path_length * trap_branching ^ TRAP_DEPTH_CAP) per puzzle.
    dp = player_decision_points(final_puzzle, tuple(path))
    difficulty = DifficultySignal(
        hint_count=len(minimal_hints),
        path_length=len(path),
        grid_size=(config.width, config.height),
        n_decisions=dp.n_decisions,
        decision_ratio=dp.decision_ratio,
        total_decision_weight=dp.total_decision_weight,
        decisions=tuple(
            (d.step, d.n_candidates, d.max_trap_depth, d.weight)
            for d in dp.decisions
        ),
        perceived_score=perceived_score(
            (config.width, config.height), len(path), dp.total_decision_weight
        ),
    )

    return final_puzzle, tuple(path), difficulty


def _place_endpoints(
    config: GeneratorConfig, rng: random.Random
) -> tuple[Cell, Cell] | None:
    width, height = config.width, config.height
    min_distance = config.min_sg_distance
    if min_distance is None:
        min_distance = max(width, height) // 2

    all_cells = [Cell(c, r) for r in range(height) for c in range(width)]
    if len(all_cells) < 2:
        return None

    for _ in range(200):
        start = rng.choice(all_cells)
        goal = rng.choice(all_cells)
        if start == goal:
            continue
        if abs(start.col - goal.col) + abs(start.row - goal.row) < min_distance:
            continue
        if config.require_diagonal_endpoints and (
            start.row == goal.row or start.col == goal.col
        ):
            continue
        return start, goal
    return None


def _derive_counts(
    path: list[Cell], width: int, height: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    row_counts = [0] * height
    col_counts = [0] * width
    for cell in path:
        row_counts[cell.row] += 1
        col_counts[cell.col] += 1
    return tuple(row_counts), tuple(col_counts)


def full_hint_set(path: list[Cell]) -> list[Segment]:
    """For each cell on the path, derive its segment from its path neighbors.

    The first cell (S) and last cell (G) get a 1-sided segment pointing to
    the single adjacent path cell. Interior cells get a 2-sided segment
    showing both neighbors.
    """
    hints: list[Segment] = []
    for i, cell in enumerate(path):
        sides: list[Direction] = []
        if i > 0:
            sides.append(_direction(cell, path[i - 1]))
        if i < len(path) - 1:
            sides.append(_direction(cell, path[i + 1]))
        hints.append(Segment(cell=cell, sides=frozenset(sides)))
    return hints


def _direction(from_cell: Cell, to_cell: Cell) -> Direction:
    dc = to_cell.col - from_cell.col
    dr = to_cell.row - from_cell.row
    if dc == 1 and dr == 0:
        return Direction.E
    if dc == -1 and dr == 0:
        return Direction.W
    if dc == 0 and dr == 1:
        return Direction.S
    if dc == 0 and dr == -1:
        return Direction.N
    raise ValueError(f"non-adjacent cells: {from_cell} -> {to_cell}")


def _dig_holes(
    full_hints: list[Segment], puzzle: Puzzle, rng: random.Random
) -> list[Segment]:
    """Remove hints one at a time, keeping only those whose absence breaks deduction."""
    order = list(full_hints)
    rng.shuffle(order)
    current = list(full_hints)
    for hint in order:
        candidate = [h for h in current if h is not hint]
        trial_puzzle = Puzzle(
            width=puzzle.width,
            height=puzzle.height,
            start=puzzle.start,
            goal=puzzle.goal,
            row_counts=puzzle.row_counts,
            col_counts=puzzle.col_counts,
            hints=tuple(candidate),
        )
        result = solve(trial_puzzle)
        if result.solved:
            current = candidate
    return current


def _resolve_target_hints(
    target: int | float | None, path_length: int
) -> int | None:
    """Translate the config knob (int absolute count, float fraction, or None) to an int."""
    if target is None:
        return None
    if isinstance(target, int):
        return target
    return int(round(target * path_length))


def _top_up_to(
    minimal: list[Segment],
    full: list[Segment],
    target: int,
    rng: random.Random,
) -> list[Segment]:
    """Add back hints from `full` until len(result) == target.

    Caller has already verified `len(minimal) <= target`. If minimal already
    has enough, returned unchanged.
    """
    if len(minimal) >= target:
        return minimal
    minimal_cells = {h.cell for h in minimal}
    extras = [h for h in full if h.cell not in minimal_cells]
    rng.shuffle(extras)
    needed = target - len(minimal)
    return minimal + extras[:needed]

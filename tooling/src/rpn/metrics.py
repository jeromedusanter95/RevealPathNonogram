"""Player-experience metrics.

A player traces S→G one cell at a time. At each step they either see an
obviously-forced next move or they face a real choice. The metric here
counts the second kind, using rules a human can apply at the table:

  At the tip of the player's drawn path, consider each in-bounds neighbor.
  A neighbor is a "live candidate" iff:
    1. It's not already on the drawn path.
    2. Adding it doesn't push row_counts[neighbor.row] over its clue.
    3. Adding it doesn't push col_counts[neighbor.col] over its clue.
    4. If the neighbor has a visible hint, the hint's side-set includes
       the direction back to the tip (the hint commits the cell's
       connections; entering from a non-hinted side contradicts the hint).
    5. The neighbor isn't a non-tip endpoint (you can't walk through G
       except as your final move).
  Additionally, if the *tip* has a visible hint, the next move is fully
  determined by it (the tip's two sides are committed; one was the entry,
  the other is the exit). In that case exactly one neighbor is forced and
  we don't even need rule 1-5.

  If exactly one candidate survives: obligated move.
  If two or more survive: decision point.
  Zero survivors should be impossible on a valid path (the puzzle has a
  solution by construction); if it ever happens we count it as a decision.

This is intentionally NOT a solver-deduction check. Earlier attempts used
the full deduction solver and over-counted forced moves: the solver would
chain 5 steps ahead and prove a move "forced" even though the player at
the table sees three locally-legal choices and has to commit blindly.
"""

from __future__ import annotations

from dataclasses import dataclass

from rpn.model import Cell, Direction, Puzzle, Segment


_DIR_FROM_DELTA: dict[tuple[int, int], Direction] = {
    (0, -1): Direction.N,
    (1, 0): Direction.E,
    (0, 1): Direction.S,
    (-1, 0): Direction.W,
}


@dataclass(frozen=True, slots=True)
class Decision:
    """Per-decision metadata.

    `step` is 1-indexed move number along the solution path.
    `n_candidates` is the number of locally-legal next cells at the tip.
    `max_trap_depth` is the deepest dead-end reachable from a wrong choice
    (capped at TRAP_DEPTH_CAP). A wrong choice that dies immediately has
    trap_depth = 1; the player loses one move.
    `weight = (n_candidates - 1) * (1 + max_trap_depth)`.
    """
    step: int
    n_candidates: int
    max_trap_depth: int
    weight: int


@dataclass(frozen=True, slots=True)
class DecisionPoints:
    n_moves: int
    n_forced: int
    n_decisions: int
    decision_step_indices: tuple[int, ...]
    decisions: tuple[Decision, ...]
    total_decision_weight: int

    @property
    def decision_ratio(self) -> float:
        if self.n_moves == 0:
            return 0.0
        return self.n_decisions / self.n_moves


# Cap on how deep we explore wrong branches when measuring trap depth. A
# wrong choice that goes deeper than this is treated as "deep enough"; the
# player would have given up and undone before reaching the dead-end anyway.
# 5 is calibrated against the user's intuition that "5+ deep traps feel
# meaningfully harder than 1-2 deep traps."
TRAP_DEPTH_CAP = 5


def player_decision_points(
    puzzle: Puzzle, solution_path: tuple[Cell, ...]
) -> DecisionPoints:
    """Walk the solution path, classifying each move as forced or decision.

    For each decision point we also compute:
      - n_candidates: how many neighbors survive the local-rules check at
        the tip.
      - max_trap_depth: among the *wrong* candidates (everything except the
        correct next cell), what's the deepest dead-end the player would
        hit if they committed to that branch and kept exploring with local
        rules? Capped at TRAP_DEPTH_CAP.
      - weight: (n_candidates - 1) * (1 + max_trap_depth). Captures both
        the breadth of the fork and the depth of the punishment for going
        the wrong way.
    """
    n = len(solution_path)
    if n < 2:
        return DecisionPoints(
            n_moves=0, n_forced=0, n_decisions=0,
            decision_step_indices=(), decisions=(), total_decision_weight=0,
        )

    hint_by_cell: dict[Cell, frozenset[Direction]] = {
        h.cell: h.sides for h in puzzle.hints
    }

    row_used = [0] * puzzle.height
    col_used = [0] * puzzle.width
    drawn: set[Cell] = set()
    row_used[solution_path[0].row] += 1
    col_used[solution_path[0].col] += 1
    drawn.add(solution_path[0])

    forced_flags: list[bool] = []
    decision_indices: list[int] = []
    decisions: list[Decision] = []

    for k in range(n - 1):
        tip = solution_path[k]
        # Hint at the tip determines exit direction; treat as forced.
        if tip in hint_by_cell:
            forced_flags.append(True)
            drawn.add(solution_path[k + 1])
            row_used[solution_path[k + 1].row] += 1
            col_used[solution_path[k + 1].col] += 1
            continue

        # If any non-drawn neighbor of the tip is a hint cell whose hint
        # commits the edge BACK to the tip, that edge is committed-USED by
        # the visible hint. The player has no real choice: either the next
        # move IS that neighbor, or (if multiple neighbors commit back) the
        # next move is one of them and the others are also committed for
        # later. Either way, no decision-making happens at this step.
        if _has_hint_pulled_neighbor(puzzle, tip, drawn, hint_by_cell):
            forced_flags.append(True)
            nxt = solution_path[k + 1]
            drawn.add(nxt)
            row_used[nxt.row] += 1
            col_used[nxt.col] += 1
            continue

        is_last = (k + 1 == n - 1)
        candidates = _surviving_candidates(
            puzzle, tip, drawn, row_used, col_used, hint_by_cell, is_last
        )
        forced = len(candidates) == 1
        forced_flags.append(forced)
        if not forced:
            decision_indices.append(k + 1)
            correct = solution_path[k + 1]
            wrong = [c for c in candidates if c != correct]
            max_depth = 0
            for branch in wrong:
                depth = _explore_trap(
                    puzzle, branch, drawn, row_used, col_used,
                    hint_by_cell, depth_budget=TRAP_DEPTH_CAP,
                )
                if depth > max_depth:
                    max_depth = depth
            n_c = len(candidates)
            weight = (n_c - 1) * (1 + max_depth)
            decisions.append(
                Decision(
                    step=k + 1,
                    n_candidates=n_c,
                    max_trap_depth=max_depth,
                    weight=weight,
                )
            )

        nxt = solution_path[k + 1]
        drawn.add(nxt)
        row_used[nxt.row] += 1
        col_used[nxt.col] += 1

    return DecisionPoints(
        n_moves=n - 1,
        n_forced=sum(forced_flags),
        n_decisions=len(decision_indices),
        decision_step_indices=tuple(decision_indices),
        decisions=tuple(decisions),
        total_decision_weight=sum(d.weight for d in decisions),
    )


def _surviving_candidates(
    puzzle: Puzzle,
    tip: Cell,
    drawn: set[Cell],
    row_used: list[int],
    col_used: list[int],
    hint_by_cell: dict[Cell, frozenset[Direction]],
    is_last_move: bool,
) -> list[Cell]:
    out: list[Cell] = []
    for direction, neighbor in puzzle.neighbors(tip):
        if _passes_local_rules(
            puzzle, tip, direction, neighbor, drawn,
            row_used, col_used, hint_by_cell, is_last_move,
        ):
            out.append(neighbor)
    return out


def _explore_trap(
    puzzle: Puzzle,
    cell: Cell,
    drawn: set[Cell],
    row_used: list[int],
    col_used: list[int],
    hint_by_cell: dict[Cell, frozenset[Direction]],
    depth_budget: int,
) -> int:
    """Simulate the player committing to `cell` and exploring greedily.

    Returns the number of moves the player makes after the wrong choice
    before hitting a dead end (no surviving neighbors). 1 means the wrong
    cell itself was the dead end (no moves possible after committing).

    To keep this tractable we DFS through surviving branches up to
    depth_budget, returning the deepest dead-end found. If a branch reaches
    the goal G or runs out of depth budget without dying, we treat it as
    "deep" by returning depth_budget. This is conservative: it overweights
    branches that look survivable but would actually require more lookahead
    to confirm wrong, which is in fact harder for the player.
    """
    # Commit `cell` and recurse. We mutate row_used/col_used/drawn in place
    # and unwind at the end (cheaper than copying).
    if cell in drawn:
        return 0
    if row_used[cell.row] + 1 > puzzle.row_counts[cell.row]:
        return 0
    if col_used[cell.col] + 1 > puzzle.col_counts[cell.col]:
        return 0

    drawn.add(cell)
    row_used[cell.row] += 1
    col_used[cell.col] += 1
    try:
        # If we've reached G, treat as deep (player completed the wrong
        # branch successfully? That shouldn't happen on a unique-solution
        # puzzle, but treat as full depth defensively).
        if cell == puzzle.goal:
            return depth_budget
        if depth_budget <= 0:
            return TRAP_DEPTH_CAP

        # Find neighbors of `cell` that survive local rules.
        is_last = False  # in-trap, we never claim "this is the last move"
        next_candidates = _surviving_candidates(
            puzzle, cell, drawn, row_used, col_used, hint_by_cell, is_last
        )
        if not next_candidates:
            return 1  # dead end one move into the wrong branch
        best = 0
        for nb in next_candidates:
            sub = _explore_trap(
                puzzle, nb, drawn, row_used, col_used,
                hint_by_cell, depth_budget - 1,
            )
            if sub + 1 > best:
                best = sub + 1
            if best >= TRAP_DEPTH_CAP:
                return TRAP_DEPTH_CAP
        return best
    finally:
        drawn.remove(cell)
        row_used[cell.row] -= 1
        col_used[cell.col] -= 1


def _has_hint_pulled_neighbor(
    puzzle: Puzzle,
    tip: Cell,
    drawn: set[Cell],
    hint_by_cell: dict[Cell, frozenset[Direction]],
) -> bool:
    """True iff any non-drawn neighbor of `tip` has a hint that commits the
    edge back to `tip`.

    Such a neighbor pulls the path: the visible hint commits an edge between
    the neighbor and the tip, so the player must use that edge. There's no
    decision-making at the tip in this case.

    Drawn cells are excluded because their edge to the tip is already known
    (the player has either drawn or not drawn it).
    """
    for direction, neighbor in puzzle.neighbors(tip):
        if neighbor in drawn:
            continue
        nb_hint = hint_by_cell.get(neighbor)
        if nb_hint is None:
            continue
        # Direction from neighbor BACK to tip:
        back_to_tip = direction.opposite
        if back_to_tip in nb_hint:
            return True
    return False


def _passes_local_rules(
    puzzle: Puzzle,
    tip: Cell,
    direction: Direction,
    neighbor: Cell,
    drawn: set[Cell],
    row_used: list[int],
    col_used: list[int],
    hint_by_cell: dict[Cell, frozenset[Direction]],
    is_last_move: bool,
) -> bool:
    # Rule 1: not already drawn.
    if neighbor in drawn:
        return False
    # Rule 2/3: clue capacities.
    if row_used[neighbor.row] + 1 > puzzle.row_counts[neighbor.row]:
        return False
    if col_used[neighbor.col] + 1 > puzzle.col_counts[neighbor.col]:
        return False
    # Rule 4: hint at neighbor must accept the entry direction.
    neighbor_hint = hint_by_cell.get(neighbor)
    if neighbor_hint is not None:
        # Direction *from neighbor back to tip* is opposite of `direction`.
        entry_side = direction.opposite
        if entry_side not in neighbor_hint:
            return False
    # Rule 5: G can only be entered on the final move.
    if neighbor == puzzle.goal and not is_last_move:
        return False
    return True


# Calibration constants for the perceived-difficulty score.
# Three principles:
#   1. Size sets the band ceiling. A 10x10 always feels heavier than a 5x5
#      regardless of decision content, because reading 10-cell rows is fatiguing.
#   2. Weighted decisions dominate within a fixed size. A decision's weight
#      is (n_candidates - 1) * (1 + max_trap_depth), so a 2-way fork with a
#      1-deep trap counts as 2, a 3-way fork with a 5-deep trap counts as 12.
#   3. Path length is a small secondary term within a size.
SIZE_WEIGHTS: dict[tuple[int, int], float] = {
    (5, 5): 0.0,
    (7, 7): 1000.0,
    (10, 10): 2000.0,
}
PATH_LENGTH_COEFF = 5.0
# Weighted-decisions are ~5x more granular than the old binary count (a
# typical decision has weight 2-6), so the per-unit coefficient is smaller.
DECISION_WEIGHT_COEFF = 15.0


def perceived_score(
    grid_size: tuple[int, int], path_length: int, total_decision_weight: int
) -> float:
    """Combined size + path-length + weighted-decision score.

    Out-of-table sizes fall back to a width-based interpolation that keeps
    the band ceiling monotonic in `max(W, H)`.
    """
    size_weight = SIZE_WEIGHTS.get(grid_size)
    if size_weight is None:
        size_weight = max(0.0, (max(grid_size) - 5) * 500.0)
    return (
        size_weight
        + PATH_LENGTH_COEFF * float(path_length)
        + DECISION_WEIGHT_COEFF * float(total_decision_weight)
    )

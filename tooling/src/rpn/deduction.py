"""Deduction solver entry point.

Applies tactics in a fixed order, iterating until a full sweep produces no
new facts. Returns a `DeductionResult` summarizing what was achieved.

Tactic tiers (see HANDOFF.md Phase 2):
  Tier 1: T1 (saturation), T2 (trivial extremes), T3 (capacity), T4-T8 (local degree).
  Tier 2: T9 (premature cycle), T10 (isolated island), T12 (cross-line saturation).
  Tier 3: reserved (T13 deferred).
  Tier 4: T14 (1-step lookahead / bounded contradiction).
  T11 (hint init) is the puzzle-setup pass, not a tactic the player exercises.

T14 is gated: it only fires after T1-T13 have reached a fixed point with the
puzzle still unsolved. This matches Roucairol & Cazenave 2024's treatment of
lookahead as a tier-distinct event whose count, not its mere occurrence,
defines difficulty within the tier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rpn.model import Cell, Puzzle
from rpn.state import Inconsistent, SolverState, apply_hint_init
from rpn.tactics import TACTICS


# Maps each tactic tag (as recorded on Step.tactic) to its tier number. T11
# and any "init:*" tags are excluded from tier accounting (the hint placement
# is a pre-pass, not a player-facing tactic).
TACTIC_TIERS: dict[str, int] = {
    # Tier 1: single-line saturation and local degree tactics.
    "T1r": 1, "T1c": 1,
    "T2": 1,
    "T3r": 1, "T3c": 1,
    "T4": 1, "T5": 1, "T6": 1, "T7": 1, "T8": 1,
    # Tier 2: path-topology and cross-line tactics.
    "T9": 2, "T10": 2,
    "T12": 2,
    # Tier 3 reserved (T13 deferred per Phase 1 plan).
    # Tier 4: 1-step lookahead / bounded contradiction.
    "T14": 4,
}

# Tags excluded from all tier-based score components. Hint init is bookkeeping,
# not a tactic; the probe tag never reaches DeductionResult because probe
# steps are rolled back, but it's listed for safety.
TIER_EXCLUDED_TAGS: frozenset[str] = frozenset({"T11", "init:S", "init:G", "T14-probe"})


@dataclass(frozen=True, slots=True)
class DeductionResult:
    solved: bool
    inconsistent: bool
    reason: str
    state: SolverState
    by_tactic: dict[str, int]
    total_steps: int
    path: tuple[Cell, ...] | None = None

    @property
    def hint_init_steps(self) -> int:
        return sum(
            count for tactic, count in self.by_tactic.items()
            if tactic.startswith(("init:", "T11"))
        )

    @property
    def line_tactic_steps(self) -> int:
        """Single-line saturation + trivial extremes (tier 1 line tactics)."""
        return sum(
            self.by_tactic.get(t, 0) for t in ("T1r", "T1c", "T2", "T3r", "T3c")
        )

    @property
    def path_tactic_steps(self) -> int:
        return sum(
            self.by_tactic.get(t, 0)
            for t in ("T4", "T5", "T6", "T7", "T8", "T9", "T10")
        )

    @property
    def max_tier(self) -> int:
        """Highest tier of any tactic that fired (T11/init excluded).

        Returns 1 if only tier-1 tactics fired (or only excluded tags fired);
        the empty-puzzle case is unreachable because every solvable puzzle
        triggers at least the endpoint placements during hint init, but the
        tier-1 floor models 'easiest possible'.
        """
        highest = 1
        for tactic, count in self.by_tactic.items():
            if count <= 0 or tactic in TIER_EXCLUDED_TAGS:
                continue
            tier = TACTIC_TIERS.get(tactic)
            if tier is None:
                continue
            if tier > highest:
                highest = tier
        return highest

    @property
    def tier_count(self) -> int:
        """Number of firings of tactics at the max tier."""
        target = self.max_tier
        total = 0
        for tactic, count in self.by_tactic.items():
            if tactic in TIER_EXCLUDED_TAGS:
                continue
            if TACTIC_TIERS.get(tactic) == target:
                total += count
        return total

    @property
    def lower_tier_total(self) -> int:
        """Total firings strictly below max_tier (T11/init excluded)."""
        target = self.max_tier
        total = 0
        for tactic, count in self.by_tactic.items():
            if tactic in TIER_EXCLUDED_TAGS:
                continue
            tier = TACTIC_TIERS.get(tactic)
            if tier is None or tier >= target:
                continue
            total += count
        return total

    @property
    def tier_score(self) -> float:
        """Combined tier-based difficulty score (HANDOFF Phase 2).

        score = max_tier * 1000 + tier_count * 10 + lower_tier_total * 0.1

        - Big jumps between tiers force the band ordering.
        - tier_count orders puzzles within a band.
        - lower_tier_total breaks ties when tier_count is equal.
        """
        return (
            float(self.max_tier) * 1000.0
            + float(self.tier_count) * 10.0
            + float(self.lower_tier_total) * 0.1
        )


def solve(puzzle: Puzzle, max_iterations: int = 1000) -> DeductionResult:
    state = SolverState(puzzle)

    try:
        apply_hint_init(state)
    except Inconsistent as exc:
        return _fail(state, f"contradiction during init: {exc}")

    try:
        _run_inner_loop(state, max_iterations)
        # If inner loop stalled without solving, escalate to T14 (tier 4).
        while not state.is_solved():
            from rpn.tactics import t14_bounded_contradiction

            if not t14_bounded_contradiction(state):
                break  # T14 produced nothing new; truly stalled.
            _run_inner_loop(state, max_iterations)
    except Inconsistent as exc:
        return _fail(state, str(exc))

    by_tactic: dict[str, int] = {}
    for step in state.steps:
        by_tactic[step.tactic] = by_tactic.get(step.tactic, 0) + 1

    solved = state.is_solved()
    path = state.cell_path() if solved else None
    reason = "solved" if solved else "stalled"
    return DeductionResult(
        solved=solved,
        inconsistent=False,
        reason=reason,
        state=state,
        by_tactic=by_tactic,
        total_steps=len(state.steps),
        path=path,
    )


def _run_inner_loop(state: SolverState, max_iterations: int) -> None:
    """Run T1-T13 to fixed point. Caller catches `Inconsistent`."""
    for _ in range(max_iterations):
        progress = False
        for _, tactic in TACTICS:
            if tactic(state):
                progress = True
        if not progress:
            return
    raise Inconsistent(
        f"deduction inner loop did not converge within {max_iterations} iterations"
    )


def _fail(state: SolverState, reason: str) -> DeductionResult:
    by_tactic: dict[str, int] = {}
    for step in state.steps:
        by_tactic[step.tactic] = by_tactic.get(step.tactic, 0) + 1
    return DeductionResult(
        solved=False,
        inconsistent=True,
        reason=reason,
        state=state,
        by_tactic=by_tactic,
        total_steps=len(state.steps),
        path=None,
    )

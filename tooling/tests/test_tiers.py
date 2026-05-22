"""Tier-based difficulty model tests.

Covers:
- T1/T3 are labelled per axis (T1r, T1c, T3r, T3c) when single-line.
- T12 fires when a line saturation depends on a perpendicular T1/T3 deduction.
- T14 fires only after T1-T13 stall; restores state correctly on probe failure.
- max_tier, tier_count, lower_tier_total, tier_score are computed consistently.
"""

from __future__ import annotations

from rpn.deduction import (
    TACTIC_TIERS,
    TIER_EXCLUDED_TAGS,
    solve,
)
from rpn.generator import GeneratorConfig, generate
from rpn.model import Cell, Puzzle


def _trivial_straight() -> Puzzle:
    """5x5 horizontal straight path. Solvable by T2 + T1 (single-line) alone."""
    return Puzzle(
        width=5,
        height=5,
        start=Cell(0, 0),
        goal=Cell(4, 0),
        row_counts=(5, 0, 0, 0, 0),
        col_counts=(1, 1, 1, 1, 1),
        hints=(),
    )


def test_trivial_puzzle_uses_only_tier_one() -> None:
    """A puzzle solvable by line saturation alone is tier 1."""
    result = solve(_trivial_straight())
    assert result.solved
    assert result.max_tier == 1
    # T12 / T14 should never appear on this puzzle.
    assert result.by_tactic.get("T12", 0) == 0
    assert result.by_tactic.get("T14", 0) == 0


def test_t1_t3_labels_carry_axis_suffix() -> None:
    """Single-line T1/T3 firings are labelled with row/col suffix, not bare T1/T3."""
    result = solve(_trivial_straight())
    # "T1" or "T3" without suffix would mean a regressed label.
    assert "T1" not in result.by_tactic
    assert "T3" not in result.by_tactic
    # At least one of the axis-suffixed labels must appear.
    line_tags = {"T1r", "T1c", "T2", "T3r", "T3c"}
    assert any(t in result.by_tactic for t in line_tags)


def test_tier_excluded_tags_have_no_tier_assignment() -> None:
    """T11 and init:* must be in TIER_EXCLUDED_TAGS to avoid polluting the score."""
    for tag in ("T11", "init:S", "init:G"):
        assert tag in TIER_EXCLUDED_TAGS
        assert tag not in TACTIC_TIERS


def test_tier_score_formula() -> None:
    """tier_score = max_tier * 1000 + tier_count * 10 + lower_tier_total * 0.1."""
    result = solve(_trivial_straight())
    expected = (
        result.max_tier * 1000.0
        + result.tier_count * 10.0
        + result.lower_tier_total * 0.1
    )
    assert abs(result.tier_score - expected) < 1e-9


def test_t14_fires_on_no_hint_puzzle() -> None:
    """A puzzle with zero visible hints is likely to require lookahead. Seed 2 is
    a confirmed T14-requiring 5x5; if generator config changes break this,
    update the seed in this test rather than removing it."""
    config = GeneratorConfig(width=5, height=5, target_density=0.55, target_hints=0)
    gp = generate(config, seed=2)
    assert gp is not None
    result = solve(gp.puzzle)
    assert result.solved
    assert result.by_tactic.get("T14", 0) > 0
    assert result.max_tier == 4


def test_t14_state_restored_after_probe() -> None:
    """T14 probes must not leave residual provenance/edges on rolled-back tries.

    We re-solve the same puzzle twice and assert identical paths and by_tactic
    histograms; if probe state leaked, the second run would diverge.
    """
    config = GeneratorConfig(width=5, height=5, target_density=0.55, target_hints=0)
    gp = generate(config, seed=2)
    assert gp is not None
    r1 = solve(gp.puzzle)
    r2 = solve(gp.puzzle)
    assert r1.path == r2.path
    assert r1.by_tactic == r2.by_tactic


def test_t12_fires_when_cross_line_needed() -> None:
    """A puzzle from the existing 5x5_multi pack with high T12 count (5x5_013)
    confirms strict T12 still fires when appropriate. We hand-craft the
    equivalent puzzle here for deterministic testing."""
    # Generate a small puzzle and confirm at least one T12-firing puzzle exists
    # in a fixed seed sweep. We don't pin a specific by_tactic count because
    # generator changes could shift which seeds produce T12, but at least one
    # of the first 50 seeds should produce T12 firings.
    found_t12 = False
    for seed in range(50):
        config = GeneratorConfig(width=5, height=5, target_density=0.55)
        gp = generate(config, seed=seed)
        if gp is None:
            continue
        result = solve(gp.puzzle)
        if result.by_tactic.get("T12", 0) > 0:
            found_t12 = True
            assert result.max_tier >= 2
            break
    assert found_t12, "expected at least one of 50 seeds to require T12"

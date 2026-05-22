"""Hand-crafted puzzle fixtures and round-trip tests.

Five fixtures, all from `design/01_solver.md` §5. Each fixture is tested
against both the deduction solver and the CP-SAT uniqueness checker; when
both report a solution, they must agree cell-for-cell.
"""

from __future__ import annotations

import pytest

from rpn.deduction import solve
from rpn.model import Cell, Direction, Puzzle, Segment
from rpn.uniqueness import UniquenessStatus, check_uniqueness


def _trivial_straight() -> Puzzle:
    """5x5, S=(0,0), G=(4,0), straight path along row 0."""
    return Puzzle(
        width=5,
        height=5,
        start=Cell(0, 0),
        goal=Cell(4, 0),
        row_counts=(5, 0, 0, 0, 0),
        col_counts=(1, 1, 1, 1, 1),
        hints=(),
    )


def _l_shape() -> Puzzle:
    """3x3, S=(0,0), G=(2,2)."""
    return Puzzle(
        width=3,
        height=3,
        start=Cell(0, 0),
        goal=Cell(2, 2),
        row_counts=(1, 1, 3),
        col_counts=(3, 1, 1),
        hints=(),
    )


def _prototype_level_one() -> Puzzle:
    """Reading of the HTML prototype's level 1 from the screenshot."""
    return Puzzle(
        width=5,
        height=5,
        start=Cell(4, 2),
        goal=Cell(0, 4),
        row_counts=(2, 2, 3, 5, 3),
        col_counts=(5, 5, 2, 1, 2),
        hints=(),
    )


def _inconsistent() -> Puzzle:
    """Trivial straight but with a wrong row count."""
    return Puzzle(
        width=5,
        height=5,
        start=Cell(0, 0),
        goal=Cell(4, 0),
        row_counts=(3, 0, 0, 0, 0),  # path needs to reach G but only 3 cells allowed in row 0
        col_counts=(1, 1, 1, 0, 0),
        hints=(),
    )


def _multi_solution() -> Puzzle:
    """3x3 fully-covered grid, S=(0,0) G=(0,2): two distinct Hamiltonian paths."""
    return Puzzle(
        width=3,
        height=3,
        start=Cell(0, 0),
        goal=Cell(0, 2),
        row_counts=(3, 3, 3),
        col_counts=(3, 3, 3),
        hints=(),
    )


# Helpers ---------------------------------------------------------------------


def _assert_path_valid(path: tuple[Cell, ...], puzzle: Puzzle) -> None:
    assert path[0] == puzzle.start, f"path starts at {path[0]}, expected {puzzle.start}"
    assert path[-1] == puzzle.goal, f"path ends at {path[-1]}, expected {puzzle.goal}"
    seen = set(path)
    assert len(seen) == len(path), "path repeats a cell"
    for a, b in zip(path, path[1:]):
        assert abs(a.col - b.col) + abs(a.row - b.row) == 1, f"non-adjacent step: {a}->{b}"

    # row/col counts must match.
    actual_row = [0] * puzzle.height
    actual_col = [0] * puzzle.width
    for cell in path:
        actual_row[cell.row] += 1
        actual_col[cell.col] += 1
    assert tuple(actual_row) == puzzle.row_counts
    assert tuple(actual_col) == puzzle.col_counts


# Tests -----------------------------------------------------------------------


def test_trivial_straight_deduction() -> None:
    puzzle = _trivial_straight()
    result = solve(puzzle)
    assert result.solved
    assert result.path is not None
    _assert_path_valid(result.path, puzzle)


def test_trivial_straight_unique() -> None:
    puzzle = _trivial_straight()
    result = check_uniqueness(puzzle)
    assert result.status == UniquenessStatus.UNIQUE
    assert result.first_solution_path is not None
    _assert_path_valid(result.first_solution_path, puzzle)


def test_l_shape_deduction() -> None:
    puzzle = _l_shape()
    result = solve(puzzle)
    assert result.solved
    assert result.path == (
        Cell(0, 0), Cell(0, 1), Cell(0, 2), Cell(1, 2), Cell(2, 2),
    )


def test_l_shape_unique() -> None:
    puzzle = _l_shape()
    result = check_uniqueness(puzzle)
    assert result.status == UniquenessStatus.UNIQUE


def test_prototype_level_one_unique() -> None:
    puzzle = _prototype_level_one()
    result = check_uniqueness(puzzle)
    assert result.status == UniquenessStatus.UNIQUE
    assert result.first_solution_path is not None
    _assert_path_valid(result.first_solution_path, puzzle)
    assert len(result.first_solution_path) == 15


def test_inconsistent_returns_infeasible() -> None:
    puzzle = _inconsistent()
    result = check_uniqueness(puzzle)
    assert result.status == UniquenessStatus.INFEASIBLE


def test_inconsistent_deduction_fails() -> None:
    puzzle = _inconsistent()
    result = solve(puzzle)
    assert not result.solved
    # Either inconsistent (detected via contradiction) or stalled at non-full.
    # Both outcomes are acceptable failures.


def test_multi_solution_reports_multiple() -> None:
    puzzle = _multi_solution()
    result = check_uniqueness(puzzle)
    assert result.status == UniquenessStatus.MULTIPLE
    assert result.first_solution_path is not None
    assert result.second_solution_path is not None
    assert result.first_solution_path != result.second_solution_path


def test_deduction_and_uniqueness_agree_on_solvable() -> None:
    """When both solvers reach a solution, they must agree cell-by-cell."""
    for puzzle in (_trivial_straight(), _l_shape(), _prototype_level_one()):
        ded = solve(puzzle)
        uniq = check_uniqueness(puzzle)
        if uniq.status == UniquenessStatus.UNIQUE and ded.solved:
            assert ded.path == uniq.first_solution_path, (
                f"deduction and uniqueness disagree on {puzzle}"
            )

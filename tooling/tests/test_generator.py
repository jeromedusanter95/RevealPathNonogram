"""Generator tests.

Covers:
- Reproducibility: same seed → same puzzle.
- Validity invariants on every generated puzzle.
- Round-trip with deduction solver.
- Round-trip with uniqueness checker.
"""

from __future__ import annotations

import pytest

from rpn.deduction import solve
from rpn.generator import GeneratedPuzzle, GeneratorConfig, generate
from rpn.uniqueness import UniquenessStatus, check_uniqueness


def _generate(width: int, height: int, seed: int) -> GeneratedPuzzle:
    config = GeneratorConfig(width=width, height=height, target_density=0.55)
    result = generate(config, seed=seed)
    assert result is not None, f"failed to generate {width}x{height} seed={seed}"
    return result


def test_reproducibility_same_seed_same_puzzle() -> None:
    a = _generate(5, 5, seed=42)
    b = _generate(5, 5, seed=42)
    assert a.puzzle == b.puzzle
    assert a.solution_path == b.solution_path
    assert a.difficulty == b.difficulty


def test_different_seeds_produce_different_puzzles() -> None:
    a = _generate(5, 5, seed=42)
    b = _generate(5, 5, seed=43)
    # In rare cases two seeds could produce the same puzzle, but with these
    # specific seeds we expect different ones.
    assert a.puzzle != b.puzzle


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_row_col_counts_sum_to_path_length(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    assert sum(g.puzzle.row_counts) == sum(g.puzzle.col_counts)
    assert sum(g.puzzle.row_counts) == len(g.solution_path)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_solution_path_is_valid(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    path = g.solution_path
    assert path[0] == g.puzzle.start
    assert path[-1] == g.puzzle.goal
    assert len(set(path)) == len(path)
    for a, b in zip(path, path[1:]):
        assert abs(a.col - b.col) + abs(a.row - b.row) == 1


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_hints_reference_path_cells(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    path_set = set(g.solution_path)
    for hint in g.puzzle.hints:
        assert hint.cell in path_set


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_endpoint_hints_are_one_sided(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    endpoints = {g.puzzle.start, g.puzzle.goal}
    for hint in g.puzzle.hints:
        if hint.cell in endpoints:
            assert len(hint.sides) == 1
        else:
            assert len(hint.sides) == 2


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_deduction_solves_generated_puzzle(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    result = solve(g.puzzle)
    assert result.solved, f"deduction failed on seed {seed}: {result.reason}"
    assert result.path == g.solution_path


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_generated_puzzle_is_unique(seed: int) -> None:
    g = _generate(5, 5, seed=seed)
    result = check_uniqueness(g.puzzle)
    assert result.status == UniquenessStatus.UNIQUE
    assert result.first_solution_path == g.solution_path


def test_generator_handles_larger_grids() -> None:
    g = _generate(7, 7, seed=0)
    assert len(g.solution_path) > 0
    result = solve(g.puzzle)
    assert result.solved

"""Core puzzle data model.

A `Puzzle` is the immutable specification of a single level: grid size, S/G
positions, row/column counts, and visible hints. The deduction solver and the
CP-SAT uniqueness checker both consume `Puzzle` instances unchanged.

Conventions:
- Coordinates are `(col, row)`, 0-indexed, origin top-left.
- Compass directions: N (row-1), E (col+1), S (row+1), W (col-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


class Direction(Enum):
    N = "N"
    E = "E"
    S = "S"
    W = "W"

    @property
    def delta(self) -> tuple[int, int]:
        return _DELTAS[self]

    @property
    def opposite(self) -> Direction:
        return _OPPOSITES[self]


_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.N: (0, -1),
    Direction.E: (1, 0),
    Direction.S: (0, 1),
    Direction.W: (-1, 0),
}

_OPPOSITES: dict[Direction, Direction] = {
    Direction.N: Direction.S,
    Direction.S: Direction.N,
    Direction.E: Direction.W,
    Direction.W: Direction.E,
}


class Cell(NamedTuple):
    col: int
    row: int

    def neighbor(self, direction: Direction) -> Cell:
        dc, dr = direction.delta
        return Cell(self.col + dc, self.row + dr)


@dataclass(frozen=True, slots=True)
class Segment:
    """A visible in-grid hint at one cell.

    `sides` lists the cell borders the path connects through.
    - 1-sided: only valid at S or G; the path uses the single named neighbor.
    - 2-sided: only valid at non-endpoint path cells; the path enters from one
      side and exits via the other.
    """

    cell: Cell
    sides: frozenset[Direction]

    def __post_init__(self) -> None:
        if len(self.sides) not in (1, 2):
            raise ValueError(
                f"Segment must have 1 or 2 sides, got {len(self.sides)} at {self.cell}"
            )


@dataclass(frozen=True, slots=True)
class Puzzle:
    width: int
    height: int
    start: Cell
    goal: Cell
    row_counts: tuple[int, ...]
    col_counts: tuple[int, ...]
    hints: tuple[Segment, ...]

    def __post_init__(self) -> None:
        _validate_puzzle(self)

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell.col < self.width and 0 <= cell.row < self.height

    def all_cells(self) -> list[Cell]:
        return [Cell(c, r) for r in range(self.height) for c in range(self.width)]

    def neighbors(self, cell: Cell) -> list[tuple[Direction, Cell]]:
        result: list[tuple[Direction, Cell]] = []
        for d in Direction:
            n = cell.neighbor(d)
            if self.in_bounds(n):
                result.append((d, n))
        return result

    @property
    def path_length(self) -> int:
        """Number of path cells. Identity: row_counts and col_counts must sum to this."""
        return sum(self.row_counts)


def _validate_puzzle(puzzle: Puzzle) -> None:
    if puzzle.width < 1 or puzzle.height < 1:
        raise ValueError(f"width and height must be >= 1, got {puzzle.width}x{puzzle.height}")

    if len(puzzle.row_counts) != puzzle.height:
        raise ValueError(
            f"row_counts has {len(puzzle.row_counts)} entries, expected {puzzle.height}"
        )

    if len(puzzle.col_counts) != puzzle.width:
        raise ValueError(
            f"col_counts has {len(puzzle.col_counts)} entries, expected {puzzle.width}"
        )

    if not puzzle.in_bounds(puzzle.start):
        raise ValueError(f"start {puzzle.start} is out of bounds")

    if not puzzle.in_bounds(puzzle.goal):
        raise ValueError(f"goal {puzzle.goal} is out of bounds")

    if puzzle.start == puzzle.goal:
        raise ValueError("start and goal must differ")

    row_sum = sum(puzzle.row_counts)
    col_sum = sum(puzzle.col_counts)
    if row_sum != col_sum:
        raise ValueError(
            f"row_counts sum ({row_sum}) must equal col_counts sum ({col_sum})"
        )

    if row_sum < 2:
        raise ValueError(
            f"path must contain at least S and G; row_counts sum = {row_sum}"
        )

    for r_count in puzzle.row_counts:
        if not 0 <= r_count <= puzzle.width:
            raise ValueError(f"row count {r_count} out of range [0, {puzzle.width}]")

    for c_count in puzzle.col_counts:
        if not 0 <= c_count <= puzzle.height:
            raise ValueError(f"col count {c_count} out of range [0, {puzzle.height}]")

    endpoint_cells = {puzzle.start, puzzle.goal}
    seen_hint_cells: set[Cell] = set()
    for hint in puzzle.hints:
        if not puzzle.in_bounds(hint.cell):
            raise ValueError(f"hint cell {hint.cell} out of bounds")
        if hint.cell in seen_hint_cells:
            raise ValueError(f"duplicate hint at {hint.cell}")
        seen_hint_cells.add(hint.cell)

        is_endpoint = hint.cell in endpoint_cells
        if is_endpoint and len(hint.sides) != 1:
            raise ValueError(
                f"hint at endpoint {hint.cell} must have 1 side, got {len(hint.sides)}"
            )
        if not is_endpoint and len(hint.sides) != 2:
            raise ValueError(
                f"hint at non-endpoint {hint.cell} must have 2 sides, got {len(hint.sides)}"
            )

        for side in hint.sides:
            neighbor = hint.cell.neighbor(side)
            if not puzzle.in_bounds(neighbor):
                raise ValueError(
                    f"hint at {hint.cell} points off-grid in direction {side.value}"
                )

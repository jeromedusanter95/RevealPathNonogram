"""Mutable working state shared by every deduction tactic.

The state holds tri-state values for each cell and each edge of the grid. A
union-find tracks connectivity of cells joined by USED edges, used by T9 to
detect premature cycles.
"""

from __future__ import annotations

from enum import Enum

from rpn.model import Cell, Direction, Puzzle, Segment


class CellState(Enum):
    UNKNOWN = "?"
    FILLED = "F"
    EMPTY = "E"


class EdgeState(Enum):
    UNKNOWN = "?"
    USED = "U"
    UNUSED = "X"


class Inconsistent(Exception):
    """Raised by tactic application when the puzzle reaches a contradiction.

    The deduction solver catches this and returns a failure result. The
    generator's HINT loop uses this to discard candidate hint sets.
    """


_HORIZONTAL = (Direction.E, Direction.W)


def _edge_key(a: Cell, b: Cell) -> tuple[Cell, Cell]:
    """Canonical undirected edge key: sort the two endpoints."""
    return (a, b) if (a.col, a.row) <= (b.col, b.row) else (b, a)


class UnionFind:
    """Path-compression union-find over cells. Used by T9 (cycle detection)."""

    __slots__ = ("_parent",)

    def __init__(self) -> None:
        self._parent: dict[Cell, Cell] = {}

    def find(self, c: Cell) -> Cell:
        parent = self._parent.setdefault(c, c)
        if parent == c:
            return c
        root = self.find(parent)
        self._parent[c] = root
        return root

    def union(self, a: Cell, b: Cell) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def same(self, a: Cell, b: Cell) -> bool:
        return self.find(a) == self.find(b)


class _StateSnapshot:
    """Frozen copy of the mutable parts of a SolverState. See `SolverState.snapshot`."""

    __slots__ = ("cells", "edges", "uf_parent", "provenance", "steps_len")

    def __init__(
        self,
        cells: dict[Cell, "CellState"],
        edges: dict[tuple[Cell, Cell], "EdgeState"],
        uf_parent: dict[Cell, Cell],
        provenance: dict[Cell, str],
        steps_len: int,
    ) -> None:
        self.cells = cells
        self.edges = edges
        self.uf_parent = uf_parent
        self.provenance = provenance
        self.steps_len = steps_len


class SolverState:
    """Working state for the deduction solver.

    Mutations flow through `set_cell` and `set_edge`; both raise
    `Inconsistent` on contradiction and return True iff the value actually
    changed. Tactics use the return flag to decide whether to keep looping.
    """

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self.cells: dict[Cell, CellState] = {
            cell: CellState.UNKNOWN for cell in puzzle.all_cells()
        }
        self.edges: dict[tuple[Cell, Cell], EdgeState] = {}
        for cell in puzzle.all_cells():
            for direction, neighbor in puzzle.neighbors(cell):
                if direction in _HORIZONTAL:
                    continue  # avoid double-insertion
                self.edges[_edge_key(cell, neighbor)] = EdgeState.UNKNOWN
            for direction, neighbor in puzzle.neighbors(cell):
                key = _edge_key(cell, neighbor)
                if key not in self.edges:
                    self.edges[key] = EdgeState.UNKNOWN

        self.union_find = UnionFind()
        self.steps: list[Step] = []
        # Records the tactic that most recently set each known cell. Used by
        # T12 to detect cross-line reasoning: a line-saturation step is
        # cross-line iff the cells that made saturation possible were set by
        # a tactic on the perpendicular axis (not by hints or local tactics).
        self.cell_provenance: dict[Cell, str] = {}

    def set_cell(self, cell: Cell, value: CellState, tactic: str) -> bool:
        current = self.cells[cell]
        if current == value:
            return False
        if current != CellState.UNKNOWN:
            raise Inconsistent(
                f"{tactic}: cell {cell} already {current.name}, refused to set {value.name}"
            )
        self.cells[cell] = value
        self.cell_provenance[cell] = tactic
        self.steps.append(Step(tactic=tactic, kind="cell", target=cell, value=value.name))
        return True

    def set_edge(self, a: Cell, b: Cell, value: EdgeState, tactic: str) -> bool:
        key = _edge_key(a, b)
        current = self.edges[key]
        if current == value:
            return False
        if current != EdgeState.UNKNOWN:
            raise Inconsistent(
                f"{tactic}: edge {key} already {current.name}, refused to set {value.name}"
            )
        self.edges[key] = value
        if value == EdgeState.USED:
            ca, cb = key
            if self.union_find.same(ca, cb):
                raise Inconsistent(
                    f"{tactic}: edge {key} would close a premature cycle"
                )
            self.union_find.union(ca, cb)
        self.steps.append(Step(tactic=tactic, kind="edge", target=key, value=value.name))
        return True

    def snapshot(self) -> "_StateSnapshot":
        """Capture current state. Pair with `restore` to roll back a probe.

        Used by T14: try a tentative cell assignment, run a sweep, and roll
        back if it doesn't yield a contradiction.
        """
        return _StateSnapshot(
            cells=dict(self.cells),
            edges=dict(self.edges),
            uf_parent=dict(self.union_find._parent),
            provenance=dict(self.cell_provenance),
            steps_len=len(self.steps),
        )

    def restore(self, snap: "_StateSnapshot") -> None:
        self.cells = snap.cells
        self.edges = snap.edges
        self.union_find._parent = snap.uf_parent
        self.cell_provenance = snap.provenance
        del self.steps[snap.steps_len:]

    def edge_state(self, a: Cell, b: Cell) -> EdgeState:
        return self.edges[_edge_key(a, b)]

    def incident_edges(self, cell: Cell) -> list[tuple[Direction, Cell, EdgeState]]:
        """Return list of (direction, neighbor, edge_state) for each in-grid neighbor."""
        result: list[tuple[Direction, Cell, EdgeState]] = []
        for direction, neighbor in self.puzzle.neighbors(cell):
            result.append((direction, neighbor, self.edge_state(cell, neighbor)))
        return result

    def is_solved(self) -> bool:
        return all(state != CellState.UNKNOWN for state in self.cells.values())

    def cell_path(self) -> tuple[Cell, ...] | None:
        """Return the path S→G if the state determines one, else None.

        A fully decided state with consistent degree constraints has a unique
        path (or no path, but we'd have raised earlier).
        """
        if not self.is_solved():
            return None

        adjacency: dict[Cell, list[Cell]] = {c: [] for c, s in self.cells.items() if s == CellState.FILLED}
        for (a, b), edge_state in self.edges.items():
            if edge_state == EdgeState.USED:
                adjacency[a].append(b)
                adjacency[b].append(a)

        path: list[Cell] = [self.puzzle.start]
        seen = {self.puzzle.start}
        while path[-1] != self.puzzle.goal:
            current = path[-1]
            next_cells = [n for n in adjacency[current] if n not in seen]
            if len(next_cells) != 1:
                return None
            nxt = next_cells[0]
            path.append(nxt)
            seen.add(nxt)
        return tuple(path)


class Step:
    """Record of one cell or edge fact derived by a tactic."""

    __slots__ = ("tactic", "kind", "target", "value")

    def __init__(self, tactic: str, kind: str, target: object, value: str) -> None:
        self.tactic = tactic
        self.kind = kind
        self.target = target
        self.value = value

    def __repr__(self) -> str:
        return f"Step({self.tactic}, {self.kind}={self.target}, {self.value})"


def apply_hint_init(state: SolverState) -> bool:
    """Initial pass: set S and G FILLED, then apply T11 (hint propagation).

    Called once before the main deduction loop. Returns True if anything
    changed (it always will for a non-empty puzzle).
    """
    changed = False
    changed |= state.set_cell(state.puzzle.start, CellState.FILLED, "init:S")
    changed |= state.set_cell(state.puzzle.goal, CellState.FILLED, "init:G")
    for hint in state.puzzle.hints:
        changed |= _apply_segment(state, hint)
    return changed


def _apply_segment(state: SolverState, hint: Segment) -> bool:
    changed = state.set_cell(hint.cell, CellState.FILLED, "T11")
    for direction, neighbor in state.puzzle.neighbors(hint.cell):
        target = EdgeState.USED if direction in hint.sides else EdgeState.UNUSED
        changed |= state.set_edge(hint.cell, neighbor, target, "T11")
    return changed

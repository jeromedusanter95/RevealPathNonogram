"""Deduction tactics T1-T11.

Each tactic returns True iff it changed any cell or edge value. The main
solver loop calls every tactic in order, repeating until a full sweep makes
no progress.

Naming follows `design/01_solver.md` §2.
"""

from __future__ import annotations

from collections.abc import Callable

from rpn.model import Cell
from rpn.state import CellState, EdgeState, SolverState


Tactic = Callable[[SolverState], bool]


def _line_cells(state: SolverState, axis: str, index: int) -> list[Cell]:
    if axis == "row":
        return [Cell(c, index) for c in range(state.puzzle.width)]
    return [Cell(index, r) for r in range(state.puzzle.height)]


def _line_counts(state: SolverState, axis: str, index: int) -> tuple[int, int, int]:
    """Return (filled_count, empty_count, unknown_count) for one row or column."""
    filled = empty = unknown = 0
    for cell in _line_cells(state, axis, index):
        s = state.cells[cell]
        if s == CellState.FILLED:
            filled += 1
        elif s == CellState.EMPTY:
            empty += 1
        else:
            unknown += 1
    return filled, empty, unknown


def _line_clue(state: SolverState, axis: str, index: int) -> int:
    return (
        state.puzzle.row_counts[index]
        if axis == "row"
        else state.puzzle.col_counts[index]
    )


_PERPENDICULAR_SATURATION_TAGS = {
    "row": {"T1c", "T3c"},
    "col": {"T1r", "T3r"},
}


def _is_cross_line(
    state: SolverState,
    axis: str,
    cells: list[Cell],
    counted_state: CellState,
) -> bool:
    """True iff a perpendicular-axis T1/T3 deduction is *necessary* for this firing.

    A line-saturation firing is triggered by a count of cells in some target
    CellState reaching a threshold (e.g. filled == clue forces EMPTYs; the
    contributing cells are FILLED). The firing is cross-line iff at least one
    of those contributing cells was set by T1/T3 on the perpendicular axis.

    Without that perpendicular contribution the count would drop below the
    threshold and the firing would not happen, so the perpendicular tactic is
    a necessary input. This matches what a player would experience: "I need
    to know what the column told me before this row's count works out."

    Cells set by hint init (T11), endpoint init, or local path tactics
    (T4-T10) do not count as cross-line: the player got those for free or
    derived them locally.
    """
    perpendicular_tags = _PERPENDICULAR_SATURATION_TAGS[axis]
    for cell in cells:
        if state.cells[cell] != counted_state:
            continue
        provenance = state.cell_provenance.get(cell)
        if provenance in perpendicular_tags:
            return True
    return False


def t1_saturation(state: SolverState) -> bool:
    """T1: if filled count equals clue, remaining UNKNOWNs become EMPTY; symmetric for spaces.

    Per-firing label:
      - "T1r" / "T1c" when single-line: this firing's count is reached without
        any contribution from T1/T3 on the perpendicular axis.
      - "T12" when cross-line: at least one of the cells in the contributing
        state (FILLED for filled-saturation, EMPTY for empty-saturation) was
        set by T1/T3 on the perpendicular axis. Tier-2 in the difficulty model.
    """
    changed = False
    puzzle = state.puzzle
    for axis, length in (("row", puzzle.height), ("col", puzzle.width)):
        for index in range(length):
            clue = _line_clue(state, axis, index)
            filled, empty, _ = _line_counts(state, axis, index)
            cells = _line_cells(state, axis, index)
            line_length = puzzle.width if axis == "row" else puzzle.height
            if filled == clue:
                cross = _is_cross_line(state, axis, cells, CellState.FILLED)
                tactic = "T12" if cross else f"T1{axis[0]}"
                for cell in cells:
                    if state.cells[cell] == CellState.UNKNOWN:
                        changed |= state.set_cell(cell, CellState.EMPTY, tactic)
            if empty == line_length - clue:
                cross = _is_cross_line(state, axis, cells, CellState.EMPTY)
                tactic = "T12" if cross else f"T1{axis[0]}"
                for cell in cells:
                    if state.cells[cell] == CellState.UNKNOWN:
                        changed |= state.set_cell(cell, CellState.FILLED, tactic)
    return changed


def t2_trivial_extremes(state: SolverState) -> bool:
    """T2: clue == 0 → all EMPTY; clue == lineLength → all FILLED."""
    changed = False
    puzzle = state.puzzle
    for axis, length in (("row", puzzle.height), ("col", puzzle.width)):
        for index in range(length):
            clue = _line_clue(state, axis, index)
            cells = _line_cells(state, axis, index)
            line_length = puzzle.width if axis == "row" else puzzle.height
            if clue == 0:
                for cell in cells:
                    if state.cells[cell] != CellState.EMPTY:
                        changed |= state.set_cell(cell, CellState.EMPTY, "T2")
            elif clue == line_length:
                for cell in cells:
                    if state.cells[cell] != CellState.FILLED:
                        changed |= state.set_cell(cell, CellState.FILLED, "T2")
    return changed


def t3_capacity_bound(state: SolverState) -> bool:
    """T3: if filled + unknown == clue, every UNKNOWN in the line is FILLED.

    See T1's docstring for the T12 cross-line relabel rule.
    """
    changed = False
    puzzle = state.puzzle
    for axis, length in (("row", puzzle.height), ("col", puzzle.width)):
        for index in range(length):
            clue = _line_clue(state, axis, index)
            filled, _, unknown = _line_counts(state, axis, index)
            if filled + unknown == clue and unknown > 0:
                cells = _line_cells(state, axis, index)
                # T3's count is `filled + unknown`. unknown is just the count
                # of remaining UNKNOWNs, not derived from any tactic, so the
                # contribution we care about is the FILLED count.
                cross = _is_cross_line(state, axis, cells, CellState.FILLED)
                tactic = "T12" if cross else f"T3{axis[0]}"
                for cell in cells:
                    if state.cells[cell] == CellState.UNKNOWN:
                        changed |= state.set_cell(cell, CellState.FILLED, tactic)
    return changed


def _required_degree(state: SolverState, cell: Cell) -> int | None:
    """Required path-degree given the cell's known FILLED/EMPTY state, else None."""
    cs = state.cells[cell]
    if cs == CellState.EMPTY:
        return 0
    if cs == CellState.FILLED:
        return 1 if cell in (state.puzzle.start, state.puzzle.goal) else 2
    return None


def _classify_edges(state: SolverState, cell: Cell) -> tuple[int, int, int]:
    used = unused = unknown = 0
    for _, _, edge_state in state.incident_edges(cell):
        if edge_state == EdgeState.USED:
            used += 1
        elif edge_state == EdgeState.UNUSED:
            unused += 1
        else:
            unknown += 1
    return used, unused, unknown


def _set_unknown_incident(
    state: SolverState, cell: Cell, target: EdgeState, tactic: str
) -> bool:
    changed = False
    for _, neighbor, edge_state in state.incident_edges(cell):
        if edge_state == EdgeState.UNKNOWN:
            changed |= state.set_edge(cell, neighbor, target, tactic)
    return changed


def t4_endpoint_degree(state: SolverState) -> bool:
    """T4: S and G have exactly one USED incident edge."""
    changed = False
    for cell in (state.puzzle.start, state.puzzle.goal):
        used, unused, unknown = _classify_edges(state, cell)
        if used == 1 and unknown > 0:
            changed |= _set_unknown_incident(state, cell, EdgeState.UNUSED, "T4")
        elif used == 0 and unknown == 1:
            changed |= _set_unknown_incident(state, cell, EdgeState.USED, "T4")
        if used > 1:
            from rpn.state import Inconsistent

            raise Inconsistent(f"T4: endpoint {cell} has {used} USED edges")
    return changed


def t5_filled_degree(state: SolverState) -> bool:
    """T5: non-endpoint FILLED cells have exactly two USED edges."""
    changed = False
    for cell, cell_state in state.cells.items():
        if cell_state != CellState.FILLED:
            continue
        if cell in (state.puzzle.start, state.puzzle.goal):
            continue
        used, unused, unknown = _classify_edges(state, cell)
        if used == 2 and unknown > 0:
            changed |= _set_unknown_incident(state, cell, EdgeState.UNUSED, "T5")
        elif used + unknown == 2 and unknown > 0:
            changed |= _set_unknown_incident(state, cell, EdgeState.USED, "T5")
        if used > 2:
            from rpn.state import Inconsistent

            raise Inconsistent(f"T5: filled cell {cell} has {used} USED edges")
    return changed


def t6_empty_degree(state: SolverState) -> bool:
    """T6: EMPTY cells have all incident edges UNUSED."""
    changed = False
    for cell, cell_state in state.cells.items():
        if cell_state != CellState.EMPTY:
            continue
        used, _, unknown = _classify_edges(state, cell)
        if used > 0:
            from rpn.state import Inconsistent

            raise Inconsistent(f"T6: empty cell {cell} has {used} USED edges")
        if unknown > 0:
            changed |= _set_unknown_incident(state, cell, EdgeState.UNUSED, "T6")
    return changed


def t7_edge_implies_cell(state: SolverState) -> bool:
    """T7: a USED edge forces both endpoints FILLED."""
    changed = False
    for (a, b), edge_state in state.edges.items():
        if edge_state != EdgeState.USED:
            continue
        if state.cells[a] == CellState.UNKNOWN:
            changed |= state.set_cell(a, CellState.FILLED, "T7")
        if state.cells[b] == CellState.UNKNOWN:
            changed |= state.set_cell(b, CellState.FILLED, "T7")
    return changed


def t8_clue_forced_unused(state: SolverState) -> bool:
    """T8: when a cell's required degree is met by USED edges, remaining UNKNOWNs become UNUSED.

    Equivalent to T4/T5 for the case where USED count already equals the
    requirement. Listed separately because for UNKNOWN cells we may also
    derive UNUSED edges using line/path bounds; for now this captures the
    FILLED/endpoint cases.
    """
    return False  # subsumed by T4/T5; reserved for future cross-line logic


def t9_no_premature_cycle(state: SolverState) -> bool:
    """T9: forbid edges whose endpoints are already in the same connected component.

    Mostly handled inline by `set_edge` (raises Inconsistent if it would close
    a cycle). Here we use it positively: if an UNKNOWN edge would close a
    cycle, mark it UNUSED.
    """
    changed = False
    for (a, b), edge_state in list(state.edges.items()):
        if edge_state != EdgeState.UNKNOWN:
            continue
        if state.union_find.same(a, b):
            changed |= state.set_edge(a, b, EdgeState.UNUSED, "T9")
    return changed


def t10_no_isolated_island(state: SolverState) -> bool:
    """T10: a cell that can no longer reach its required degree must be EMPTY (or contradict)."""
    changed = False
    for cell, cell_state in state.cells.items():
        used, unused, unknown = _classify_edges(state, cell)
        max_degree = used + unknown
        if cell_state == CellState.FILLED:
            required = 1 if cell in (state.puzzle.start, state.puzzle.goal) else 2
            if max_degree < required:
                from rpn.state import Inconsistent

                raise Inconsistent(
                    f"T10: filled cell {cell} can only reach degree {max_degree}, needs {required}"
                )
        elif cell_state == CellState.UNKNOWN:
            if max_degree < 2 and cell not in (state.puzzle.start, state.puzzle.goal):
                changed |= state.set_cell(cell, CellState.EMPTY, "T10")
            elif max_degree < 1:
                changed |= state.set_cell(cell, CellState.EMPTY, "T10")
    return changed


def t14_bounded_contradiction(state: SolverState) -> bool:
    """T14: 1-step lookahead. For each UNKNOWN cell, tentatively try FILLED and EMPTY.

    If exactly one of the two leads to a contradiction when running T1-T13 to
    fixed point, the other value is forced.

    Cost: O(unknown cells x inner-sweep runtime) per outer T14 call. Run only
    when the rest of the solver has stalled (caller responsibility). Single
    depth: the inner sweep excludes T14 itself.
    """
    changed = False
    unknowns = [c for c, s in state.cells.items() if s == CellState.UNKNOWN]
    for cell in unknowns:
        if state.cells[cell] != CellState.UNKNOWN:
            continue  # already decided by an earlier T14 firing in this pass
        filled_consistent = _probe(state, cell, CellState.FILLED)
        empty_consistent = _probe(state, cell, CellState.EMPTY)
        if filled_consistent and not empty_consistent:
            changed |= state.set_cell(cell, CellState.FILLED, "T14")
        elif empty_consistent and not filled_consistent:
            changed |= state.set_cell(cell, CellState.EMPTY, "T14")
        elif not filled_consistent and not empty_consistent:
            from rpn.state import Inconsistent

            raise Inconsistent(f"T14: cell {cell} contradicts on both FILLED and EMPTY")
    return changed


def _probe(state: SolverState, cell: Cell, value: CellState) -> bool:
    """Return True iff tentatively setting `cell` to `value` is consistent.

    Runs T1-T13 to fixed point with the tentative assignment. Restores state
    before returning. Does not call T14 (single-depth lookahead).
    """
    from rpn.state import Inconsistent

    snap = state.snapshot()
    try:
        state.set_cell(cell, value, "T14-probe")
        for _ in range(_PROBE_MAX_ITERATIONS):
            progress = False
            for _, tactic in _NON_PROBE_TACTICS:
                if tactic(state):
                    progress = True
            if not progress:
                break
        return True
    except Inconsistent:
        return False
    finally:
        state.restore(snap)


# Iteration cap for an inner T14 probe sweep. Same magnitude as the outer
# deduction loop's max_iterations (1000); probes are very unlikely to hit it
# but the cap prevents an unbounded loop if a future tactic regresses.
_PROBE_MAX_ITERATIONS = 200


TACTICS: list[tuple[str, Tactic]] = [
    ("T1", t1_saturation),
    ("T2", t2_trivial_extremes),
    ("T3", t3_capacity_bound),
    ("T4", t4_endpoint_degree),
    ("T5", t5_filled_degree),
    ("T6", t6_empty_degree),
    ("T7", t7_edge_implies_cell),
    ("T8", t8_clue_forced_unused),
    ("T9", t9_no_premature_cycle),
    ("T10", t10_no_isolated_island),
]


# Tactics T1-T13 are the "inner" set used by T14 probes. T14 itself is
# excluded to keep lookahead single-depth (no recursive contradictions).
_NON_PROBE_TACTICS: list[tuple[str, Tactic]] = TACTICS


# Public list including T14, used by the solver's outer loop when the inner
# loop stalls. See `deduction.solve`.
TACTICS_WITH_LOOKAHEAD: list[tuple[str, Tactic]] = TACTICS + [
    ("T14", t14_bounded_contradiction),
]

"""CP-SAT uniqueness checker.

Builds a constraint model with one boolean per cell and one per undirected
edge, posts the puzzle's hard constraints (row/col counts, degree, S/G
endpoints, hints), and enforces connectivity via depth labels (spanning-tree
encoding from Knijff 2021). Calls the solver with an enumeration callback
that stops after finding the second satisfying assignment.

Result: UNIQUE, MULTIPLE, or INFEASIBLE.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import cast

from ortools.sat.python import cp_model

from rpn.model import Cell, Direction, Puzzle, Segment


class UniquenessStatus(Enum):
    UNIQUE = "UNIQUE"
    MULTIPLE = "MULTIPLE"
    INFEASIBLE = "INFEASIBLE"


@dataclass(frozen=True, slots=True)
class UniquenessResult:
    status: UniquenessStatus
    first_solution_path: tuple[Cell, ...] | None
    second_solution_path: tuple[Cell, ...] | None


def _edge_key(a: Cell, b: Cell) -> tuple[Cell, Cell]:
    return (a, b) if (a.col, a.row) <= (b.col, b.row) else (b, a)


def check_uniqueness(puzzle: Puzzle) -> UniquenessResult:
    """Uniqueness via solve + blocking clause.

    Enumeration callbacks would count distinct values of every model variable,
    including the auxiliary depth labels used for the connectivity constraint.
    Two assignments with identical cell+edge values but different depth labels
    look like distinct solutions to the callback but are the same puzzle
    solution. So we instead use the blocking-clause technique: solve once on
    the full model, then add a constraint that forbids the exact cell+edge
    assignment and solve again. The depth labels remain free.
    """
    model, cell_vars, edge_vars = _build_model(puzzle)
    solver = cp_model.CpSolver()

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return UniquenessResult(UniquenessStatus.INFEASIBLE, None, None)

    first_cells = {cell: int(solver.Value(var)) for cell, var in cell_vars.items()}
    first_edges = {edge: int(solver.Value(var)) for edge, var in edge_vars.items()}
    first_path = _reconstruct_path(puzzle, first_cells, first_edges)

    # Block this exact cell+edge assignment.
    diff_terms: list[cp_model.IntVar | cp_model.LinearExpr] = []
    for cell, var in cell_vars.items():
        if first_cells[cell] == 1:
            diff_terms.append(1 - var)  # was 1, must become 0
        else:
            diff_terms.append(var)  # was 0, must become 1
    for edge, var in edge_vars.items():
        if first_edges[edge] == 1:
            diff_terms.append(1 - var)
        else:
            diff_terms.append(var)
    model.Add(sum(diff_terms) >= 1)

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return UniquenessResult(UniquenessStatus.UNIQUE, first_path, None)

    second_cells = {cell: int(solver.Value(var)) for cell, var in cell_vars.items()}
    second_edges = {edge: int(solver.Value(var)) for edge, var in edge_vars.items()}
    second_path = _reconstruct_path(puzzle, second_cells, second_edges)
    return UniquenessResult(UniquenessStatus.MULTIPLE, first_path, second_path)


def _build_model(
    puzzle: Puzzle,
) -> tuple[cp_model.CpModel, dict[Cell, cp_model.IntVar], dict[tuple[Cell, Cell], cp_model.IntVar]]:
    model = cp_model.CpModel()

    cell_vars: dict[Cell, cp_model.IntVar] = {}
    for cell in puzzle.all_cells():
        cell_vars[cell] = model.NewBoolVar(f"cell_{cell.col}_{cell.row}")

    # Endpoints are FILLED.
    model.Add(cell_vars[puzzle.start] == 1)
    model.Add(cell_vars[puzzle.goal] == 1)

    edge_vars: dict[tuple[Cell, Cell], cp_model.IntVar] = {}
    for cell in puzzle.all_cells():
        for direction, neighbor in puzzle.neighbors(cell):
            if direction in (Direction.S, Direction.E):
                key = _edge_key(cell, neighbor)
                edge_vars[key] = model.NewBoolVar(f"edge_{key[0].col}_{key[0].row}_{key[1].col}_{key[1].row}")

    # An edge can be USED only if both endpoints are FILLED.
    for (a, b), edge_var in edge_vars.items():
        model.Add(edge_var <= cell_vars[a])
        model.Add(edge_var <= cell_vars[b])

    # Degree constraints.
    for cell in puzzle.all_cells():
        incident: list[cp_model.IntVar] = []
        for _, neighbor in puzzle.neighbors(cell):
            incident.append(edge_vars[_edge_key(cell, neighbor)])
        if cell in (puzzle.start, puzzle.goal):
            model.Add(sum(incident) == 1)
        else:
            model.Add(sum(incident) == 2 * cell_vars[cell])

    # Row and column counts.
    for r in range(puzzle.height):
        model.Add(sum(cell_vars[Cell(c, r)] for c in range(puzzle.width)) == puzzle.row_counts[r])
    for c in range(puzzle.width):
        model.Add(sum(cell_vars[Cell(c, r)] for r in range(puzzle.height)) == puzzle.col_counts[c])

    # Hints: each hint fixes the cell and its incident edges.
    _post_hint_constraints(model, puzzle, cell_vars, edge_vars)

    # Connectivity via spanning-tree depth labels (Knijff 2021).
    #
    # For each cell, an integer depth ∈ [0, path_length-1]. S has depth 0.
    # Every FILLED cell other than S must have at least one USED incident edge
    # to a neighbor with depth = (own depth - 1). This is the standard
    # "parent-pointer" encoding that prevents disconnected components: the
    # depth labels alone are not enough (they don't constrain disconnected
    # components), so we explicitly require a strictly-decreasing edge.
    max_depth = puzzle.path_length - 1
    depth_vars: dict[Cell, cp_model.IntVar] = {}
    for cell in puzzle.all_cells():
        depth_vars[cell] = model.NewIntVar(0, max_depth, f"depth_{cell.col}_{cell.row}")

    model.Add(depth_vars[puzzle.start] == 0)

    # For every FILLED cell other than S, exactly one incident edge is the
    # "parent edge" (USED edge to a neighbor with depth - 1). We encode this
    # with auxiliary booleans `parent[c, n]` meaning "the parent of c is n".
    for cell in puzzle.all_cells():
        if cell == puzzle.start:
            continue
        parent_vars: list[cp_model.IntVar] = []
        for _, neighbor in puzzle.neighbors(cell):
            parent_var = model.NewBoolVar(
                f"parent_{cell.col}_{cell.row}_via_{neighbor.col}_{neighbor.row}"
            )
            parent_vars.append(parent_var)
            edge_var = edge_vars[_edge_key(cell, neighbor)]
            # If parent_var is True: edge is USED, neighbor depth + 1 == cell depth.
            model.Add(edge_var == 1).OnlyEnforceIf(parent_var)
            model.Add(depth_vars[cell] == depth_vars[neighbor] + 1).OnlyEnforceIf(parent_var)
        # Exactly one parent edge iff cell is FILLED, zero otherwise.
        model.Add(sum(parent_vars) == cell_vars[cell])

    return model, cell_vars, edge_vars


def _post_hint_constraints(
    model: cp_model.CpModel,
    puzzle: Puzzle,
    cell_vars: dict[Cell, cp_model.IntVar],
    edge_vars: dict[tuple[Cell, Cell], cp_model.IntVar],
) -> None:
    for hint in puzzle.hints:
        model.Add(cell_vars[hint.cell] == 1)
        for direction, neighbor in puzzle.neighbors(hint.cell):
            key = _edge_key(hint.cell, neighbor)
            value = 1 if direction in hint.sides else 0
            model.Add(edge_vars[key] == value)


def _reconstruct_path(
    puzzle: Puzzle,
    cells: dict[Cell, int],
    edges: dict[tuple[Cell, Cell], int],
) -> tuple[Cell, ...]:
    adjacency: dict[Cell, list[Cell]] = {}
    for cell, value in cells.items():
        if value == 1:
            adjacency[cell] = []
    for (a, b), value in edges.items():
        if value == 1:
            adjacency[a].append(b)
            adjacency[b].append(a)

    path: list[Cell] = [puzzle.start]
    seen = {puzzle.start}
    while path[-1] != puzzle.goal:
        current = path[-1]
        next_cells = [n for n in adjacency.get(current, []) if n not in seen]
        if not next_cells:
            return tuple(path)
        path.append(next_cells[0])
        seen.add(next_cells[0])
    return tuple(path)

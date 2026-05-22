# Solver Design (v0)

> Living design document. Updated as decisions evolve. Every load-bearing claim cites the relevant research file or external source.

## 0. Goal

We need two solvers, not one.

| Solver | Role | Output |
|---|---|---|
| **Deduction solver** | Plays the puzzle like a human. Applies only the v1 tactic set. | Final grid (if fully solved), trace of tactics used, or "stalled" with current partial grid. |
| **SAT/CP solver** | Ground truth. Used by the generator to verify uniqueness. Never shown to the player. | "Unique", "Multiple solutions", or "No solution". |

The generator (designed separately in `02_generator.md`) accepts a candidate puzzle only when:
1. The deduction solver fully solves it using only v1 tactics, AND
2. The SAT/CP solver confirms uniqueness.

(1) implies (2) by construction (deduction only ever fixes forced cells), but the SAT pass is a cheap belt-and-suspenders correctness check, plus it gives us a counterexample second-solution if our deduction logic is ever buggy. (Research basis: this is the Tatham/Batenburg "simple class" pattern from `research/01_nonogram.md` §3.5, §6.1, §9.)

## 1. Puzzle model

### 1.1 Grid

- Rectangle `W × H` cells. Origin top-left, `(col, row)` with `col ∈ [0, W)` and `row ∈ [0, H)`.
- Coordinates exposed to the player as 1-indexed (the prototype shows row labels 2/2/3/5/3 and column labels 5/5/2/1/2), but internally 0-indexed.

### 1.2 Endpoints

- Exactly one **Start `S`** cell at `(sc, sr)`.
- Exactly one **Goal `G`** cell at `(gc, gr)`.
- `S ≠ G`.

### 1.3 Cell state

Each cell has a tri-state value in the deduction solver:

- `FILLED`: known to be on the path.
- `EMPTY`: known to be off the path.
- `UNKNOWN`: not yet decided.

`S` and `G` are pre-set to `FILLED`.

### 1.4 Clues

- `row_counts[row] ∈ [0, W]`: number of path cells in that row.
- `col_counts[col] ∈ [0, H]`: number of path cells in that column.
- Both arrays always shown. (No "iced" clues in v1; deferred per `GAME_CONTEXT.md`.)

Identity: `sum(row_counts) == sum(col_counts) == path_length`.

### 1.5 In-grid hints

Each hint is attached to a specific cell and asserts shape information the solution must contain. A hint is rendered as a small line glyph inside the cell whose ends touch the cell borders facing the connected neighbors. There is **one hint type** with two arities, expressing how many of the four neighbors the path connects through this cell:

- `Segment(sides)` where `sides ⊂ {N, E, S, W}`:
  - `|sides| == 1`: only at `S` or `G`. One line on the named side, indicating the single neighbor the path connects to. The prototype shows S with a short downward line; same convention applies to G.
  - `|sides| == 2`: at any non-endpoint cell on the path. Two-neighbor connector. Six glyphs:
    - **Straights**: `{N,S}` vertical bar, `{E,W}` horizontal bar.
    - **Corners**: `{N,E}` ⌐-shape, `{N,W}`, `{S,E}`, `{S,W}`.
- A `Segment` is **direction-agnostic**: it asserts which neighbors are connected, but not which side is "before" and which is "after" along the path. Travel direction is determined globally by S→G.

Effect on solver state, for a `Segment(sides)` at cell `c`:
- `c` is `FILLED`.
- For each `d ∈ sides`: the incident edge of `c` in direction `d` is `USED`.
- For each `d ∉ sides` (still inside the grid): the incident edge in direction `d` is `UNUSED`.

Consistency requirement on hints (enforced by the generator, not the solver):
- A 1-sided segment may only appear at `S` or `G`.
- A 2-sided segment may only appear at non-endpoint cells.

Hints do NOT include "this cell is NOT on the path" in v1. (Deferred per `GAME_CONTEXT.md` open questions.)

### 1.6 Path

A sequence of `FILLED` cells `c[0] = S, c[1], …, c[L-1] = G` such that:

1. Every consecutive pair `c[i], c[i+1]` is orthogonally adjacent.
2. No cell appears twice (no self-crossing, no loops).
3. Every `FILLED` cell appears in the sequence (single connected component).
4. Every `EMPTY` cell does not appear in the sequence.

The path *does not* have to cover all cells. Coverage equals `path_length = sum(row_counts)`.

### 1.7 Edges (derived)

For the deduction solver it's often easier to reason about edges than cells.

- Each pair of orthogonally adjacent cells `(a, b)` has an undirected edge `e_ab`.
- Edge state: `USED`, `UNUSED`, `UNKNOWN`.
- An edge is `USED` iff the path traverses between those two cells.

Cell–edge consistency:

- A cell `c` has **path-degree** = number of incident `USED` edges. Notation: `deg(c)`.
- If `c == S` or `c == G`, `deg(c) = 1`.
- Else if `c` is `FILLED`, `deg(c) = 2`.
- Else if `c` is `EMPTY`, `deg(c) = 0`.

Hints fix incident edges: see §1.5. The 1-sided variant (only at `S`/`G`) fixes the single `USED` edge and the three `UNUSED` edges. The 2-sided variant fixes two `USED` edges and two `UNUSED` edges.

## 2. v1 tactic set

The deduction solver applies these tactics repeatedly until no progress is made. Each tactic is a *function from current state to a set of new forced facts*: cells flipped from `UNKNOWN` to `FILLED` or `EMPTY`, edges flipped from `UNKNOWN` to `USED` or `UNUSED`. A tactic never overwrites a previously-set value (if it would, the puzzle is inconsistent and the solver reports failure).

### 2.1 Nonogram line tactics

Each row and each column is a "line". The single integer clue gives the total count of `FILLED` cells in that line.

> Note. Classic nonogram tactics (overlap / glue / etc., see `research/01_nonogram.md` §3.1) are defined for sequences-of-runs clues. Our clue is a single total. The classical tactics specialise nicely to this case; the rules are weaker per line but still useful.

**T1. Saturation.**
If the count of `FILLED` cells in a line already equals the clue, every other cell in the line is `EMPTY`.
If the count of `EMPTY` cells in a line equals `lineLength - clue`, every other cell is `FILLED`.

**T2. Trivial extremes.**
If `clue == 0`: every cell in the line is `EMPTY`.
If `clue == lineLength`: every cell is `FILLED`.

**T3. Capacity bound.**
Let `k = clue`, `u = number of UNKNOWN cells in the line`, `f = number of FILLED so far`.
If `f + u == k`: every `UNKNOWN` in the line is `FILLED`.
If `f == k`: every `UNKNOWN` is `EMPTY` (same as T1 case 1).

T1, T2, T3 together cover the simple-total nonogram constraints. They are O(W·H) per sweep.

> **Honesty note.** Classic nonogram "overlap" / "glue" tactics rely on sequence-of-runs structure (knowing the blocks must be contiguous). Our single-total clue does NOT enforce contiguity per line, so those tactics do not apply directly. However, when combined with path constraints (degree, connectivity), runs of `FILLED` cells in a line become forced indirectly. See T7-T9 below.

### 2.2 Local path tactics

**T4. Endpoint degree.**
For `c ∈ {S, G}`:
- Exactly one of the (up to 4) incident edges is `USED`; the rest are `UNUSED`.
- If all but one edge are already `UNUSED`, the remaining edge is `USED`.
- If any edge is already `USED`, all other incident edges are `UNUSED`.

**T5. Filled-cell degree.**
For any `c` known `FILLED` with `c ∉ {S, G}`:
- Exactly two incident edges are `USED`; the rest are `UNUSED`.
- If exactly two incident edges are still `UNKNOWN` and the rest are `UNUSED`, both `UNKNOWN` edges are `USED`.
- If two incident edges are `USED`, all others are `UNUSED`.

**T6. Empty-cell degree.**
For any `c` known `EMPTY`: all incident edges are `UNUSED`.

**T7. Edge implies cell.**
If an incident edge `e_ab` is `USED`, both `a` and `b` are `FILLED`.
If a cell has any `USED` incident edge, it is `FILLED`.
Contrapositive: if a cell is `EMPTY`, all incident edges are `UNUSED` (= T6).

**T8. Forced unused edges from clue.**
For any cell `c`:
- If `c` is `FILLED ∧ c ∉ {S, G}`: at most 2 incident edges `USED`. If 2 are already `USED`, the rest become `UNUSED`.
- If `c` is `S` or `G`: at most 1 `USED`. If 1 is `USED`, others become `UNUSED`.
- For any `c`: the count of `UNUSED` incident edges plus `USED` incident edges is bounded by 4 minus its border-clipped neighbors. Useful at corners and edges of the grid.

**T9. No-premature-cycle.**
If adding an edge `e_ab` would close a path component into a cycle (i.e. `a` and `b` are both already on the same connected component of `USED` edges, and that component does not contain both `S` and `G` ending exactly at `a` and `b`), then `e_ab` must be `UNUSED`.

> *Note.* T9 is the IBA G4G8 "avoid premature short cycles" rule (`research/02_path_puzzles.md` §3.2). It's the key path-specific deduction. Implementation: maintain a union-find of cells joined by `USED` edges; before marking an edge `USED`, check if its endpoints are already in the same component.

**T10. No-isolated-island.**
A cell `c` that would have all incident edges `UNUSED` cannot be `FILLED` (degree would be 0). Therefore: if a cell currently `UNKNOWN` or `FILLED` has 3 incident `UNUSED` edges (or 2 at the grid border, etc.) and is not `S`/`G`, it must be `EMPTY` (or the puzzle is inconsistent if already `FILLED`).

**T11. Hint propagation.**
For each `Segment(sides)` hint at cell `c`:
- Mark `c` as `FILLED`.
- For each `d ∈ sides`: mark the incident edge in direction `d` as `USED`.
- For each in-grid `d ∉ sides`: mark the incident edge in direction `d` as `UNUSED`.

This runs once at initialization. T11 is excluded from tier-based difficulty accounting (it's puzzle setup, not a tactic the player exercises).

### 2.3 Cross-line and lookahead tactics

These were added after the v1 tactic set proved insufficient to discriminate among puzzles that were all "line-and-degree solvable but felt different to the player."

**T12. Cross-line saturation (relabel of T1/T3).**
A T1/T3 firing is **cross-line** when its triggering count includes at least one cell in the contributing state (FILLED for filled-saturation, EMPTY for empty-saturation) that was set by a perpendicular-axis T1/T3 deduction. Such firings are labelled `T12` instead of `T1*` / `T3*`. Implementation: `SolverState.cell_provenance` records the last tactic that set each cell; T1 and T3 consult that table when about to fire and decide between the single-line and cross-line label. The "strict" variant only considers cells in the **contributing state** for the specific saturation direction, not just any non-UNKNOWN cell in the line. See `tooling/src/rpn/tactics.py:_is_cross_line`.

**T14. Bounded contradiction (1-step lookahead).**
For each UNKNOWN cell, tentatively set it FILLED and run T1-T13 to fixed point. If contradiction → cell must be EMPTY. Symmetric for tentatively-EMPTY. Restores state via `SolverState.snapshot()/restore()`.

T14 is **gated**: it runs only after T1-T13 reach a fixed point with the puzzle still unsolved. The deduction main loop alternates between (a) running T1-T13 to fixed point and (b) one T14 sweep if needed, looping until T14 produces no new facts.

T14 excludes itself from inner-loop probes (single depth, no recursive contradictions).

### 2.4 Tier model (internal)

Each tactic tag is assigned a tier 1-4:

| Tier | Tactics | What it measures |
|---|---|---|
| 1 | T1r, T1c, T2, T3r, T3c, T4-T8 | Single-line saturation, local degree, trivial extremes. |
| 2 | T9, T10, T12 | Path-topology and cross-line reasoning. |
| 3 | (reserved) | Future edge/contiguity tactics. |
| 4 | T14 | 1-step lookahead. |

T11 and `init:*` are excluded.

The tier model is used internally to drive T14 escalation. It is **not** part of the difficulty score the player sees; the player-facing metric is `perceived_score` (see `design/02_generator.md` §2.6 and `tooling/src/rpn/metrics.py`).

### 2.5 Main loop

```
apply_hint_init(state)                    # T11
loop:
  run T1-T13 to fixed point               # the inner loop
  if state.is_solved(): break
  if T14.apply(state) made no progress: break
```

Termination: each tactic only flips state from `UNKNOWN` to known, never the reverse. The outer loop terminates because T14 either makes new facts (advancing the inner loop) or doesn't, in which case the solver is truly stalled.

## 3. SAT/CP backend (uniqueness validator)

Implemented with **Google OR-Tools CP-SAT** (Python). One model, two queries:

### 3.1 Variables

- `cell[c] ∈ {0, 1}`: whether cell `c` is `FILLED`. `cell[S] = cell[G] = 1`.
- `edge[e] ∈ {0, 1}`: whether edge `e` is `USED`.

### 3.2 Constraints

**Cell-edge link.** For each edge `e = (a, b)`: `edge[e] ≤ cell[a]` and `edge[e] ≤ cell[b]`. (A `USED` edge requires both endpoints `FILLED`.)

**Degree.**
- For `c ∈ {S, G}`: `sum(edge[e] for e incident to c) == cell[c]` and `cell[c] == 1`. So degree is exactly 1.
- For `c ∉ {S, G}`: `sum(edge[e] for e incident to c) == 2 * cell[c]`. So degree is 2 if `FILLED`, 0 if `EMPTY`.

**Row/column counts.**
- For each row `r`: `sum(cell[c] for c in row r) == row_counts[r]`.
- For each column: same.

**Single connected component.**
This is the hard one. Three options on the table:

1. **`AddCircuit` reformulation**: add a virtual edge `G → S` to close the path into a cycle, then express the whole thing as a Hamiltonian circuit on the FILLED cells. CP-SAT's `AddCircuit` does lazy subtour elimination internally. (Source: `research/03_solver_tooling.md` §3.3 point 4.)
2. **Spanning tree with depth labels**: for each `FILLED` cell `c`, integer `depth[c] ∈ [0, W·H]` with `depth[S] = 0`; for every `USED` edge `(a, b)`, `|depth[a] - depth[b]| = 1`. Forces a tree rooted at `S`. (Source: Knijff 2021 via `research/02_path_puzzles.md` §4.4.)
3. **Flow encoding**: inject 1 unit at `S`, demand at `G`, balance at every other cell. (Source: `research/02_path_puzzles.md` §4.5.)

> *Decision deferred to implementation*. Option 1 (`AddCircuit`) is most idiomatic for CP-SAT and gets lazy cuts for free. Option 2 is simpler to reason about and translates cleanly to other backends. We'll try option 1 first; if it doesn't behave well on our shape (only `FILLED` cells participate, the circuit needs to skip `EMPTY` cells via self-loops), we fall back to option 2. Will document the choice in code with a comment.

**Hints.** Each `Segment` hint fixes the corresponding `cell` and `edge` variables to 1 or 0.

### 3.3 Queries

**Query A: solve once.**
`solver.solve(model)` → `OPTIMAL` or `FEASIBLE` if a path exists; `INFEASIBLE` otherwise.

**Query B: uniqueness.**
1. Solve once, capture solution `σ`.
2. Add a blocking constraint forbidding exactly `σ` (in CP-SAT: an additional clause that at least one variable differs from its value in `σ`; standard recipe from `research/03_solver_tooling.md` §4.1).
3. Solve again. If `INFEASIBLE`, the puzzle has a unique solution. If `FEASIBLE`, it has at least two.

Alternative (faster on average): use `CpSolverSolutionCallback` with `enumerate_all_solutions = True`, set a callback that stops after the second solution. (Source: `research/03_solver_tooling.md` §1.5.)

> *Decision*: callback approach, capped at 2 solutions. Cleaner code and avoids re-solving with a blocking clause.

## 4. Solver public API

The Python module exposes:

```python
@dataclass(frozen=True)
class Puzzle:
    width: int
    height: int
    start: Cell
    goal: Cell
    row_counts: tuple[int, ...]   # length = height
    col_counts: tuple[int, ...]   # length = width
    hints: tuple[Hint, ...]       # frozen tuple

class DeductionSolver:
    def solve(self, puzzle: Puzzle) -> DeductionResult: ...
        # Result has: final_grid (with UNKNOWN cells if stalled),
        #             solved: bool,
        #             trace: list[TacticApplication]

class UniquenessChecker:
    def check(self, puzzle: Puzzle) -> UniquenessResult: ...
        # Result has: status ∈ {UNIQUE, MULTIPLE, INFEASIBLE},
        #             solution: Grid | None (the first one found),
        #             second_solution: Grid | None (only if MULTIPLE)
```

`DeductionResult.solved == True` is the green light for the generator. `UniquenessChecker.check(p).status == UNIQUE` is the safety check.

## 5. Test plan (v0)

Hand-craft a small set of puzzles to verify the solver before any generator code is written:

1. **5×5 empty puzzle**: row counts and col counts all 0; no hints; `S = (0,0)`, `G = (0,1)` adjacent. Expected: `path_length = 0` is infeasible since `S` and `G` are both `FILLED`. So this is a sanity check that the solver returns `INFEASIBLE`. (Or rejects at parse time.)
2. **5×5 trivial straight**: `S = (0,0)`, `G = (4,0)`, row 0 count = 5, all other rows = 0, all col counts = 1. Solution: straight path along row 0. Expected: deduction solver completes via T2 + T11; uniqueness UNIQUE.
3. **5×5 prototype level 1**: the puzzle in the HTML screenshot (row counts 2/2/3/5/3, col counts 5/5/2/1/2). Use the visible hints. Expected: solvable, unique, path length 14.
4. **Inconsistent puzzle**: same as (2) but row 0 count = 3. Expected: `INFEASIBLE` from CP-SAT, `stalled` or contradiction from deduction.
5. **Multi-solution puzzle**: deliberately omit enough hints from (3). Expected: deduction stalls, CP-SAT returns MULTIPLE.

Each test asserts:
- Deduction result matches expectation.
- CP-SAT uniqueness matches expectation.
- If both report a solution, they agree cell-by-cell.

## 6. What's deferred

- Pretty-printer for the trace (for debugging).
- Negative hints / "iced" clues.
- Non-rectangular boards.
- Parity tactics, deeper recursion (T15+ if ever needed).
- Performance optimization (we're targeting tens of milliseconds per small puzzle, well within reach for either implementation).

Difficulty rating is **done**: it lives in `tooling/src/rpn/metrics.py` and is documented in `design/02_generator.md` §2.6. It does not use tactic counts; it uses a player-walk simulation. See that doc for details.

## 7. Open questions surfaced by this design

- What happens if a deduction tactic and the SAT solver disagree (a deduction marks `EMPTY` but a SAT solution puts the path through it)? This would be a solver bug; we should fail loudly in tests. Worth a dedicated invariant check during the generator's accept step.

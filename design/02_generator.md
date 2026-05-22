# Generator Design (v0)

> Living design document. Updated as decisions evolve. Reads alongside `design/01_solver.md`.

## 0. Goal

Produce a set of puzzles such that every one satisfies:

1. Has a unique solution (CP-SAT verified).
2. Is fully solvable by the v1 deduction solver, using only the tactics in `design/01_solver.md` §2, no guessing, no nested contradictions.
3. Carries a difficulty signal computed from the solver's trace.

Output: a JSON file consumed by the KMP app at build time (puzzles ship bundled).

Constraints we accept:
- Generator runs offline on a developer machine. No on-device generation.
- Slow generation is fine. Minutes per puzzle pack is acceptable.

## 1. Pipeline overview

The standard "draw → derive → solve → validate" pattern, adapted to our path puzzle. Modeled on Tatham `pattern.c` (`research/01_nonogram.md` §9) and PuzzleMadness Numberlink (`research/02_path_puzzles.md` §1.3).

```
generate_puzzle(width, height, target_difficulty):
  loop:
    1. PLACE      S, G with random positions, min Manhattan distance.
    2. DRAW       a random simple path from S to G covering ~target_density cells.
    3. DERIVE     row/col counts directly from the path.
    4. HINT       start with full hints (every path cell gets its segment),
                  then progressively remove hints while puzzle stays deduction-solvable.
    5. VALIDATE   CP-SAT uniqueness check on the resulting puzzle.
    6. MEASURE    compute difficulty signal from the final deduction trace.
    7. ACCEPT     if difficulty within target band, emit puzzle; else retry or perturb.
```

Each step is independently testable. Failures in steps 4-7 cause a retry of the loop, not a crash.

## 2. Step details

### 2.1 PLACE: pick S and G

Input: grid dimensions `W × H`, optional target path length.

```
sc, sr = random_cell()
loop:
  gc, gr = random_cell()
  if (gc, gr) == (sc, sr): continue
  manhattan = |gc - sc| + |gr - sr|
  if manhattan >= max(W, H) // 2: break
return (sc, sr), (gc, gr)
```

The min-distance threshold keeps S and G visually separated. Tunable.

> *Open*: should S be in one half of the board and G in the other? Or completely independent? Going with independent + min-distance for now. Trivial to change.

### 2.2 DRAW: random simple path

Input: grid, S, G, target_density (fraction of cells to cover).

Output: an ordered list of cells from S to G, each adjacent to the next, no repeats.

**Approach: random self-avoiding walk with goal bias.**

```
path = [S]
visited = {S}
while path[-1] != G:
  current = path[-1]
  candidates = orthogonal_neighbors(current) - visited
  candidates = [c for c in candidates if can_still_reach_G(c, visited, G)]
  if not candidates:
    # dead-end; backtrack
    visited.remove(path.pop())
    if path is empty: return FAIL
    continue
  weights = goal_bias_weights(candidates, G, visited, target_density)
  next_cell = weighted_random_pick(candidates, weights)
  path.append(next_cell)
  visited.add(next_cell)
return path
```

Where:
- `can_still_reach_G`: cheap BFS/flood-fill on the unvisited cells; reject moves that disconnect from G.
- `goal_bias_weights`: when current path length is short relative to target, prefer moves that don't head toward G (keep exploring). When path length approaches target_density × W·H, prefer moves toward G.

> *Why not a simpler approach.* Pure self-avoiding random walks on a grid tend to get stuck or terminate too early. Bias + reachability check produces longer, varied paths reliably. This is essentially Warnsdorff-style heuristics (`research/02_path_puzzles.md` §3.5: Papadopoulos's "Number Trail" uses Warnsdorff's rule). We don't need full Warnsdorff here because we don't require Hamiltonicity, but the same idea (prefer constrained moves) applies.

> *Honesty note.* I have not verified by reading source that this exact heuristic produces well-distributed paths for our exact case. It's a sensible starting point; the test plan validates that we get paths of reasonable length and shape across many seeds. If results are bad, the alternative is to draw a Hamiltonian path on a sub-region (using IPS 1982's poly-time algorithm on rectangles, `research/02_path_puzzles.md` §5.2) and then erase a random "tail" of cells.

### 2.3 DERIVE: row/column counts

Trivial: count how many path cells lie in each row and each column. Identity: `sum(row_counts) == sum(col_counts) == len(path)`.

### 2.4 HINT: dig holes until barely solvable

This is the heart of the pipeline. We don't try to choose hints "smartly"; we use the same "dig holes" technique that Sudoku/nonogram generators use (Tatham `pattern.c`, HoDoKu, sudokuoftheday). The pattern: start dense, remove blindly, only keep removals that don't break solvability.

**Initial state.**
- For every cell on the path: attach the appropriate `Segment` hint (1-sided at S and G, 2-sided elsewhere, derived from the path's local shape at that cell).
- Run the deduction solver. If it fails to fully solve the puzzle even with full hints, something is very wrong. Assert in tests.

**Iteration.**
```
hints = compute_full_hints(path)
order = random_shuffle(list(hints))
for cell in order:
  candidate = hints.without(cell)
  result = DeductionSolver.solve(puzzle.with_hints(candidate))
  if result.solved:
    hints = candidate
return hints
```

Termination: when every remaining hint is "load-bearing", removing it leaves the puzzle deduction-unsolvable.

**Optimization (later, not v0).** Hints that are clearly forced by what's already deducible (e.g. a corner cell whose only two non-removed-hint neighbors force its shape) can be removed deterministically without solver invocation. Skip for now; the simple loop is fast enough on 5×5 to 15×15.

### 2.5 VALIDATE: CP-SAT uniqueness

Run `UniquenessChecker.check(puzzle)`. Three outcomes:
- `UNIQUE`: keep going.
- `MULTIPLE`: bug in deduction solver, or pathological puzzle. Abort puzzle, log diagnostics, retry generation loop.
- `INFEASIBLE`: same.

In principle, a deduction-solvable puzzle is uniquely solvable. This is a guard-rail.

### 2.6 MEASURE: player-experience difficulty

The deduction solver's tactic counts proved to be a poor difficulty proxy in playtesting: about a third of generated puzzles ended up in the wrong band when ranked by solver-tier-based scores. Path-puzzle difficulty depends on properties the deduction solver doesn't directly capture, in particular the *order* in which moves must be committed and how often the player faces a real choice vs an obvious next step.

The current metric, in `tooling/src/rpn/metrics.py`, walks the solution path simulating a player:

```
For each tip cell along the path:
  candidates = neighbors of tip that survive the "local rules":
    - not already drawn
    - row count + 1 <= row clue
    - col count + 1 <= col clue
    - if neighbor has a hint, hint's sides include the entry direction
    - G can only be entered as the final move
  hint-pull rule: if tip has a hint, the next move is fully committed.
  hint-pull rule: if any neighbor's hint commits the edge back to the tip,
                  the next move is forced (no decision).
  if |candidates| == 1: forced move.
  if |candidates| >= 2: DECISION POINT.
    For each wrong candidate, simulate committing to it and exploring
    further with the same local rules. Take the max depth reached before
    a dead-end (capped at TRAP_DEPTH_CAP = 5).
    weight = (n_candidates - 1) * (1 + max_trap_depth).
```

Per-puzzle metric:

```
n_decisions             = number of decision points along the path
total_decision_weight   = sum of weights
perceived_score = SIZE_WEIGHTS[(W, H)]
                + PATH_LENGTH_COEFF * path_length
                + DECISION_WEIGHT_COEFF * total_decision_weight

SIZE_WEIGHTS:     {5x5: 0, 7x7: 1000, 10x10: 2000}
PATH_LENGTH_COEFF:       5
DECISION_WEIGHT_COEFF:  15
```

Why this shape:

- **Size sets the band ceiling.** Reading 10x10 rows is fatiguing in a way 5x5 isn't, regardless of decision content. The user confirmed this with playtesting: "a 5x5 cannot be as hard as a 10x10 hard."
- **Decisions are weighted by branching + trap depth.** A 2-way fork where the wrong choice dies immediately (weight 2) is much easier than a 2-way fork where the wrong choice wanders 5 moves before dying (weight 10).
- **Path length is a small secondary term.** Within a size, longer paths feel slightly heavier.

The constants are calibrated empirically against the user's first playtest review of 50 mixed-size puzzles. Re-tune as more playtest data comes in.

The `DifficultySignal` written to the puzzle pack contains only player-experience fields:

```
DifficultySignal {
  hint_count, path_length, grid_size,
  n_decisions, decision_ratio, total_decision_weight,
  perceived_score,
  decisions: tuple of (step, n_candidates, max_trap_depth, weight)
}
```

The `decisions` array exists so the playtest viewer can highlight decision tiles for debug visualization (orange ring + weight badge, behind a toggle).

> *Why not the solver tactic counts.* The original difficulty score was the sum of weighted tactic firings, with cross-line and lookahead tactics weighted heaviest. It correlates poorly with perceived difficulty because the deduction solver chains many steps ahead and proves moves "forced" that a player at the table cannot see. The player-walk metric specifically captures what's *immediately obvious to a human applying local checks*, which is what the player actually experiences.

> *Tier model lives on internally.* The solver still tracks tactic tiers because T14 (lookahead) is gated to fire only after T1-T13 stall, and the tier system encodes that gate. But tier numbers are NOT part of the difficulty score the player sees and are NOT serialized into the pack JSON. See `design/01_solver.md` §2.4.

### 2.7 ACCEPT: filter by target difficulty band

If the caller specified a difficulty target band, drop puzzles outside it. If not, accept everything.

For v0: no banding. Generate a large corpus, eyeball it, then design the bucketing scheme from data. (Avoids premature curve design.)

## 3. Difficulty curve

The shipping curve is **4 bands × N levels per band, mixed sizes within a band**, ordered by `perceived_score`:

- Easy: mostly 5×5 with 0-5 weighted decisions.
- Medium: 5×5 with many decisions, transitioning to 7×7.
- Difficult: 7×7 with many decisions, transitioning to 10×10.
- Expert: 10×10 with many decisions and deep traps.

The 5-band scheme (with a "divinity" tier) was tried and dropped after playtesting confirmed that 5×5 grids can never be as hard as 10×10 hards: the path-puzzle "order of moves" property makes a 5×5 fundamentally less punishing than a 10×10. Four bands matches the user's mental model and Easybrain's Nonogram.com convention.

Generation strategy (`build-pack` command, see §7):

1. For each (band, size) combination, generate a pool of `per_difficulty × pool_multiplier` candidates with that band's constraints (clue restrictions, safe-endpoints, etc.).
2. Merge all candidates and sort by `perceived_score`.
3. The **last band** keeps its hard structural constraints: only candidates generated under those constraints are eligible. (Used to be "divinity"; today it's the most-constrained band, often `expert` with stricter rules.)
4. For all other bands, draw from the **global sorted pool**: each non-last band gets a contiguous slice of `per_difficulty` evenly-spaced candidates from the merged pool. This is the "hybrid" rule: high-hint puzzles still tend toward easy bands (because more hints reduce decisions), but a high-hint puzzle that turns out hard can land in a higher band based on score.

## 4. Public API

```python
@dataclass(frozen=True)
class DifficultySignal:
    hint_count: int
    path_length: int
    grid_size: tuple[int, int]
    n_decisions: int
    decision_ratio: float
    total_decision_weight: int
    # Per-decision detail: (step, n_candidates, max_trap_depth, weight).
    decisions: tuple[tuple[int, int, int, int], ...]
    perceived_score: float


@dataclass(frozen=True)
class GeneratedPuzzle:
    puzzle: Puzzle               # from model.py
    solution_path: tuple[Cell, ...]
    difficulty: DifficultySignal
    seed: int                    # reproducible regeneration


@dataclass(frozen=True)
class GeneratorConfig:
    width: int
    height: int
    target_density: float = 0.55
    min_sg_distance: int | None = None
    max_attempts: int = 100
    min_path_length: int | None = None    # defaults to max(W, H)
    target_hints: int | float | None = None   # int = absolute, float = fraction
    allowed_clue_values: frozenset[int] | None = None
    forbid_endpoint_auto_lines: bool = False
    require_diagonal_endpoints: bool = False


# Module-level entry point (no Generator class).
def generate(config: GeneratorConfig, seed: int) -> GeneratedPuzzle | None: ...
```

## 5. JSON output format

**Schema version 4.** One file per puzzle pack, e.g. `packs/mixed_5_7_10.json`:

```jsonc
{
  "version": 4,
  "pack_id": "5x5_7x7_10x10_multi",
  // Multi-band packs carry per-band metadata.
  "difficulties": [
    {"name": "easy",      "start_index": 0,  "hints_target": "n/a"},
    {"name": "medium",    "start_index": 12, "hints_target": "n/a"},
    {"name": "difficult", "start_index": 24, "hints_target": "n/a"},
    {"name": "expert",    "start_index": 36, "hints_target": "n/a"}
  ],
  "puzzles": [
    {
      "id": "5x5_001",
      "width": 5,
      "height": 5,
      "start": [4, 2],
      "goal":  [0, 4],
      "row_counts": [2, 2, 3, 5, 3],
      "col_counts": [5, 5, 2, 1, 2],
      "hints": [
        { "cell": [4, 2], "sides": ["S"] },
        { "cell": [1, 0], "sides": ["S", "W"] }
      ],
      "solution_path": [[4,2], [4,3], /* ... */ [0,4]],
      "difficulty": {
        "hint_count": 6,
        "path_length": 14,
        "n_decisions": 2,
        "decision_ratio": 0.154,
        "total_decision_weight": 7,
        "perceived_score": 175.0,
        // Per-decision detail used by the playtest viewer.
        // Each entry: [step, n_candidates, max_trap_depth, weight].
        // step is 1-indexed; tip cell = solution_path[step - 1].
        "decisions": [
          [4, 2, 1, 2],
          [7, 2, 4, 5]
        ]
      },
      "difficulty_name": "easy",
      "seed": 12345
    }
    /* more puzzles */
  ]
}
```

Notes on this format:
- `cell` is `[col, row]`, 0-indexed.
- `sides` uses single-letter `N`, `E`, `S`, `W` for compass directions.
- `solution_path` is shipped so the app's "Reveal solution" feature has no dependency on a runtime solver.
- `difficulty_name` is set by multi-band packs (`build-pack` CLI) and absent in single-band packs.
- `difficulty.decisions` is debug metadata for the playtest viewer; the shipping app can ignore it.

**Schema history:**
- v1: original. Solver tactic counts (`total_steps`, `line_tactic_steps`, `by_tactic`).
- v2: added solver-tier model (`max_tier`, `tier_count`, `tier_score`).
- v3: added player-experience metric (`n_decisions`, `perceived_score`) alongside the tier model.
- v4: removed all solver-perspective scores. Only player-experience fields remain. This is the current schema.

Old packs still load in the viewer (defensively-read fields default to "?" placeholders).

## 6. Test plan (v0)

In `tests/test_generator.py`:

1. **Reproducibility**: same seed → same puzzle. Compare JSON-serialized outputs.
2. **Validity invariants on every generated puzzle**:
   - `row_counts` and `col_counts` sum to the same value.
   - That value equals `len(solution_path)`.
   - `solution_path` starts at S, ends at G, has only orthogonal moves, no repeats.
   - Every hint references a cell on the solution path.
   - 1-sided hints only at S/G; 2-sided elsewhere.
3. **Solver round-trip**: feed the puzzle (without the solution path) to the deduction solver. It must fully solve. The result must match the solution_path.
4. **Uniqueness round-trip**: feed the puzzle to the CP-SAT uniqueness checker. Must return `UNIQUE`.
5. **Generator on the prototype puzzle**: use a fixed seed that we discover produces a 5×5 puzzle structurally similar to the HTML prototype (row counts 2/2/3/5/3, etc.). If our generator can produce *that exact puzzle* by luck, even better.
6. **No infinite loops**: every test runs with a generation time bound; assert we never exceed it.

## 7. CLI

Click-based CLI at `tooling/src/rpn/cli.py`. Run with `uv run python -m rpn.cli`.

```
# Single-band pack at one size.
$ uv run python -m rpn.cli new --width 5 --height 5 --count 10 --out packs/easy_5x5.json

# Multi-band pack across multiple sizes.
$ uv run python -m rpn.cli build-pack \
    --sizes 5,7,10 \
    --per-difficulty 10 \
    --pool-multiplier 8 \
    --difficulties "easy:6,medium:4,difficult:3,expert:2:2+3+4:safe-endpoints+diagonal-endpoints" \
    --out packs/mixed_5_7_10.json

# Restrict a specific band to certain sizes (e.g. only 5x5 + 7x7 for the hardest band).
$ uv run python -m rpn.cli build-pack \
    --sizes 5,7,10 \
    --band-sizes "expert=5+7" \
    --per-difficulty 10 \
    --out packs/mixed_5_7.json

# Pool sorted by score across a single size, no bands.
$ uv run python -m rpn.cli curve --width 5 --height 5 --count 20 --out packs/5x5_curve.json

# Print pack stats.
$ uv run python -m rpn.cli stats packs/mixed_5_7_10.json
```

The `difficulties` flag is `name:hints[:clues[:flags]]` per entry, comma-separated. `hints` is an int (absolute count) or float with `.` (fraction of path length). `clues` is `+`-separated allowed clue values. `flags` is `+`-separated from `safe-endpoints`, `diagonal-endpoints`.

`safe-endpoints` rejects candidates where some row or column has clue equal to the number of S/G endpoints it contains (such lines auto-complete trivially).

`diagonal-endpoints` rejects candidates where S and G share a row or column.

The global rule **clue == 0 is never allowed** is enforced by the generator regardless of `allowed_clue_values`.

## 8. What's deferred

- **Hint quality scoring**: do some hint choices make puzzles more elegant than others? Maybe later.
- **Per-difficulty hint density**: not separately tunable; emerges from the dig-holes loop plus the `target_hints` knob.
- **Path length target enforcement**: we have `target_density` but the random walk may overshoot/undershoot. Acceptable; we filter post-hoc.
- **Symmetry / aesthetics**: nonograms.com hand-curates puzzles that depict pictures. Out of scope.
- **Pack themes / level progression curves**: out of scope.
- **Negative hints, iced clues, multi-color extensions**: post-v1.
- **Refining `_explore_trap`**: currently it walks all surviving local-rules neighbors and takes the max trap depth. A real player would follow hint-pulled edges and not explore all branches. May slightly inflate trap depths for hint-dense puzzles. Revisit if a calibrated puzzle scores high but feels easy.

## 9. Open questions

Resolved (kept for traceability):

- ~~Path density~~: default 0.55. Tuned empirically over multiple pack regenerations.
- ~~Seed scope~~: fully deterministic per seed; required for reproducible test fixtures.
- ~~Max attempts exhausted~~: return `None`, let caller decide.
- ~~Difficulty bucketing~~: 4 bands ordered by `perceived_score`, hybrid pool selection. See §3.
- ~~clue == 0 globally banned~~: enforced in generator. clue == line_length still allowed (path can zigzag).

Still open:

- **Cross-puzzle diversity**: nothing in the current pipeline prevents two consecutive puzzles from looking identical. Batenburg et al. address this with a "previously generated" penalty (`research/01_nonogram.md` §6.2). Not yet observed as a problem at our pack sizes; revisit if duplicates become noticeable.
- **Calibration**: the constants in `metrics.py` (`SIZE_WEIGHTS`, `PATH_LENGTH_COEFF`, `DECISION_WEIGHT_COEFF`, `TRAP_DEPTH_CAP`) are calibrated against one user's playtest review of 50 puzzles. With broader playtesting (the user is family-testing now), some constants may need to shift.

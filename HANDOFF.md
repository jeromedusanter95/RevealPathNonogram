# Handoff Document

> Snapshot for resuming this project in a fresh Claude session. Read this top to bottom before doing anything.

## What this project is

A mobile puzzle game: trace a single path from S to G on a grid, constrained by row/column path-cell counts and visible segment hints inside the grid. Hybrid of nonogram (the count clues) and Numberlink/Flow Free (the path). See `GAME_CONTEXT.md` for the full pitch.

## Where to read first, in order

1. `CLAUDE.md` — project rules. **Read every line; they override defaults.** Key rules:
   - Never assume; cite every claim with proof.
   - When uncertain, ask the user; do not write speculative code.
   - No em dashes / en dashes / hyphens as punctuation.
2. `GAME_CONTEXT.md` — game spec, tech direction, what's locked, what's deferred.
3. `design/01_solver.md` — solver design (tactics, CP-SAT model, public API).
4. `design/02_generator.md` — generator design (pipeline, scoring, JSON output).
5. `research/01_nonogram.md`, `research/02_path_puzzles.md`, `research/03_solver_tooling.md` — literature surveys with citations. Reference only; consult when designing new tactics or scoring.

## Current state of the code

Located in `tooling/`. Python project managed with `uv`. Run tests with `cd tooling && uv run pytest`.

### What works (58 tests passing)

- **Data model** (`tooling/src/rpn/model.py`): `Puzzle`, `Cell`, `Direction`, `Segment` with full validation. Hints have 1 side at S/G, 2 sides elsewhere.
- **Working state** (`tooling/src/rpn/state.py`): tri-state cells (`UNKNOWN`/`FILLED`/`EMPTY`), tri-state edges (`UNKNOWN`/`USED`/`UNUSED`), union-find for cycle detection. `set_cell` and `set_edge` raise `Inconsistent` on contradiction. `snapshot/restore` supports T14 probe rollback. `cell_provenance` records which tactic last set each cell (used by T12 cross-line detection).
- **Deduction tactics T1-T14** (`tooling/src/rpn/tactics.py`):
  - T1: line saturation (single-line). Labels: `T1r` / `T1c` per axis. Cross-line relabel: see T12.
  - T2: trivial extremes (clue 0 or line_length).
  - T3: capacity bound (filled+unknown == clue). Labels: `T3r` / `T3c`.
  - T4: endpoint degree (S, G have degree 1).
  - T5: filled-cell degree (interior FILLED has degree 2).
  - T6: empty-cell degree (EMPTY has no incident USED edges).
  - T7: USED edge forces both endpoints FILLED.
  - T8: reserved (currently no-op).
  - T9: no-premature-cycle (forbid edges that would close a cycle).
  - T10: no-isolated-island (cell that can't reach required degree is EMPTY).
  - T11: hint propagation (applied once at init; excluded from tier accounting).
  - **T12: cross-line saturation** (relabel inside T1/T3). A line saturation is `T12` instead of `T1*`/`T3*` iff the saturating count includes cells set by T1/T3 on the perpendicular axis. The "strict" variant: only counts cells in the contributing state (FILLED for filled-saturation, EMPTY for empty-saturation).
  - **T14: bounded contradiction / 1-step lookahead.** Gated: runs only when T1-T13 reach a fixed point with the puzzle unsolved. For each UNKNOWN cell, tentatively set FILLED, run T1-T13 to fixed point; if contradiction, the cell is EMPTY. Symmetric for FILLED. Uses `state.snapshot()/state.restore()` for rollback. Excludes T14 itself from probes (single depth).
- **Tier model** (`tooling/src/rpn/deduction.py`): tactic tags → tier 1-4 mapping. **Used only internally** to decide when to escalate to T14. Exposed via `DeductionResult.max_tier` but NOT serialized into puzzle packs anymore (removed in JSON v4).
- **Deduction solver** (`tooling/src/rpn/deduction.py`): tactic-loop driver, returns `DeductionResult` with per-tactic histogram. Inner loop is T1-T13 to fixed point, then escalates to T14 once if stalled, then resumes inner loop. Repeats until truly stalled.
- **CP-SAT uniqueness checker** (`tooling/src/rpn/uniqueness.py`): cell + edge variables, degree constraints, row/col counts, hint constraints, spanning-tree-with-parent-pointers connectivity encoding (Knijff 2021 style). Uniqueness via blocking-clause technique.
- **Random walk** (`tooling/src/rpn/path_walk.py`): self-avoiding walk with goal-bias, reachability check at every step.
- **Player-experience metric** (`tooling/src/rpn/metrics.py`): walks the solution path simulating a human player. At each tip, applies **local rules** to enumerate surviving neighbors:
  - Not already drawn.
  - Doesn't exceed row/col clue.
  - If neighbor has a hint, hint's sides must include the entry direction.
  - Hint-pull rule: if any non-drawn neighbor has a hint committing the edge BACK to tip, that edge is forced USED and the player has no real choice.
  - Goal can only be entered on the final move.
  - Hint at the tip itself commits the exit (forced).
  
  Each "decision" (>1 surviving candidate) gets a **weight = (n_candidates - 1) × (1 + max_trap_depth)** where `max_trap_depth` is the deepest dead-end reachable from a wrong choice using the same local rules (capped at `TRAP_DEPTH_CAP = 5`).
  
  Primary score: `perceived_score = SIZE_WEIGHTS[(W, H)] + 5 × path_length + 15 × total_decision_weight`. Calibration constants in `metrics.py`.
- **Generator** (`tooling/src/rpn/generator.py`): `PLACE` → `DRAW` → `DERIVE` → `HINT` (dig holes) → `VALIDATE` → `MEASURE`. Returns `GeneratedPuzzle` with `DifficultySignal` (player-metric fields only; legacy tier_score and clue_ambiguity are gone).
  - Config flags: `target_density`, `min_path_length`, `target_hints` (int or float), `allowed_clue_values`, `forbid_endpoint_auto_lines`, `require_diagonal_endpoints`.
  - **Global rule**: rejects any candidate with `clue == 0` in any row or column. clue=line_length is allowed (path can zigzag through all cells, not trivial).
- **JSON output** (`tooling/src/rpn/pack.py`): `write_pack` at schema **version 4**. Difficulty block contains only player-experience metrics: `hint_count`, `path_length`, `n_decisions`, `decision_ratio`, `total_decision_weight`, `perceived_score`, `decisions` (per-decision list of `[step, n_candidates, trap_depth, weight]`).
- **CLI** (`tooling/src/rpn/cli.py`):
  - `new`: generate a single-band pack.
  - `build-pack`: multi-band pack with `--sizes A,B,C` (mixed sizes per band), `--band-sizes "divinity=5+7"` (per-band size restrictions), hybrid band assignment. Pool sorted by `perceived_score`; non-last bands picked from the global pool, last band restricted to its constrained sub-pool.
  - `curve`: generate a globally sorted pack, no bands.
  - `stats`: print pack stats.
- **HTML playtest viewer** (`tooling/playtest/index.html`):
  - Scales cell size: 60px at 5×5, ~50px at 7×7, ~40px at 10×10.
  - Level header shows `Level N (band, WxH)` and `K clues revealed · N decisions (weight W) · score S`.
  - **Help button**: 3 charges per grid, reveals a random non-endpoint path cell's hint glyph. Reset refunds charges; switching levels also resets.
  - **Show decisions** toggle: highlights decision tiles with an orange ring + weight badge for debugging score calibration.
  - **Show solution** toggle: draws the solution path overlay.

### Current packs

- `tooling/packs/mixed_5_7_10_rebanded.json` — 50 puzzles, 4 bands (easy/medium/difficult/expert), mixed sizes 5×5/7×7/10×10. Sorted globally by `perceived_score`, monotonic from 55 to 7280. Easy=mostly 5×5, Medium=5×5+7×7 with decisions, Difficult=7×7 with many decisions, Expert=10×10. Pack rebuilt locally from `mixed_5_7_10.json` source via the reband script (no regeneration needed for score changes).
- `tooling/packs/mixed_5_7_10.json` — original 50-puzzle pack with the pre-cleanup schema. Source for rebanding.
- `tooling/packs/5x5_multi.json`, `5x5_curve.json`, `easy_5x5.json`, `test_5x5.json` — earlier packs from the v0-v3 era. Schema version 1-3, contain obsolete `tier_score` / `score` fields. Kept as historical fixtures; not playtested.

### Difficulty score (current)

`tooling/src/rpn/metrics.py`:

```
perceived_score = SIZE_WEIGHTS[(W, H)]   # 5x5=0, 7x7=1000, 10x10=2000
              + 5 * path_length
              + 15 * total_decision_weight
```

`total_decision_weight = Σ (n_candidates - 1) × (1 + max_trap_depth)` over decision points.

A **decision** is a tip where 2+ neighbors pass the local-rules check. The **weight** combines branching width and how deep the wrong choices go before dead-ending.

Validated against the user's playtest review of `mixed_5_7_10.json`:
- The old solver-tier score got 18/50 levels miscategorised (36%).
- The new score puts easy = 5×5, medium = 5×5+7×7, difficult = 7×7+, expert = 10×10, matching the user's mental model.

### Player feedback so far (`mixed_5_7_10_rebanded.json`)

- Level 1: super easy ✓
- Level 2: correctly identifies "1 decision" matching the user's "I have 3 options" moment.
- Level 3: 2 decisions (one weight 2, one weight 5), matches user's "two real choices."
- Level 4: 1 decision after the hint-pull fix (the initial S move is now correctly marked forced because a neighbor's hint commits the edge back to S).

User playtesting the pack with family now.

## Architecture decisions made along the way

These are decisions to NOT revisit unless the user asks:

1. **No divinity band.** Five bands collapsed to four (easy/medium/difficult/expert) once the user observed that 5×5 grids can never be as hard as 10×10 hards, so a "ultimate" band tied to small sizes doesn't work.
2. **Size and difficulty are not independent.** Unlike Kakuro Conquest's 2D matrix (size × difficulty), this game ties bands roughly to size because the path-puzzle property (order of moves matters) makes a 5×5 fundamentally less hard than a 10×10.
3. **No clue == 0.** Globally rejected by the generator. clue == line_length is allowed.
4. **Player metric, not solver metric.** Difficulty is measured from the player's walk of the solution path with local rules, not from the deduction solver's tactic firings. Solver-perspective metrics (tier_score, clue_ambiguity, the original `difficulty_score` function) are gone from `DifficultySignal` and from JSON v4.
5. **Tier system kept inside the solver only.** The `TACTIC_TIERS` table still exists in `deduction.py` because the solver uses it to decide when to escalate to T14 (T14 is the only tier-4 tactic). The tier numbers do NOT appear in any user-facing JSON or UI.
6. **Hint-pull rule.** A non-drawn neighbor with a hint committing the edge back to the tip forces the move. This was added after the user pointed out that level 4 move 1 was misclassified as a decision when the visible hint at (3,0) clearly committed the edge to S.

## Risks and gotchas the next session should know

1. **`_explore_trap` doesn't apply the hint-pull rule.** When measuring how deep a wrong branch goes, it explores all surviving local-rules neighbors and takes the max depth. A real player would follow hint-pulled edges and not explore arbitrary branches. This may slightly inflate trap depths in puzzles with many hints in the wrong-branch region. Not yet observed to cause miscalibration; revisit if a puzzle scores high but feels easy.
2. **The CP-SAT uniqueness checker is slow on divinity 10×10 generation.** When generating the original 50-puzzle pack, divinity 7×7 took ~30 minutes due to constraint rejection rate. Divinity 10×10 was excluded from the spec. If a future band needs constrained 10×10 puzzles, expect long generation times.
3. **`mixed_5_7_10.json` is the canonical source.** The `_rebanded.json` is a re-scored copy. If the metric is ever changed again, the simplest path is to re-run `reband.py` on the source rather than regenerate.
4. **Calibration constants in `metrics.py` are not theoretical.** `SIZE_WEIGHTS`, `PATH_LENGTH_COEFF`, `DECISION_WEIGHT_COEFF`, `TRAP_DEPTH_CAP` are all fit by hand against the user's first playtest review. Re-tune as more playtest data comes in.
5. **The viewer assumes pack schema v4.** Older packs (`5x5_multi.json` etc.) still load because the viewer reads fields defensively, but the header/tooltips will show "?" placeholders where v4 fields are missing.

## What's not done

- KMP app scaffolding (deferred per `GAME_CONTEXT.md`).
- Bridges, portals, non-rectangular grids (post-v1 features in `GAME_CONTEXT.md`).
- Performance optimization beyond making the generator complete in reasonable time.
- Cross-platform UI work.
- Daily challenges / monetization / accounts.

## What the user might want next

After family playtesting:

- Adjust calibration constants if a band feels off.
- Generate a bigger pack (100+ puzzles) once the score feels right.
- Move to the KMP app shell.
- Add a level-select polish pass (current viewer is debug-grade).

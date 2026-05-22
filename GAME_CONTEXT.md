# Game Context (Living Spec)

> Status: draft. This document evolves as decisions are made. Update sections in place rather than appending revisions.

---

## 1. Working title

**TBD.** Folder name `RevealPathNonogram` is a placeholder. The HTML prototype uses "Path Finder" as a UI title but the final brand is undecided.

Naming should wait until the rules are locked. Candidates can come later.

## 2. One-line pitch

A grid puzzle game where you trace a single path from a start tile (S) to a goal tile (G), using nonogram-style row/column clues and revealed in-grid hints to deduce the unique solution.

## 3. Vision

### Inspiration

- **nonograms.com** — visual style, level grid, monetization (ads, daily puzzle), session length, "satisfying clean UI" feel. We deliberately mimic its presentation because it works and we don't want to spend design budget reinventing it.
- **Sudoku** — the idea that hints inside the grid (revealed tiles with directional arrows or path segments) constrain the solution, not just the edge clues.
- **Original prototype** — a "trace S to G, die on mistakes, retry from S" maze game. This evolved away from punish-and-retry toward pure logical deduction.

### Target audience

Same audience as nonograms.com / sudoku.com / wordscapes:
- Casual mobile players, broad age range, plays in short sessions (1 to 10 minutes).
- Enjoys logic puzzles, not reflex games.
- Tolerates ads in exchange for a free, large content library.

### Core loop

1. Pick a level from a numbered grid (1, 2, 3, ...).
2. Read the row/column clues and the revealed in-grid hints.
3. Tap or drag to extend a path from S, tile by tile.
4. Validate against clues. Adjust. Solve.
5. Celebration + unlock next level. Repeat.

### What makes it different from nonogram.com

In a classic nonogram, every cell is independent (filled or not) and clues describe runs of filled cells per row/column.

Here, **the filled cells must form a single connected path** from S to G, with no branches and no loops. That single rule changes everything:
- Each filled cell has exactly two path neighbors (except S and G, which have one).
- A row clue like "5" no longer just means "5 filled in this row in some pattern", it means "the path passes through 5 cells in this row, in any arrangement of sub-runs".
- Revealed in-grid hints (arrows, path segments) directly constrain the path's local shape.

The puzzle becomes a hybrid of nonogram deduction and maze tracing.

## 4. Game rules (v0, from the HTML prototype)

> These are the rules as observed in the current prototype. We'll refine them.

### Board

- Rectangular grid, size varies by difficulty (prototype shows 5x5; expect 5x5 up to ~15x15 or larger).
- Each cell is either **on the path** or **off the path**.

### Endpoints

- Exactly one **Start cell (S)** and one **Goal cell (G)**, placed by the puzzle author.
- Both are always on the path.

### Path properties

- The path is a single connected sequence of orthogonally adjacent cells (up/down/left/right, no diagonals).
- The path does not branch and does not cross itself.
- The path starts at S and ends at G.
- S has exactly one path neighbor, G has exactly one path neighbor, every other path cell has exactly two.

### Clues

- **Edge clues** (numbers above each column and to the left of each row): the total count of path cells in that row or column. Single number per row/column, not a sequence of runs.
- **Revealed in-grid hints** (visible from the start, the "8 arrow clues revealed" in the screenshot): pre-drawn path segments or arrows inside specific cells that the solution must contain. They reduce difficulty and guide deduction.

### Coverage

The path does NOT need to cover every cell. Sum of row counts (= sum of column counts = path length) may be strictly less than `width × height`. This keeps the puzzle close to nonogram spirit ("how many cells in this row are filled?") rather than Flow Free ("everything is filled").

### Win condition

The player's traced path exactly matches the unique solution path.

### Loss / mistake handling

In the prototype: no loss state. Player traces freely, can undo (click last tile), can reset, can reveal the solution. This is the casual-puzzle direction (no death, no timer pressure).

### UI affordances (from the prototype)

- Level picker (1 to 10 visible, presumably more).
- Step counter (`Steps: 0 / 14`) showing current path length vs. solution length.
- Solution button (reveals answer, presumably ad-gated or limited).
- Reset button.
- "New set" button (regenerates puzzles? or new pack?).
- Tooltip: "Click adjacent tiles to extend. Click last tile to undo."

## 5. Tech direction

### Decided

- **Platform**: Kotlin Multiplatform (KMP) + Compose Multiplatform.
- **Targets**: Android and iOS from day one.
- **UI feel**: native, like nonograms.com mobile apps.
- **Architecture**: MVVM + Clean Architecture, Koin for DI, repository pattern with interfaces in `domain/` and `Impl` in `data/`. See user's global CLAUDE.md for the full set of rules.

### Reasoning (short)

- User is a senior Android dev with prior KMP shipping experience, so Compose is the highest-leverage stack to read and review.
- Compose handles all required animations (tile fill, path tracing, mistake feedback, celebrations) trivially.
- Single codebase for Android and iOS, with Compose Multiplatform mature enough for a UI-driven puzzle game.
- Ad SDKs (AdMob, AppLovin) have known KMP integration paths via `expect`/`actual`.
- Godot was on the table (user has shipped 3 Godot apps) but overkill for a grid-based UI app and weaker on "native feel".

### Deferred

- Module layout (single `composeApp` vs split `core`/`game`/`ui`).
- Persistence (SQLDelight vs simple key-value vs file-backed JSON).
- Ads SDK choice (AdMob is most likely).
- Analytics.
- Localization scope.

### Offline tooling (generator + solver)

Decided after the literature review in `/research/`:

- **Language**: Python.
- **Constraint engine**: Google OR-Tools CP-SAT.
- **Why**: CP-SAT has built-in primitives for both halves of our puzzle: `AddAutomaton` for nonogram row/column clues, `AddCircuit` for the path (with internal lazy subtour cuts). Apache 2.0, state of the art on CP competitions, mature documentation. (See `research/03_solver_tooling.md` §1.5, §6.3.)
- **Output**: JSON puzzle files consumed by the KMP app at runtime.
- **Run location**: developer machine only. App never runs the generator.

### Pure-deduction policy

The generator only ships puzzles solvable by our human-style solver using a fixed set of tactics. The CP-SAT engine is used as a uniqueness validator and ground truth, not as a solving model. (Reference: Batenburg "simple class" pattern from `research/01_nonogram.md` §3.5, §6.1, §9.)

Current tactic set (see `design/01_solver.md` §2 for details):

- **Single-line nonogram tactics** (T1, T2, T3): line saturation, trivial extremes (clue 0 / line_length), capacity bound.
- **Local path tactics** (T4-T10): endpoint and filled-cell degree constraints, empty-cell degree, edge-implies-cell, no-premature-cycle, no-isolated-island.
- **Hint propagation** (T11): visible hints commit cell + edges at puzzle init.
- **Cross-line saturation** (T12): a T1/T3 firing whose triggering count includes cells set by perpendicular-axis T1/T3 deductions. Re-label, not a new pass.
- **Bounded contradiction** (T14): 1-step lookahead. For each UNKNOWN cell, tentatively assign; if running T1-T13 yields a contradiction, the opposite assignment is forced. Gated to run only after T1-T13 stall (single depth, no nested contradictions).

Each tactic firing is tagged so a tier (1-4) can be computed per puzzle. Tiers are used internally to gate T14 escalation. Difficulty is **not** scored from tiers; see "Difficulty metric" below.

### Difficulty metric

Solver-perspective tactic counts proved a poor predictor of perceived difficulty in playtest (a third of generated puzzles ended up in the wrong band). The shipping metric walks the solution path simulating a human player and counts **decision points**: moments where local rules (clue capacity, hint constraints, hint-pull from adjacent hints) leave more than one legal next move. Each decision is weighted by branching width and how deep the wrong choices go before dead-ending.

Per puzzle:

```
perceived_score = SIZE_WEIGHTS[(W, H)]
                + 5 * path_length
                + 15 * total_decision_weight
```

Calibration: `5×5 = 0`, `7×7 = 1000`, `10×10 = 2000`. Set so size dominates band boundaries while decisions order puzzles within a size. Constants are empirical from playtesting; see `design/02_generator.md` §2.6 and `tooling/src/rpn/metrics.py`.

### Band scheme

Four bands, ordered by `perceived_score`, mixed sizes within a band:

- **Easy**: 5×5 with few or shallow decisions.
- **Medium**: 5×5 with many decisions, transitioning to 7×7.
- **Difficult**: 7×7 with many decisions, transitioning to 10×10.
- **Expert**: 10×10 with many decisions and deep traps.

The "divinity" tier (5 bands) was tried and dropped. 5×5 grids cannot match the difficulty of 10×10 hards because the path-puzzle "order of moves matters" property limits how punishing a small grid can be.

## 6. Monetization

Mirroring nonograms.com:
- Free to play, ad-supported.
- Banner ads + interstitials between levels.
- Rewarded video to reveal solution / unlock hints.
- Optional one-time IAP to remove ads.

**Out of scope for v1.** Build the game first. Wire ads after the core loop is fun.

## 7. Out of scope (for now)

- Multiplayer / leaderboards / social.
- User-generated puzzles.
- Daily challenge calendar (likely later).
- Themes / cosmetics.
- Account system / cloud sync.

## 8. Open questions

Resolved (kept for traceability):

- ~~Clue format~~: single total per row/column. Locked.
- ~~Solver guarantee~~: every puzzle must be solvable by pure deduction with no guessing, and have exactly one solution. Validated by re-running the SAT/CP solver with a blocking clause for uniqueness. Locked.
- ~~Puzzle source~~: procedural generator only (offline). Hand authoring is out of scope; everything ships generated. Locked.
- ~~Difficulty curve~~: 4 bands by `perceived_score`, mixed sizes within a band. Metric: player-walk decision count weighted by branching and trap depth. See "Difficulty metric" above.
- ~~Cross-line and harder tactics~~: added (T12 cross-line, T14 lookahead). Used internally; not part of the player-facing score.
- ~~Mistake feedback~~: silent. Playtest viewer never validates user moves against the solution.
- ~~clue == 0 globally~~: banned by the generator (it lets the player decide a whole row instantly).

Still open:

1. **In-grid hint types**: just arrows (start direction) and straight/corner segments, or also negative hints ("this cell is NOT on the path")?
2. **Path input**: tap-to-extend only, drag-to-trace, or both? The playtest viewer is tap-to-extend; mobile may want drag.
3. **Naming and branding**: the actual product name.
4. **Help charges in shipping app**: the playtest viewer offers 3 charges per grid that reveal a random non-endpoint hint glyph. Should this be free, ad-rewarded, or capped per session?

## 9. Reference assets

- HTML prototype: shared as a screenshot in the initial conversation. Shows the visual target.
- nonograms.com / sudoku.com mobile apps: visual and monetization reference.
- `research/01_nonogram.md`: literature survey on classic nonogram solvers and generators. Tatham `pattern.c` is the cleanest reference for our simple-class generator pipeline.
- `research/02_path_puzzles.md`: literature survey on connected-path puzzles. IBA Monorail (Iba G4G8 paper) and Pathonogram are the closest commercial references.
- `research/03_solver_tooling.md`: literature survey on SAT/CSP tooling. OR-Tools CP-SAT chosen; `AddAutomaton` + `AddCircuit` are the two key primitives.
- GitHub `nonogram` topic page (https://github.com/topics/nonogram): index of open-source nonogram solvers in many languages. Use as a fallback if our line-solver implementation needs reference code or hard test cases. Top entries surveyed in `research/01_nonogram.md` §5.4 (HandsomeOne/Nonogram, Izaron/Nonograms, tsionyx/nonogrid, tsionyx/pynogram, pierre-dejoue/picross-solver).

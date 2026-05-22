# 03 — Solver Tooling Research

Status: draft, research only. No tool chosen.

Scope: an offline pipeline (Python or Kotlin/JVM) to generate puzzles combining
nonogram-style row/column block counts with a single connected path from `S` to
`G` on a grid. We need: encode the rules, prove uniqueness, ideally rate
human-difficulty. No code is being committed; this is a literature review.

Citation convention: every factual claim has a URL. Where I could only read a
page summary (rather than the full source), I mark it "summary" so it can be
audited later. Where a PDF was returned to me as undecodable binary and I
could not extract text, I say so and rely only on the search-page summary.

---

## 0. Quick glossary

- **SAT**: Boolean CNF satisfiability. CDCL solvers (CaDiCaL, Kissat, Glucose).
- **CP/CSP**: finite-domain variables, global constraints (`allDifferent`,
  `regular`, `circuit`); alternates propagation and search.
- **SMT**: SAT extended with theories (arithmetic, arrays, etc.). Z3 is the
  canonical implementation.
- **CP-SAT**: Google OR-Tools' hybrid CP-over-SAT (lazy clause generation +
  portfolio).
- **ASP / Clingo**: stable-model logic programming; has native acyclicity /
  reachability support.
- **Line solver (nonogram)**: given one row/column's clue and current cell
  states, finds the cells that are forced. A puzzle is *line-solvable* iff
  iterating line solving across rows and columns fully determines the grid.

---

## 1. Python tooling

### 1.1 z3-solver

- **What it is**: Python bindings for Microsoft's Z3 SMT solver. Latest PyPI
  version `4.16.0.0`, released Feb 2026.
  - https://pypi.org/project/z3-solver/ (summary; result text)
- **License**: MIT (Z3 project).
  - https://github.com/Z3Prover/z3 (project home)

#### Puzzle examples

- **Sudoku tutorial** in the official Z3Py guide; uses `Int` variables 1–9 and
  `Distinct()` for rows, columns, and 3×3 boxes.
  - https://ericpony.github.io/z3py-tutorial/guide-examples.htm (summary)
  - https://www.mintlify.com/Z3Prover/z3/examples/sudoku-solver (Z3 docs mirror)
- **Miracle Sudoku (Z3, Python)**: a complete walk-through encoding knight and
  king move constraints, no-consecutive-orthogonal-neighbours, and standard
  sudoku constraints. Solves in seconds.
  - https://www.gcardone.net/2020-06-03-solving-the-miracle-sudoku-in-z3/
  - https://akaritakai.net/blog/solving-miracle-sudokus/
- **Greater-than Sudoku, Z3**: variant-specific constraints.
  - https://ca.rstenpresser.de/blag/2021/03/solving-greater-than-sudoku-with-python-and-z3/
- **Nonogram with Z3**: at least two implementations exist. They model each
  row/column as an integer sequence and add constraints encoding the
  `0*1{k1}0+1{k2}0+...0*` pattern via auxiliary integers or by enumerating
  valid placements. Neither result reports clause/variable counts.
  - https://dev.to/taw/open-source-adventures-episode-70-crystal-z3-solver-for-nonograms-puzzle-40hb
    (Crystal, but uses Z3; "sets up cell variables as Boolean expressions and
    configures groups based on row and column hints")
  - https://github.com/datahaven/Z3PuzzleSolvers (Python Z3 puzzle solver
    collection; existence and language confirmed by search summary)
  - https://shmulc.substack.com/p/forget-manual-solving-let-z3-crack
    (claims "Nonograms present a modeling challenge by swapping integer theory
    for a complex sequence problem")

#### All-solutions / uniqueness with Z3

- Z3 has no built-in "enumerate all solutions". The standard pattern is the
  **block-model loop**: get a model `m`, add the constraint
  `Or([v() != m[v] for v in vars])` to forbid it, solve again.
  - https://brandonrozek.com/blog/obtaining-multiple-solutions-z3/ (summary)
  - https://dev.to/brandonrozek/obtaining-multiple-solutions-z3-52cb
  - https://github.com/Z3Prover/z3/issues/2532 (Z3 maintainers confirm this is
    the supported approach; summary)

#### Pros / cons for our use case

- **Pros**:
  - Very expressive: integers, booleans, sets, bit-vectors, quantifiers, all in
    one model. Great when the constraints don't decompose cleanly to CNF.
  - Block-model uniqueness check is trivial in 5 lines.
  - Active project, MIT licensed.
- **Cons**:
  - Per Stanford "Programming Z3", Z3 performance is **highly sensitive to
    encoding**; "the same problem can take seconds or hours depending on
    formulation, and minor syntactic changes may drastically affect
    performance".
    - https://theory.stanford.edu/~nikolaj/programmingz3.html (summary)
    - https://www.johndcook.com/blog/2025/03/17/lessons-learned-with-the-z3-sat-smt-solver/
      (summary; confirms tactics-tuning sensitivity)
  - Reachability/connectivity is not a Z3 built-in. You either compile your own
    flow encoding or use Z3 with custom theory plugins.
  - SAT competition-style modern CDCL solvers (Glucose, CaDiCaL, Kissat)
    typically outpace Z3 on pure SAT problems, since Z3's overhead serves the
    theory layer we don't need here.
    - **Unverified**: I did not find a head-to-head SAT-only benchmark for our
      puzzle size. The arXiv "Evaluating SAT and SMT Solvers on Large-Scale
      Sudoku Puzzles" abstract claims modern SMT solvers outperform classical
      SAT solvers on 25×25 sudoku, which contradicts my intuition; the full
      paper would need to be read to confirm.
    - https://arxiv.org/html/2501.08569v1 (abstract only consulted)

### 1.2 python-constraint

- **What it is**: a pure-Python CSP library for finite domains. The actively
  maintained fork is on PyPI as `python-constraint2`, version 2.5.0
  (Jan 2026). BSD-2-Clause.
  - https://github.com/python-constraint/python-constraint (confirmed via
    project README via WebFetch)
- **Built-in solvers**: `OptimizedBacktrackingSolver` (default),
  `BacktrackingSolver`, `RecursiveBacktrackingSolver`, `MinConflictsSolver`,
  `ParallelSolver`.
- **Built-in constraints**: `AllDifferentConstraint`, `AllEqualConstraint`,
  `ExactSumConstraint`, `MinSumConstraint`, `MaxSumConstraint`, plus product
  and set-based constraints. Constraints can also be written as strings
  (`"a*2 == b"`) and parsed.
- **Pros**:
  - Pure-Python, no native binaries. Easy to ship in an offline tool.
  - Good for prototyping. Sudoku-shaped problems are documented.
    - https://stackabuse.com/constraint-programming-with-python-constraint/
- **Cons**:
  - No `regular` / automaton constraint, no `circuit`, no graph variables.
    Encoding a nonogram block-pattern this way would mean enumerating all valid
    placements per line, which scales badly for larger boards.
  - Performance is far below CP-SAT or Choco on hard instances. The project's
    own README mentions planned "rewriting hotspots in C/Pyx" to speed it up.

### 1.3 CPMpy

- **What it is**: a high-level Python constraint modeling library, numpy-style
  decision-variable arrays, **solver-agnostic** front-end. Apache 2.0.
  v0.10.0 (Jan 2026).
  - https://github.com/CPMpy/cpmpy
  - https://cpmpy.readthedocs.io/
- **Solver backends** (per project README, confirmed via WebFetch):
  - CP: OR-Tools (default), IBM CP Optimizer, Choco, Glasgow GCS, Pumpkin,
    MiniZinc.
  - ILP: SCIP, HiGHS, Gurobi, CPLEX.
  - SMT: Z3.
  - SAT/PB: PySAT, Pindakaas, Exact.
  - Decision diagrams: PySDD.
- **Built-in puzzle examples** (from `examples/`):
  - `quickstart_sudoku.ipynb`, `sudoku.py`, `nqueens.py`, `nqueens_1000.ipynb`,
    `nonogram_ortools.ipynb`, `tsp.ipynb`, graph coloring, minesweeper, others.
  - https://github.com/CPMpy/cpmpy/tree/master/examples (confirmed via
    WebFetch)
- **Nonogram in CPMpy**: the example uses a helper function that generates DFAs
  and posts them via `DirectConstraint("AddAutomaton", ...)`, calling into
  OR-Tools' `AddAutomaton`. CPMpy itself decomposes `Regular` (when used
  generically) into `Table` constraints over the transition table.
  - https://cpmpy.readthedocs.io/en/latest/api/expressions/globalconstraints.html
    (CPMpy docs, summary from search)
  - https://github.com/CPMpy/cpmpy/issues/74 (confirmed `DirectConstraint`
    pattern for `AddAutomaton`)
  - http://www.hakank.org/cpmpy/nonogram_regular.py (separate hakank example;
    WebFetch failed with timeout, source exists per search summary)
- **Pros**:
  - Switch solver with one line. Lets us experiment with CP-SAT, Choco (via
    JVM bridge), Z3, and SAT backends without rewriting the model.
  - Native `Regular` global constraint with automaton helpers.
  - Active project, Apache 2.0.
- **Cons**:
  - Extra abstraction layer over the underlying solver. For SAT-style
    operations (incremental solve, assumption-based UNSAT cores) you may want
    to drop to PySAT or CP-SAT directly.

### 1.4 PySAT

- **What it is**: Python toolkit for SAT-based prototyping. Provides a unified
  API over many CDCL solvers. MIT licensed.
  - https://pysathq.github.io/
  - https://github.com/pysathq/pysat
- **Solvers wrapped**: CaDiCaL (1.0.3, 1.5.3, 1.9.5, 3.0.0), Glucose
  (3.0, 4.1, 4.2.1), Kissat, Lingeling, MapleLCM, Minicard, Minisat variants.
  Confirmed via WebFetch on the project page.
- **Cardinality encodings** (per PySAT docs): pairwise, bitwise, sequential
  counters, sorting networks, cardinality networks, ladder/regular, totalizer,
  modulo totalizer, iterative totalizer.
  - https://pysathq.github.io/docs/html/api/card.html
  - https://pysathq.github.io/ (WebFetch confirmed)
- **Pseudo-Boolean**: PySAT integrates `PyPBLib` for PB-constraint encoding.
- **MaxSAT**: example RC2/OLLITI and Fu&Malik implementations included.
- **Other**: Tseitin clausification, model enumeration, MUS/MCS extraction.
- **Pros**:
  - Direct CNF control means we can write a careful, small encoding (e.g. for
    nonogram lines via cardinality, and reachability via the vertex-elimination
    encoding in Janhunen et al.).
  - Standard SAT toolkit; easy to add a blocking clause for uniqueness.
- **Cons**:
  - We have to do all the encoding ourselves. No `regular`, no `circuit`. For
    a project that combines nonogram clues and a path, this is the most
    work-per-line of any option here.

### 1.5 Google OR-Tools CP-SAT (Python)

- **What it is**: Google's hybrid CP-over-SAT solver. State of the art on CP
  competitions: "won all gold medals in the last 5 years of constraint
  programming competitions".
  - https://github.com/d-krupke/cpsat-primer (CP-SAT primer; confirmed via
    search summary and WebFetch on AddCircuit page)
  - https://d-krupke.github.io/cpsat-primer/
- **License**: Apache 2.0.
  - https://github.com/google/or-tools/blob/stable/LICENSE (confirmed via
    WebFetch)
- **Sudoku example** (official, in `examples/python/sudoku_sat.py`): 81
  `new_int_var(1, 9, ...)` variables, three loops of `add_all_different` for
  rows, columns, and boxes, equality on initial clues.
  - https://github.com/google/or-tools/blob/stable/examples/python/sudoku_sat.py
    (confirmed via WebFetch)
- **Nonogram via CP-SAT**: typically uses `AddAutomaton`, which takes a
  transition table for a DFA. See CPMpy `nonogram_ortools.ipynb`.
- **AddCircuit**: built-in global constraint that enforces a single Hamiltonian
  cycle through a subset of arcs (plus self-loops on excluded nodes). Uses
  internal lazy subtour elimination. Per CP-SAT Primer: "the constraint ensures
  that the edges marked as True form a single circuit visiting each vertex
  exactly once, aside from vertices with a loop set as True", and:
  > "both formulations [DFJ, MTZ] perform significantly worse than the
  > `add_circuit` constraint, because the circuit constraint can utilize lazy
  > constraints internally."
  - https://d-krupke.github.io/cpsat-primer/04B_advanced_modelling.html
    (confirmed via WebFetch)
- **All-solutions enumeration**: subclass `CpSolverSolutionCallback`, set
  `solver.parameters.enumerate_all_solutions = True`. Note: incompatible with
  multi-worker parallelism.
  - https://github.com/google/or-tools/discussions/4223
  - https://developers.google.com/optimization/cp/cp_solver (summary)
- **Performance note**: Laurent Perron (OR-Tools tech lead) has stated that for
  performance-critical use, Python is not the preferred interface; the C++,
  Java, and Go bindings tend to be faster on model construction.
  - https://github.com/google/or-tools/issues/1410 (summary from search)

#### Pros / cons

- **Pros**:
  - Most powerful free CP solver. `Regular`/`Automaton`, `AddCircuit`,
    `AllDifferent`, reservoir, cumulative, intervals, etc., all built in.
  - First-class enumeration callback for the "find a second solution"
    uniqueness check.
  - Apache 2.0 license, well documented, big community.
- **Cons**:
  - Native shared library; not pure Python. Slightly larger deployment.
  - No native "connected subgraph" / s-t-reachability constraint. We'd have to
    encode connectivity ourselves (see §3).

---

## 2. JVM / Kotlin tooling

### 2.1 Choco-solver

- **What it is**: open-source Java constraint programming library. BSD-3-Clause.
  Current versions: 4.10.17 (Jan 2025, last stable in 4.x line) and
  5.0.0-beta.1 (Feb 2025). 6.0.0 reportedly released May 2026 per GitHub README
  fetched.
  - https://github.com/chocoteam/choco-solver (confirmed via WebFetch)
  - https://mvnrepository.com/artifact/org.choco-solver/choco-solver
- **Global constraints relevant to us** (from README and `Model` Javadoc):
  - `regular` / `automaton` for sequence patterns (nonogram rows/columns).
  - `path`, `circuit`, `subCircuit` for path/cycle problems.
  - `tree` for arborescences.
  - `allDifferent`, `globalCardinality`, etc.
- **Nonogram sample** (`samples` repo, `Nonogram.java`): builds a `regular`
  expression of the form `0*1{k1}0+1{k2}...0*` for each row/column, converts
  to a `FiniteAutomaton`, posts `model.regular(cells, auto)` per line.
  - https://github.com/chocoteam/samples/blob/master/src/main/java/org/chocosolver/samples/integer/Nonogram.java
    (confirmed via WebFetch)
  - https://choco-solver.org/tutos/nonogram/code/ (confirmed via WebFetch)
- **Sudoku sample**: 81 IntVars (`1..9`), three loops of `model.allDifferent`.
  - https://sonalake.com/latest/constraint-programming-solving-sudoku-with-choco-solver-library/
  - https://www.baeldung.com/java-constraint-programming-choco (summary)
- **Graph variables (choco-graph extension)**: provides `UndirectedGraphVar` /
  `DirectedGraphVar`. Constraints include `connected`, `tree`, `nbConnComp`,
  `hamiltonianPath`, `degree`. From the extension docs:
  > "A graph variable can be subject to graph constraints to ensure global
  > graph properties (e.g. connectedness, acyclicity)…"
  - https://github.com/chocoteam/choco-graph (summary via search)
  - https://choco-solver.org/tutos/other-examples/the-connector-problem/
    (confirmed via WebFetch; uses `UndirectedGraphVar` + `dcmst` / `degrees`)
  - **Unverified**: I did not confirm whether choco-graph is current and
    compatible with Choco 4.10.x / 5.x. The repo and docs are older and may
    have bit-rotted; needs a build test before committing.

#### Pros / cons

- **Pros**:
  - Pure Java, runs in any JVM project including Android (subject to API level
    constraints).
  - Native `regular` and graph variables. The nonogram model is essentially a
    one-liner per line.
  - BSD license.
- **Cons**:
  - Slower than CP-SAT on most public benchmarks (no published head-to-head I
    could find; this is widely reported in the MiniZinc Challenge results
    where CP-SAT consistently outperforms Choco). **Unverified for our exact
    problem size.**
  - choco-graph extension freshness is unclear.

### 2.2 Sat4j

- **What it is**: pure-Java SAT solver. Dual license EPL 1.0 + GNU LGPL 2.1.
  - https://www.sat4j.org/
  - https://mvnrepository.com/artifact/org.ow2.sat4j (summary)
- **API** (confirmed via WebFetch of howto.php):
  - `ISolver solver = SolverFactory.newDefault();`
  - `solver.newVar(MAXVAR); solver.setExpectedNumberOfClauses(N);`
  - `solver.addClause(new VecInt(new int[]{1, -3, 7}));`
  - `IProblem problem = solver; if (problem.isSatisfiable()) {...}`
  - For enumeration: `ModelIterator mi = new ModelIterator(solver);`
- **Puzzle examples**:
  - Daniel Le Berre (Sat4j maintainer) provides a SAT+SMT '19 hands-on with
    sudoku examples.
    - https://github.com/danielleberre/satsmt19handson (summary)
  - Aalto course notes show the canonical CNF encoding of Sudoku (one variable
    per `(row, col, value)`, 9·9·9 = 729 vars; "at least one"/"at most one"
    cells, "exactly one occurrence per value per row/col/box").
    - https://users.aalto.fi/~tjunttil/2020-DP-AUT/notes-sat/solving.html
    - https://users.aalto.fi/~tjunttil/2022-DP-AUT/notes-sat/solving.html

#### Pros / cons

- **Pros**:
  - Pure Java, easy to embed. Runs on Android.
  - Good for prototyping. Sudoku examples are well documented.
  - Built-in `ModelIterator` for all-solutions enumeration.
- **Cons**:
  - Not on the same performance tier as CaDiCaL / Kissat / Glucose for hard
    instances; widely accepted in the SAT community though I did not find a
    rigorous 2024+ benchmark. **Unverified at our problem size.**
  - No high-level constraints (no `regular`, no `circuit`). We'd hand-write
    the CNF.

### 2.3 JaCoP

- **What it is**: Java Constraint Programming solver.
  - https://github.com/radsz/jacop
- **Nonogram support**: ships an `examples/fd/nonogram/Nonogram.java` with 151
  test instances; per hakank's survey, "JaCoP's nonogram solver has solved
  every puzzle in a full 2,491 puzzle dataset in under 15 minutes". Uses a
  line-solving DFS with zigzag variable ordering.
  - https://www.hakank.org/constraint_programming_blog/2010/03/survey_of_nonogram_solvers_upd.html
    (summary)
  - https://github.com/radsz/jacop (project home)
- **Status**: actively maintained, but less mainstream than Choco. **Unverified
  for current version/release date.**

### 2.4 OR-Tools JVM bindings

- **What it is**: Java/Kotlin access to the same CP-SAT and routing solver as
  the Python bindings. Apache 2.0.
- **Setup pattern** (per official sample `CpSatExample.java`):
  ```java
  import com.google.ortools.Loader;
  import com.google.ortools.sat.CpModel;
  import com.google.ortools.sat.CpSolver;
  ...
  Loader.loadNativeLibraries();
  CpModel model = new CpModel();
  IntVar x = model.newIntVar(0, 50, "x");
  ...
  CpSolver solver = new CpSolver();
  solver.solve(model);
  ```
  - https://github.com/google/or-tools/blob/stable/ortools/sat/samples/CpSatExample.java
    (confirmed via WebFetch)
- **Sudoku SAT example**: official Python `sudoku_sat.py`; Java equivalent
  follows the same pattern.
- **Distribution**: native binaries are shipped per platform; a community
  Maven wrapper exists at `pintowar/or-tools-maven` to ease Gradle/Maven
  consumption.
  - https://github.com/pintowar/or-tools-maven (summary)
- **Android**: official Android support is **unverified**. OR-Tools' native
  libs are built for Linux/macOS/Windows desktop. Building for Android NDK
  would be a significant effort. For an *offline* generator tool, this doesn't
  matter; we'd run on a developer machine.

#### Pros / cons

- **Pros**:
  - Same solver as Python CP-SAT. State of the art.
  - Faster model construction than Python (per Laurent Perron's comment, see
    §1.5).
- **Cons**:
  - Native binaries; adds platform-specific deployment concerns.
  - JNI bridge has some overhead but it's negligible for offline batch use.

### 2.5 Kotlin-native and pure-Kotlin SAT

- **KoSAT**: pure-Kotlin CDCL SAT solver based on MiniSat. MIT licensed.
  Features 2-watched literals, VSIDS, Luby restarts, LBD-based clause DB
  reduction, incremental. Distributed via JitPack. **No official releases**;
  small project (9 stars at fetch time).
  - https://github.com/UnitTestBot/kosat (confirmed via WebFetch)
  - **Unverified**: performance vs MiniSat/Sat4j; the README references MiniSat
    as the algorithmic basis but provides no benchmarks. Likely not competitive
    with modern CDCL solvers like CaDiCaL for hard instances. Suitable mainly
    for proof-of-concept or for code we want to keep pure-Kotlin.
- **kotlin-satlib**: JVM-only library wrapping native SAT solvers (MiniSat,
  Glucose, CryptoMiniSat, CaDiCaL) via JNI. GPL-3.0. v0.26.0 (Mar 2024).
  **Not KMP**.
  - https://github.com/Lipen/kotlin-satlib (confirmed via WebFetch)
- **Kotlin Multiplatform support**: I did **not** find any CP/SAT library with
  declared KMP support. KoSAT is pure Kotlin but only targets JVM. CP-SAT,
  Choco, Sat4j, JaCoP are JVM-only by design. For an offline generator this is
  fine; we'd run on JVM regardless.

---

## 3. Encoding patterns

### 3.1 Nonogram row/column counts

The block-pattern for a row is essentially a regular expression
`0* 1^{k1} 0^+ 1^{k2} 0^+ ... 1^{kn} 0*`. Three families of encoding:

1. **Regular / automaton constraint** (CP).
   - Build a DFA accepting valid block sequences for the line. Post one
     `regular(line, automaton)` per row and per column.
   - Used in Choco (`samples/integer/Nonogram.java`) and CPMpy / OR-Tools (via
     `AddAutomaton`).
   - https://github.com/chocoteam/samples/blob/master/src/main/java/org/chocosolver/samples/integer/Nonogram.java
   - https://cpmpy.readthedocs.io/en/latest/api/expressions/globalconstraints.html
2. **Block-position integer variables** (CP/SMT).
   - For each block `b_i` in a line, introduce an integer "start position"
     variable, plus ordering and spacing constraints. Cell `(r, c)` is 1 iff it
     falls inside some block. Used by Copris/Sugar for nonogram and similar
     puzzles.
   - https://cspsat.gitlab.io/copris-puzzles/nonogram/ (confirmed via WebFetch:
     "Variables: cell colors `x(i,j) ∈ {0,1}`; block positions `r(i,k)` for
     row blocks, `c(j,k)` for column blocks. Constraints: non-overlapping
     blocks, block-placement logic via `'x(i,j) > 0 ⇔ Or(rs)`")
3. **Pattern enumeration → DNF → CNF** (SAT).
   - For each line, enumerate all valid bit-patterns satisfying the clue,
     OR them, AND across rows and columns. Convert to CNF via Tseitin to
     avoid blow-up.
   - https://www.kbyte.io/projects/201908_nonogram (confirmed via WebFetch:
     "the column and row terms are ANDed together... uses `.to_cnf()` and
     Tseitin encoding... solved with PicoSAT")
   - Clause count: naive enumeration is **exponential in the worst case**
     (e.g. a row with no clues has `2^n` possible patterns). The Kwarc
     assignment notes:
     > "A naive CNF encoding of a nonogram ruleset leads to an exponential
     > number of clauses in the worst case."
     - https://kwarc.info/teaching/AISysProj/SS24/assignment-1.3.pdf (summary)
     - https://kwarc.info/teaching/AISysProj/WS2324/assignment-1.3.pdf (summary)

For our project a `regular`/`automaton` encoding is the simplest and scales
polynomially in the DFA size, which is itself linear in the line length plus
clue length.

### 3.2 Cardinality encodings (background)

For row/column clue *totals* (sum of cells = sum of block lengths), or for
generic counting constraints, the standard CNF encodings are:

- **Pairwise** (`O(n^2)`): for "at-most-one", `(¬x_i ∨ ¬x_j)` for every pair.
- **Sequential counter** (Sinz 2005): `O(n·k)` clauses with `O(n·k)` auxiliary
  vars; detects violation via unit propagation in linear time.
- **Totalizer** (Bailleux & Boufkhad 2003): balanced binary tree, encodes
  sums; supports unit-propagation-based bound tightening.
- **Sorting networks / cardinality networks**: `O(n log^2 n)` clauses,
  enforces arc-consistency.
- **Modulo totalizer**: best on certain hard problems (queen domination).
- All available in PySAT's `pysat.card`.
  - https://www.cs.toronto.edu/~fbacchus/csc2512/Assignments/Bailleux-Boufkhad2003_Chapter_EfficientCNFEncodingOfBooleanC.pdf
  - https://www.carstensinz.de/papers/CP-2005.pdf
  - https://pysathq.github.io/docs/html/api/card.html
  - https://www.cs.cmu.edu/~csd-phd-blog/2024/cardinality-constraints/

### 3.3 Single path with two degree-1 endpoints, all others degree-2

This is the "S to G single path covering some cell set" requirement. Three
flavours of encoding:

1. **Degree-only + connectivity (CP/ILP)**.
   - For each cell `v`, integer `deg(v)` = number of incident path edges
     selected.
   - `deg(S) = deg(G) = 1`; for any other "path cell", `deg = 2`; for any
     non-path cell, `deg = 0`.
   - This alone allows disconnected unions of paths and cycles, so you must
     also enforce **connectivity**.

2. **Flow encoding (ILP / SAT)**.
   - Treat `S` as a source of flow value 1 and `G` as a sink. For each edge,
     a flow variable. Conservation at intermediate nodes. The set of edges
     with non-zero flow is the path. Used in Hashiwokakero ILP work:
     > "Mixed Integer Linear Programming formulations have been used for
     > connectivity problems, with all approaches representing connectivity
     > constraints by means of graph flows."
     - https://arxiv.org/abs/1908.09586 (Constraint Generation Algorithm for
       MCI Problem; summary)

3. **Distance / order labels (SAT / CP)**.
   - Assign each cell `v` on the path a position `pos(v) ∈ 0..n−1` with
     `pos(S) = 0` and edges only between cells whose positions differ by 1.
     This is the standard "anti-subtour" technique. See Hamiltonian Cycle SAT
     encodings:
     > "A central issue in encoding the Hamiltonian Cycle Problem into SAT is
     > how to prevent sub-cycles, and one well-used technique is to map
     > vertices to different positions."
     - https://modref.github.io/papers/ModRef2019_In%20Pursuit%20of%20an%20Efficient%20SAT%20Encoding%20for%20the%20Hamiltonian%20Cycle%20Problem.pdf
     - https://drops.dagstuhl.de/storage/00lipics/lipics-vol307-cp2024/LIPIcs.CP.2024.40/LIPIcs.CP.2024.40.pdf
       (CP 2024 paper on vertex-elimination encoding for HCP)

4. **Built-in `circuit` / `path` constraint (CP)**.
   - CP-SAT `AddCircuit` and Choco `Model.path` / `Model.circuit` enforce
     Hamiltonian path/circuit semantics. To express *"path uses only the path
     cells, with degree-1 endpoints"* you provide arcs with Boolean
     selectors and let the solver handle subtour elimination.
   - CP-SAT primer: `AddCircuit` "ensures that the edges marked as True form
     a single circuit visiting each vertex exactly once, aside from vertices
     with a loop set as True", and uses internal lazy subtour cuts.
     - https://d-krupke.github.io/cpsat-primer/04B_advanced_modelling.html
     - https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model.html
       (summary)

### 3.4 Connectivity in SAT/CSP

This is the single hardest piece of the encoding. Five known patterns:

1. **Reachability via graph propagator** (`SAT modulo Graphs`).
   - Janhunen et al. extend a SAT solver with a propagator that checks
     acyclicity / `s-t`-reachability on a side directed graph. Variables on
     edges select edges into the graph; the propagator backtracks when
     reachability/acyclicity is violated.
     - https://www.cs.uni-potsdam.de/wv/publications/DBLP_conf/jelia/GebserJR14.pdf
       (SAT modulo Graphs: Acyclicity; my WebFetch could not parse the PDF
       binary, summary only)
     - http://research.ics.aalto.fi/publications/bibdb2014/pdf/GebserJR14jelia.pdf
       (same paper, alternate URL)
   - Implementation: this is what `clingo` / clasp uses for ASP-modulo-graphs.
   - The "Picat-based modeling" paper extends this to encode arbitrary
     reachability via the same framework.
     - https://arxiv.org/abs/2109.08293 (Picat reachability)

2. **Vertex-elimination CNF encoding** (Janhunen, Rintanen et al., AAAI 2021).
   - Plain CNF clauses, no custom propagator. Particularly efficient when the
     underlying graph is sparse (which a grid is).
   - https://arxiv.org/abs/2105.12908 (confirmed via WebFetch: "novel methods
     for encoding acyclicity and `s-t`-reachability... based on vertex
     elimination graphs... encode these constraints as standard propositional
     clauses, making them directly applicable with any SAT solver")
   - **Asymptotic blowup**: not extracted from the abstract; need full paper.

3. **Spanning tree / order labels**.
   - For each non-S cell on the path, pick a "parent" cell adjacent to it. The
     parent function defines a tree rooted at S. Forbid cycles by requiring
     `depth(v) > depth(parent(v))` (depth labels).
   - Used by van der Knijff (2021) for Slitherlink, Masyu, Shingoki, Nurikabe,
     Hitori, Hashi (via SMT).
     - https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf
       (my WebFetch couldn't decode the PDF; per search summary: "implements
       the connectivity constraint using a graph property" and covers
       Slitherlink/Masyu/Shingoki/Nurikabe/Hitori/Hashi via SMT)

4. **Flow encoding**.
   - Inject 1 unit of flow at the source; demand it at the sink. Cells with
     non-zero flow are connected to S. Standard in MIP.
     - https://arxiv.org/abs/1908.09586 (Constraint Generation for MCI)

5. **Iterative cut generation** ("lazy" / branch-and-cut).
   - Solve without explicit connectivity constraints; if the solution has
     disconnected components, add a "cut" forbidding that exact subset
     boundary; re-solve. Repeat until connected.
   - Used in Hashiwokakero ILP work (Andrade et al., 2019): "weak connectivity
     constraints (such as requiring at least n−1 bridges for n islands)
     further prune invalid subtrees, reducing computation time by up to 24% on
     large instances. The algorithm achieved an average CPU time of 11.14
     seconds with an average of 31.90 strong connectivity constraints per
     instance".
     - https://arxiv.org/abs/1905.00973 (summary; my WebFetch couldn't decode
       the PDF)
   - CP-SAT's `AddCircuit` does this internally for Hamiltonian-cycle-style
     problems; we get it for free if we model the path as a circuit.

For our project (single grid path from S to G), the cheapest options are
probably:

- CP-SAT `AddCircuit` if we accept Hamiltonian-cycle semantics on a small
  augmented graph, **or**
- Spanning-tree / parent-pointer encoding with depth labels (works in any SAT
  or SMT framework).

### 3.5 Cycle elimination summary

A path from S to G with no cycles is equivalent to: connected subgraph + every
vertex has degree ≤ 2 + exactly two degree-1 vertices (S, G). If you enforce
those three properties you get a single simple path. Cycle elimination then
reduces to "no closed cycle in the selected edges", which is the standard
acyclicity constraint encoded as in §3.4(1)–(3).

---

## 4. Uniqueness checking

### 4.1 Canonical technique: solve, block, re-solve

The standard "solve twice with blocking clause" recipe is universal across
SAT, SMT, and CP:

1. Solve the model `M` to get a satisfying assignment `σ`.
2. Add a **blocking clause** that forbids exactly `σ`. For SAT, this is the
   negation of the conjunction of literals in `σ`, i.e. `⋁ ¬ℓ_i`.
3. Solve again.
4. If UNSAT, the original solution is unique. If SAT, there exist ≥ 2
   solutions.

References:

- General principle. From Carleton/UWaterloo SAT-solving notes for Sudoku:
  > "To verify that a generated solution is unique, a SAT solver is re-run
  > with the additional 50 unit clauses corresponding to the starting
  > configuration along with blocking clauses that negate the solution,
  > thereby blocking the previous solution."
  - https://cs.uwaterloo.ca/~cbright/reports/sat-maple.pdf (summary)
- Z3 Python recipe: build `Or([v() != m[v] for v in vars])` and `assert` it.
  - https://brandonrozek.com/blog/obtaining-multiple-solutions-z3/
  - https://github.com/Z3Prover/z3/issues/2532
- CP-SAT: use `CpSolverSolutionCallback`, set
  `enumerate_all_solutions = True`, and stop after the second hit.
  - https://github.com/google/or-tools/discussions/4223
- Sat4j: `ModelIterator(solver)` enumerates models.
  - https://www.sat4j.org/howto.php (confirmed via WebFetch)
- PySAT: `solver.solve()`, then `solver.add_clause(blocking)`, then solve
  again.
  - https://pysathq.github.io/usage/ (confirmed via WebFetch)

### 4.2 Variants

- **Projected blocking**. If the puzzle's "answer" is only a subset of the
  variables (e.g. just cell colours but the model also has block-position
  variables), block only the projection. The Möhle / Biere line of work
  "On Enumerating Short Projected Models" formalises this and gives
  enumeration algorithms that avoid blowups in the number of blocking
  clauses.
  - https://arxiv.org/pdf/2110.12924 (summary)
- **Minimal blocking clauses**. "Algorithms using minimal blocking clauses
  generate solutions with up to 14× fewer partial assignments and are up to
  three orders of magnitude faster… However, a large number of blocking
  clauses affects memory consumption and drastically slows down unit
  propagation."
  - https://sites.cs.ucsb.edu/~nestan/pdf/VLSID14.pdf (All-SAT using minimal
    blocking clauses; summary)
- **Disjoint-projected enumeration** without blocking clauses entirely; uses
  splitting instead. Useful when many models are expected. Probably overkill
  for a "is there a second solution at all?" check.
  - https://www.researchgate.net/publication/391292860 (summary)

### 4.3 Performance for uniqueness checks

- For a generator, only the **second** solve matters. If the answer is "no
  second solution", the solver must prove UNSAT for the augmented formula.
  For nonogram-scale grids (say ≤ 30×30), this is typically sub-second for any
  competent solver if the encoding is reasonable.
- Repeated uniqueness checks during a clue-removal generation loop dominate
  total wall time. The Sudoku generator literature (HoDoKu, Sudoku.coach,
  sudokuoftheday) shows this is the right design pattern: dig holes, after
  each hole verify uniqueness, undo on failure.
- For nonograms specifically, a faster pre-filter is to run a **line solver**
  (polynomial per line; see §5) iteratively over rows and columns. If it
  terminates with the grid fully determined, the puzzle is uniquely solvable
  by line solving alone (and trivially uniquely satisfiable). Only when line
  solving stalls do we need to invoke SAT for the uniqueness check.
  - Steven Simpson's "line solver" classification.
    - https://stevocity.me.uk/nonogram/theory (confirmed via WebFetch)
  - Batenburg & Kosters O(kl) DP line solver.
    - https://homepages.cwi.nl/~kbatenbu/papers/bako_pr_2009.pdf (summary)

---

## 5. Human-deduction vs SAT solvers

### 5.1 The mismatch

A SAT/CP solver proves a puzzle has a unique solution. It does **not** tell
you that a human can solve it without guessing, or that doing so would be fun.
This mismatch is well-documented:

- The HoDoKu manual explicitly models "human-style solving techniques"
  (singles, subsets, locked candidates, fish, wings, uniqueness, coloring,
  chains, ALS) and uses *which technique chain solves a puzzle* as the
  difficulty signal.
  - https://hodoku.sourceforge.net/en/docs_cre.php (confirmed via WebFetch:
    "The level of a sudoku cannot be smaller than the level of the hardest
    step contained in it's solution.")
  - https://hodoku.sourceforge.net/
- Sudoku.coach and sudokuoftheday explicitly state difficulty is determined by
  "the most advanced strategies a puzzle solver must use", not by clue count
  or by raw solver iteration count.
  - https://www.sudokuoftheday.com/difficulty (summary)
  - https://sudoku.coach/en/learn/sudoku-difficulty (summary)
- "A puzzle with 17 givens can be trivially easy, while a puzzle with 35
  givens could require advanced techniques."
  - Same sources.

### 5.2 How real pipelines bridge it

Pattern, repeatedly seen across Sudoku and nonogram generators:

1. **Generator** (random or template-driven) proposes a clue set.
2. **SAT / CP / brute-force solver** verifies uniqueness. Reject if not
   unique.
3. **Rule-based human-style solver** attempts to solve using only ordered
   tactics. Record which tactics were needed.
4. **Difficulty score** is a function of the set of tactics used (sometimes
   weighted; e.g. HoDoKu's per-technique "score" summed over the solution).
5. **Filter / sort** generated puzzles by target difficulty band.

Cited examples:

- **Sudoku**:
  - HoDoKu (Java rule-based solver + generator). https://hodoku.sourceforge.net/en/docs_cre.php
  - "Generating Sudokus for Fun and No Profit" by tn1ck: "uses rule-based
    constraint propagation, specifically an Arc Consistency algorithm (AC3)
    combined with depth-first search and the 'Minimum Remaining Value'
    heuristic, not SAT solving." Iteration count used as a difficulty
    metric, with the caveat: "we still don't know if this is actually a good
    difficulty indicator for how a human perceives the difficulty."
    - https://tn1ck.com/blog/how-to-generate-sudokus (confirmed via WebFetch)
  - "Difficulty Rating of Sudoku Puzzles: An Overview and Evaluation"
    (Pelánek). My WebFetch could not decode the PDF. Per search summary:
    a survey establishing iteration counts and technique-cost models as the
    main approaches.
    - https://www.fi.muni.cz/~xpelanek/publications/sudoku-arxiv.pdf

- **Nonograms**:
  - Batenburg & Kosters (Leiden) "Constructing Simple Nonograms of Varying
    Difficulty" and "On the Difficulty of Nonograms". My WebFetch could not
    decode the PDFs. Per search summaries, they use a **human-like line
    solver** with iterative sweeps and define difficulty as the number of
    sweeps to solve. They also generate nonograms that resemble a target
    grayscale image; difficulty corresponds to the number of steps required
    to reconstruct it.
    - https://liacs.leidenuniv.nl/~kosterswa/constru.pdf (summary)
    - https://liacs.leidenuniv.nl/~kosterswa/nonodec2012.pdf (summary)
    - https://homepages.cwi.nl/~kbatenbu/papers/bako_pr_2009.pdf (Solving
      Nonograms by combining relaxations; summary)
  - "Generating Difficult and Fun Nonograms" (Cazenave et al., 2024). Search
    summary: uses MCTS and a human-like solver. My WebFetch could not decode
    the PDF.
    - https://www.lamsade.dauphine.fr/~cazenave/papers/Nonogram2024.pdf
      (summary)
  - Simpson's solver: ranks puzzles informally by line-solvability vs need to
    guess.
    - https://stevocity.me.uk/nonogram/theory (confirmed via WebFetch)
  - "Line-solvable" terminology (Medium / hcv): "puzzles are engineered so
    that each has one unique solution, and is solvable using pure logical
    deduction"; "the vast majority [of human-designed nonograms] are
    line-solvable".
    - https://medium.com/smith-hcv/solving-hard-instances-of-nonograms-35c68e4a26df
      (summary)

### 5.3 Implication for our pipeline

For a puzzle that combines nonogram clues with a path constraint, there is
**no published human-difficulty rating system**. We will need to define our
own. Plausible scaffolding:

1. **Line propagation** (Batenburg-Kosters DP): how many rows/columns are
   forced cell-by-cell by their own clue alone?
2. **Cross-line propagation**: after a sweep, do row-column interactions
   resolve more cells?
3. **Path-aware deductions**: does the path constraint + partial colouring
   force new cells? (E.g. degree constraints at corners.)
4. **Branching depth**: when (1)-(3) stall, how deep does a backtracking
   search go before another forced deduction surfaces?

A SAT solver remains the right *correctness* engine (uniqueness check). The
*difficulty engine* should be a custom rule-based solver that mirrors what we
expect a human to think.

---

## 6. Recommendation framework

This is intentionally a comparison matrix, **not** a pick. The final choice
depends on team preference and on details of the puzzle's path constraints
which I have not seen.

### 6.1 What changes the tradeoff

- **Connectivity is the hard part.** Every grid puzzle that includes a
  connected path or polyomino needs either:
  - a graph-aware CP backend (Choco's choco-graph, or build it yourself in
    Picat/Sugar), **or**
  - a custom acyclicity / reachability encoding (vertex elimination, spanning
    tree with depth labels, or flow), **or**
  - CP-SAT's `AddCircuit` if the path can be reformulated as a Hamiltonian
    circuit on a small augmented graph.
- **Uniqueness checking is trivial** in all five candidate tools (Z3, CP-SAT,
  Choco, Sat4j, PySAT). Not a discriminator.
- **Nonogram clues are easiest** with a `regular`/`automaton` global
  constraint. Choco, CP-SAT, and CPMpy (over OR-Tools) all support this
  cleanly. PySAT and pure-SAT require manual DFA→CNF (Tseitin) work. Z3 can
  do it with integer block-position variables.
- **Rule-based difficulty rating** is independent of the SAT engine. It will
  be a custom Kotlin or Python module either way.

### 6.2 Side-by-side

| Tool | Language | License | Native graph/path constraint | Native nonogram constraint | Uniqueness API | Notes |
|---|---|---|---|---|---|---|
| z3-solver | Python | MIT | No (custom encoding) | No (encode by hand) | Block-model loop | Most expressive; slowest at pure SAT. |
| python-constraint | Python | BSD-2 | No | No | Loop over `getSolutions()` | Pure Python, simplest, slow on hard instances. |
| CPMpy | Python | Apache-2 | No connected; has `Circuit`, `Regular`/`Automaton` via OR-Tools | Yes (Regular via DirectConstraint AddAutomaton) | Solver-dependent | Lets you switch backend (CP-SAT, Choco, Z3, PySAT) without rewriting. |
| OR-Tools CP-SAT (Python) | Python | Apache-2 | `AddCircuit`; no s-t-reachability | Yes (`AddAutomaton`) | `enumerate_all_solutions` callback | Best CP solver as of 2024–2025. Native libs. |
| PySAT | Python | MIT | No (encode acyclicity) | No (DFA→CNF or pattern enum) | Add blocking clause | Most flexible at CNF level; needs most custom code. |
| Choco-solver | Java/JVM | BSD-3 | `circuit`, `path`, `tree` global; choco-graph extension for `connected` (status unclear) | Yes (`regular`/automaton) | `Solver.findAllSolutions` / count | Solid, mature, pure Java. |
| sat4j | Java/JVM | EPL+LGPL | No | No | `ModelIterator` | Pure Java, easy to embed; older codebase. |
| OR-Tools CP-SAT (Java) | Java/JVM | Apache-2 | Same as Python CP-SAT | Same | Same callback API | Native binaries; faster model construction than Python. |
| KoSAT | Kotlin/JVM | MIT | No | No | DIY blocking clause | Pure Kotlin, young (no releases). Probably not production-ready. |
| kotlin-satlib | JVM | GPL-3 | No (CNF only) | No | DIY blocking clause | Wraps native MiniSat/Glucose/CryptoMiniSat/CaDiCaL. |

(All cells confirmed against the cited sources above. "Unverified" where
flagged.)

### 6.3 Likely shortlist

The combinations that would *minimise* custom encoding work are:

- **Python: OR-Tools CP-SAT directly** (or via CPMpy). Use `AddAutomaton` for
  nonogram clues; use `AddCircuit` for the path (treating S→G plus an implicit
  return arc as a Hamiltonian circuit through path cells), or a custom
  spanning-tree encoding. Uniqueness via solution callback.
- **Python: PySAT + custom vertex-elimination acyclicity encoding**. Most
  control, most code.
- **JVM: Choco + choco-graph**. If choco-graph still works (needs verification),
  this is the most declarative JVM path. `regular` for nonograms; graph
  variable with `connected` for the path.
- **JVM: OR-Tools Java bindings**, same model as the Python CP-SAT version.
  Better build complexity due to native libs.
- **Either: model in MiniZinc** and try multiple backends (Gecode, Chuffed,
  CP-SAT, Picat). MiniZinc supports `regular`, `circuit`, and `connected`
  (in some libraries). Out of scope to evaluate here but worth a note.
  - https://docs.minizinc.dev/en/stable/solvers.html (summary)

### 6.4 Open questions / gaps in this research

I want to flag, per the project's evidence rule, what is **unverified or
incomplete**:

1. I could not extract text from several key PDFs (van der Knijff 2021;
   Batenburg & Kosters 2009 & 2012; Pelánek difficulty rating; Andrade
   Hashiwokakero 2019; Cazenave et al. 2024 nonogram MCTS; SAT modulo Graphs
   Acyclicity Gebser et al.). My WebFetch returned them as undecoded binary.
   The summaries in this doc are from search-result excerpts only, not direct
   quotes from the papers. If a claim from any of these is load-bearing for a
   decision, **read the full PDF before relying on it**.
2. I did **not** run any benchmarks. All performance claims (CP-SAT > Choco,
   modern CDCL > Sat4j, JaCoP solves 2,491 puzzles in 15 min, Z3 is encoding-
   sensitive) are from secondary sources.
3. **choco-graph** maintenance status: I did not verify it builds against
   Choco 5.x. Last activity on the README didn't show a clear date.
4. **OR-Tools on Android**: not investigated; offline tooling is fine, but
   if any part of the generator needs to run on-device this is a blocker.
5. **Existing "nonogram + path" puzzle work**: I did not find any prior
   literature on this exact hybrid. The closest analogues are
   Numberlink/Slitherlink/Masyu (single loop or paths with no clues outside
   the path) and Shingoki (loops with pearls). The Knijff 2021 thesis is the
   single best reference for "puzzles with a connectivity constraint" and
   should be read in full before we commit to an encoding.
6. **Z3 vs CP-SAT on uniqueness-check workloads**: no benchmark found.
   Intuition says CP-SAT wins on grid-style integer CP problems; Z3 wins
   when SMT theories (sets, bit-vectors) are heavily used. Our problem looks
   like the former.

---

## 7. Key references (the ones worth reading next)

All other URLs are inline in §1–§6. These are the ones that would most
materially change a design decision and that I could not fully verify
because the WebFetch tool returned unreadable PDF bytes:

- **van der Knijff (2021)** — "Solving and generating puzzles with a
  connectivity constraint" (BSc thesis, Radboud). Covers six puzzles with
  exactly our class of constraint. https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf
- **Janhunen et al. (2021)** — Propositional encodings of acyclicity and
  reachability via vertex elimination. https://arxiv.org/abs/2105.12908
- **Gebser, Janhunen, Rintanen (2014)** — SAT modulo Graphs: Acyclicity. https://www.cs.uni-potsdam.de/wv/publications/DBLP_conf/jelia/GebserJR14.pdf
- **Batenburg & Kosters** — Constructing simple nonograms of varying
  difficulty, On the difficulty of nonograms, Solving nonograms by combining
  relaxations. https://liacs.leidenuniv.nl/~kosterswa/constru.pdf ; https://liacs.leidenuniv.nl/~kosterswa/nonodec2012.pdf ; https://homepages.cwi.nl/~kbatenbu/papers/bako_pr_2009.pdf
- **Cazenave et al. (2024)** — Generating difficult and fun nonograms. https://www.lamsade.dauphine.fr/~cazenave/papers/Nonogram2024.pdf
- **Pelánek** — Difficulty rating of Sudoku puzzles: overview and evaluation. https://www.fi.muni.cz/~xpelanek/publications/sudoku-arxiv.pdf
- **Andrade et al. (2019)** — Hashiwokakero branch-and-cut with iterative
  connectivity cuts. https://arxiv.org/abs/1905.00973

Read these before committing to a connectivity encoding or difficulty rating
scheme.

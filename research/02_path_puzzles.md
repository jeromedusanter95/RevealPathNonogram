# 02 Path Puzzles Research

> Research-only document. Every claim must cite a URL (or be explicitly labeled "Unverified").
> Project rule (`/Users/jeromedusanter/Sources/Games/RevealPathNonogram/CLAUDE.md`): no assumptions, every claim has a source, "I couldn't verify this" is acceptable.

This document covers connected-path puzzle research relevant to our game:
a single connected, non-branching, non-crossing path from S to G on a grid,
with row/column path-cell counts and revealed in-grid hints.

Scope:
1. Numberlink and Flow Free.
2. Slitherlink, Masyu, Hashi.
3. The single-path-plus-row/column-counts intersection (Conceptis Monorail, Round Trip, Grand Tour, Pathonogram, etc.).
4. Path representation in solvers.
5. Hamiltonian path and TSP relevance.

---

## 1. Numberlink and Flow Free

### 1.1 What the puzzles are

**Numberlink** is a Nikoli-published Japanese pencil puzzle. The Wikipedia article on
Numberlink says players "must connect matching number pairs using continuous paths
that cannot branch, cross, or have numbers in the middle" and that "a well-designed
puzzle has a unique solution with all grid cells filled, though some designers omit
this requirement. Some versions prohibit U-turns to prevent path-shortening."
Source: Wikipedia, Numberlink — <https://en.wikipedia.org/wiki/Numberlink>.

The same article traces early forms back to Sam Loyd's 1897 *Brooklyn Daily Eagle*
column and Henry Dudeney's 1917 *Amusements in Mathematics*, and notes the puzzle
"gained popularity in Japan through Nikoli under the names Arukone (using letters)
and Nanbarinku (using numbers)." Modern digital variants listed include "Wire Storm,
Flow Free, and Alphabet Connection across iOS, Android, Web, and Windows platforms."
Source: <https://en.wikipedia.org/wiki/Numberlink>.

**Flow Free** is a mobile game by Big Duck Games LLC, released June 2012 for iOS and
Android. The Wikipedia article on Flow Free states: "Flow Free presents numberlink
puzzles," that "the objective is to connect dots of the same color by drawing 'pipes'
between them so that the entire grid is occupied by pipes," and that pipes may not
intersect. As of 2022 the original game had "received more than 100 million downloads."
Source: Wikipedia, Flow Free — <https://en.wikipedia.org/wiki/Flow_Free>.

Big Duck Games' own site describes the puzzle as "connect matching colors with pipe to
create a Flow, and pair all colors while covering the entire board to solve each puzzle.
Pipes will break if they cross or overlap." Source:
<https://www.bigduckgames.com/flowfree>.

So **the standard Flow Free rule does require covering every cell**. Our puzzle is the
single-pair (only one S/G) variant of "Zig-Zag Numberlink" (the cover-all-cells version,
see §1.4).

### 1.2 Algorithms used in the wild

The Flow Free / Numberlink solving literature shows several distinct approaches.

**Backtracking with constraint propagation and pruning.**
PuzzleMadness publishes their generator pipeline. Their solver "evolved" through
iterative refinement, uses "a classic backtracking algorithm" that continues searching
after finding a solution to detect uniqueness, and the final code is "1600+ lines."
Source: <https://puzzlemadness.co.uk/howwemakenumberlink/>.

The most-starred OSS Numberlink solver, `thomasahle/numberlink` (Go, 101 stars at the time
of the GitHub fetch), is also backtracking-based: it uses "a dual representation based on
link corners" and "optimistic validation," and fills along SW-diagonals rather than starting
from sources. It solves the complete 270-puzzle set from janko.at in 0.14s and handles
40x40 instances. It explicitly **does not validate uniqueness**: "You can't use numberlink
for checking if a puzzle is unique... numberlink will assume the puzzle has just one solution."
Source: <https://github.com/thomasahle/numberlink>.

Matt Zucker's well-known C-language Flow Free solver uses best-first search with a priority
queue over puzzle states, restricting moves to a single "active color" to drop branching
from up to 24 to 4 directional moves. Validity checks are ordered by speed: dead-end detection,
stranded colors / regions (connected component labeling), chokepoint detection. Forced moves
are chained using a stack allocator, then the whole chain is rolled back if invalidated. He
reports sub-second times on all puzzles he tested, worst case `jumbo_14x14_30` at 1.558s
with 130,734 nodes. Source: <https://mzucker.github.io/2016/08/28/flow-solver.html>.

Zucker's follow-up post explicitly weighs custom solvers vs SAT and concludes the boundary
is closer than he expected. He quotes: "if your best choice for a problem is 'reduce to SAT',
maybe find a new problem?" but acknowledges this is a personal preference, not a benchmark
result. Source: <https://mzucker.github.io/2016/08/28/flow-solver.html>.

**SAT / CSP formulations.**
Torvaney's Clojure-based Flow Free solver translates the puzzle to SAT via the
`rolling-stones` library (an interface to `sat4j`). The encoding is edge-color:
"For each edge in the graph and each color available, a boolean variable represents
whether that edge carries that color." Constraints: each edge has exactly one color;
non-terminal cells have exactly two same-color edges; terminal cells have exactly one.
Source: <https://torvaney.github.io/projects/flow-solver.html>.

The Copris (Scala-embedded constraint DSL) Numberlink solver uses a different formulation:
binary edge variables `e(cell, cell1)` plus integer cell-label variables `x(cell)`, with
constraints `(e(cell, cell1) === 1) ==> (x(cell) === x(cell1))` and per-cell degree
constraints. With Sugar plus GlueMiniSat as the SAT backend, it solves 278 of 281 test
instances in under 3600s, with average 7.8s CPU time.
Source: <https://cspsat.gitlab.io/copris-puzzles/numberlink/index.html>.

`Huy1711/Numberlink-solver-SAT4J` uses cell-direction variables instead of edge variables:
"`Xij,k` variables where each cell (i, j) has four directional options: LEFT (1), RIGHT
(2), UP (3), DOWN (4)." Numbered cells have exactly one direction active; blank cells
exactly two; and reflexivity constraints enforce that if cell (i, j) points left, the
left neighbor points right. SAT4J in Java.
Source: <https://github.com/Huy1711/Numberlink-solver-SAT4J>.

`uguryavuz/numberlink-solver` (5 stars) uses Google's OR-Tools CP-SAT solver in Python.
The README notes it "may end up creating free-standing loops" (i.e. it doesn't yet
forbid disjoint cycles), and it assumes the puzzle has a unique solution.
Source: <https://github.com/uguryavuz/numberlink-solver>.

**ILP / MIP formulations.**
The "Yet Another Math Programming Consultant" blog post on Numberlink presents both a
non-convex MIQCP model (Baron, ~23s) and a linearized MIP (Cplex, 0.36s) using auxiliary
variables for products of binaries. Variables are `x_{p,k} = 1` if cell p has value k.
Counting constraints: number cells have exactly 1 neighboring cell with matching value;
interior cells have exactly 2. The author notes "for larger instances, SAT solvers are
reportedly more suitable than MIP solvers."
Source: <http://yetanothermathprogrammingconsultant.blogspot.com/2017/09/numberlink-models.html>.

The sysid blog reproduces this with Pyomo + CBC: 11x11 in under 1s, 15x15 in 40s, but 20x20
fails on CBC after 12h (Gurobi solves it in 42m). The post's takeaway: "For larger problems
CBC MIP solver is not the best tool. For this kind of puzzle SAT solvers might be a better
choice." Source: <https://sysid.github.io/numberlink-puzzle/>.

**ZDD-based enumeration (specific to uniqueness questions).**
The 2012 paper "Finding All Solutions and Instances of Numberlink and Slitherlink by ZDDs"
in *Algorithms* (MDPI) builds a Zero-suppressed Binary Decision Diagram representing all
solutions of a given puzzle instance. Because ZDD construction is enumeration, "one can
immediately decide whether an instance admits exactly one solution." For one-pair Numberlink
the underlying primitive is Knuth's `Simpath`, which constructs the ZDD of all s-t paths
in a graph.
Sources: <https://www.mdpi.com/1999-4893/5/2/176> and the abstract on the GitHub mirror
<https://github.com/kunisura/algorithms2012>.

**DLX / Dancing Links.**
The Wikipedia article on Dancing Links lists known applications (Sudoku, n-queens, pentomino
tilings, polyominoes), but I could not find Numberlink as a documented DLX application.
Source: <https://en.wikipedia.org/wiki/Dancing_links>. **Unverified**: no OSS Numberlink
solver based on DLX surfaced in any of the searches above. The reason is plausibly that
Numberlink is a path-connectivity problem and is not naturally an exact-cover problem
(unlike polyomino tiling).

### 1.3 What "unique solution" means and how generators enforce it

Across the sources, "unique solution" consistently means: only one configuration of paths
satisfies all puzzle constraints (terminals connected, no crossings, plus whatever extras
the variant requires, e.g. full coverage). Generator pipelines I found:

**PuzzleMadness's eight-step pipeline.** Empty grid → random connection with up to 6 turns
→ shortest path between pairs preferring dead-ends → fill isolated 3-or-less-cell areas →
repeat → merge → discard if any 2-cell links → renumber. Then candidate puzzles must pass
"no loops, link count in 85-115% of total grid cells, unique solution verified by the
backtracking solver."
Source: <https://puzzlemadness.co.uk/howwemakenumberlink/>.

**Doug Osborne's Flow-Free-style level generator** (powers "Connect Unlimited 2," "CTD:
Shadows," "CTD: Portals"): place pairs of dots and draw lines until the board is filled.
Constraints to keep puzzles interesting:
- Same-colored dots cannot be adjacent.
- Lines must be at least 3 tiles long.
- "No zig-zag rule": "If a line could have entered a square at an earlier point but didn't,
  it can't ever enter that square."

Source: <https://doug-osborne.com/the-level-generator/>.

**Houston-We-Have-A-Bug's `FlowFree` C program** generates random starting positions,
runs them through the solver, and rejects candidates with "Too many solutions." Parameters
include grid dimensions, color count, endpoint distance minimums, and the solution-count
limit. Source: <https://github.com/HoustonWeHaveABug/FlowFree>.

**ZDD enumeration** (above): construct the ZDD of all solutions; an instance is unique
iff the ZDD's cardinality is 1.

The pattern across all of them: solve the candidate puzzle with the solver running in
"enumerate up to k solutions" mode; reject if k > 1. The candidate generation strategy
varies (random pairs, drawing paths first, etc.) but the **uniqueness gate is always run by
re-solving**.

### 1.4 Does Flow Free use every cell?

**Yes, by the rule of the standard game.** The Wikipedia article on Flow Free states "all
grid spaces must be filled to complete a level." Big Duck Games' product page says "pair
all colors while covering the entire board to solve each puzzle." Sources:
<https://en.wikipedia.org/wiki/Flow_Free>, <https://www.bigduckgames.com/flowfree>.

In Wikipedia's *Numberlink* article, the cover-all-cells rule is presented as a Flow Free /
"Zig-Zag" variant: standard Numberlink "a well-designed puzzle has a unique solution with
all grid cells filled, though some designers omit this requirement."
Source: <https://en.wikipedia.org/wiki/Numberlink>.

This matters for our design. If we **require full coverage** with one S/G pair, the path
becomes a Hamiltonian path on the grid graph from S to G (see §5). If we **don't require
coverage**, the path is a non-self-crossing simple path on the grid graph from S to G,
plus the row/column count clues we already plan to use. The row/column count clues
**implicitly** constrain coverage (their sum = path length, which is at most n*m).
**Unverified**: whether any commercial puzzle uses exactly the rule set "single S-G path
+ row/col path-cell counts without forced full coverage." Pathonogram and Conceptis
Monorail are the closest references and are discussed in §3.

### 1.5 NP-completeness of Numberlink and related variants

Three named complexity results, in chronological order:

1. **Lynch 1975**, "The equivalence of theorem proving and the interconnection problem,"
   *ACM SIGDA Newsletter* 5: 31-65. Proved vertex-disjoint paths NP-hard on grids in the
   general (no cover-all-cells) variant. This pre-dates the Numberlink puzzle name.
   Source (citation found in): <https://arxiv.org/abs/1410.5845>.

2. **Kotsuma and Takenaga 2010**, "NP-completeness and enumeration of number link puzzle,"
   IEICE Technical Report COMP2009-49 (the Adcock et al. paper cites this as "IEICE Tech.
   Report 109, no. 465 (March 2010)"). The result: Numberlink with the standard Nikoli
   restriction that paths have the **fewest possible corners within their homotopy class**
   is NP-complete. This restriction is what stops trivial U-turns and is the rule used in
   classical Nikoli Numberlink. Sources: <https://arxiv.org/abs/1410.5845> and
   <https://www.isnphard.com/i/numberlink/> (Complexity of Games catalogue page).
   *Note*: the isnphard page warns the Kotsuma-Takenaga paper "may not have undergone a
   rigorous peer review process." Source: <https://www.isnphard.com/i/numberlink/>.

3. **Adcock, Demaine, Demaine, O'Brien, Reidl, Sánchez Villaamil, Sullivan 2014**,
   "Zig-Zag Numberlink is NP-Complete," arXiv:1410.5845, published *Journal of
   Information Processing* 23(3):239-245 (2015). They prove that the variant **with the
   cover-all-cells (vertex-covering) requirement and without the fewest-corners
   restriction** ("Zig-Zag" / Flow Free style) is NP-complete. This is the Flow Free /
   Numberlink variant explicitly. Sources: <https://arxiv.org/abs/1410.5845>,
   <https://dspace.mit.edu/handle/1721.1/100008>,
   <http://martindemaine.org/papers/Numberlink_JIP/>.

The Adcock et al. paper explicitly distinguishes its result from Lynch 1975 ("without the
vertex-covering requirement") and Kotsuma & Takenaga 2010 ("where paths minimize corners
within their homotopy class"). Source: <https://arxiv.org/abs/1410.5845>.

The Adcock et al. paper also notes: "when only one pair of terminals is allowed, the
problem reduces to finding a Hamiltonian path in a grid given fixed start and end points,
which is solvable in polynomial time" (for *rectangular* grid graphs, i.e. full m x n
rectangles; this comes from Itai, Papadimitriou and Szwarcfiter 1982, see §5).
Source: <https://arxiv.org/abs/1410.5845>.

**Practical implication for our game.** A puzzle with one S/G pair on a full m x n rectangle
where the path is required to cover every cell is poly-time decidable (Hamiltonian path
between two fixed endpoints in a rectangular grid graph, Itai-Papadimitriou-Szwarcfiter).
A puzzle with one S/G pair, no cover-all-cells constraint, plus our row/col count clues
is closer to "longest path between two endpoints with cardinality clues per row/column,"
which I have not found a complexity result for. **Unverified**.

### 1.6 OSS Numberlink/Flow Free solvers (survey)

Sorted roughly by stars/visibility, all observed via GitHub fetches above and the
`numberlink-solver` topic page <https://github.com/topics/numberlink-solver>:

- `thomasahle/numberlink` — Go + Python generator, 101 stars. Backtracking with link-corner
  representation; assumes uniqueness, does not verify it; ships a generator.
  <https://github.com/thomasahle/numberlink>.
- `kunisura/algorithms2012` — source for the *Algorithms 2012* ZDD paper. Covers both
  Numberlink and Slitherlink. <https://github.com/kunisura/algorithms2012>.
- `uguryavuz/numberlink-solver` — Python, Google OR-Tools (CP-SAT). Documented to occasionally
  create free-standing loops (open issue). <https://github.com/uguryavuz/numberlink-solver>.
- `Huy1711/Numberlink-solver-SAT4J` — Java, SAT4J. Cell-direction encoding.
  <https://github.com/Huy1711/Numberlink-solver-SAT4J>.
- `kstarzyk/numberlink-solver` — Haskell and Prolog implementations.
  <https://github.com/kstarzyk/numberlink-solver>.
- `michaellaszlo/numberlink-solver` — JavaScript.
  <https://github.com/michaellaszlo/numberlink-solver>.
- `nejiko96/NumberLink` — applet/GUI solver. <https://github.com/nejiko96/NumberLink>.
- `gODeaLoAple/Numberlink` — solver+generator for university labs.
  <https://github.com/gODeaLoAple/Numberlink>.
- `abhishekpant93/numberlink-generator` — generates solvable Numberlink puzzles with
  solutions, browser-based. <https://github.com/abhishekpant93/numberlink-generator>.

Flow Free-specific solvers:
- `mzucker/...` Matt Zucker's C solver (best-first search), described above on his blog.
  <https://mzucker.github.io/2016/08/28/flow-solver.html>.
- `Torvaney/flow-solver` — Clojure, SAT via rolling-stones / sat4j. Edge-color encoding.
  <https://github.com/Torvaney/flow-solver>.
- `andy327/flow-solver` — Scala. <https://github.com/andy327/flow-solver>.
- `adriacabeza/FlowFreeSolver` — Prolog + picosat. <https://github.com/adriacabeza/FlowFreeSolver>.
- `MusadiqPasha/FlowFree-Solver` — Python + Z3. <https://github.com/MusadiqPasha/FlowFree-Solver>.
- `lohchness/flow-free-solver` — C, Dijkstra on implicit state graph.
  <https://github.com/lohchness/flow-free-solver>.
- `leophagus/Flow-Free-Solver` — SAT-based, framed as multi-net mesh routing.
  <https://github.com/leophagus/Flow-Free-Solver>.
- `HoustonWeHaveABug/FlowFree` — C, generator + solver.
  <https://github.com/HoustonWeHaveABug/FlowFree>.

**Unverified**: definitive ranking by star count beyond `thomasahle/numberlink` being the
clear leader. The GitHub topic page <https://github.com/topics/numberlink-solver> shows
them but I did not fetch each one's star count.

---

## 2. Slitherlink, Masyu, Hashi

### 2.1 Slitherlink

**Rules.** From Wikipedia: "The number inside a square represents how many of its four
sides are segments in the loop," and "the lines form a simple loop with no loose ends."
The puzzle started in *Puzzle Communication Nikoli* #26 (June 1989).
Source: <https://en.wikipedia.org/wiki/Slitherlink>.

**Named human deduction techniques (from Conceptis's official catalogue).** Conceptis groups
their techniques into Starting / Basic / Advanced. The Starting techniques are:
1. No lines around a 0
2. Adjacent 0 and 3
3. Diagonal 0 and 3
4. Two adjacent 3's
5. Two diagonal 3's
6. Any number in a corner

Basic: constraints on a 3; loop reaching a 3; loop reaching a 1; constraints on a 2;
avoiding a separate loop. Advanced: "six complex strategies using recursion, a looking
ahead process of making assumptions" to resolve difficult situations.
Source: <https://www.conceptispuzzles.com/index.aspx?uri=puzzle/slitherlink/techniques>.

Dev.to has a comprehensive guide that mirrors Conceptis but adds the "S-shape / Z-shape"
naming for the corner-3-next-to-3 pattern: "5 edges determined at once" via the shared edge
between adjacent 3s and forced outer lines.
Source: <https://dev.to/ansonchan/slitherlink-corner-patterns-the-complete-guide-3gcf>.

Jonathan Olson's page treats Slitherlink as a constraint system and emphasizes the
"every vertex has either 0 or 2 lines" invariant as the unifying principle, plus parity /
coloring methods (inside vs outside via Jordan curve theorem).
Source: <https://jonathanolson.net/slitherlink/>.

**Solver structure.** Two well-documented approaches:

1. **SAT/SMT encoding with edge variables.** Each edge is a boolean. Per-cell constraints
   enforce the number-clue count. Per-vertex constraints enforce 0 or 2 incident lines.
   A connectivity/single-loop constraint is the hard part (see Knijff 2021 below). Examples:
   `agill123/SlitherLink` (constraint programming + web UI)
   <https://github.com/agill123/SlitherLink>; `mame/ruby-minisat` examples include a
   Slitherlink encoding <https://github.com/mame/ruby-minisat/blob/master/examples/slitherlink.rb>;
   `japdlsd/slither-link-sat` <https://github.com/japdlsd/slither-link-sat>; Westreicher's
   bachelor thesis "Slitherlink Reloaded" (Innsbruck, 2011) uses SAT + an "Iterative SAT"
   technique <https://david-westreicher.github.io/static/papers/ba-thesis.pdf>.

2. **CSP / DSL frontends to SAT.** Naoyuki Tamura's Copris+Sugar+GlueMiniSat stack runs a
   Slitherlink solver in Scala. Source: <https://cspsat.gitlab.io/copris-puzzles/slitherlink/index.html>.

3. **SMT with graph-property connectivity.** Knijff 2021 (bachelor thesis, Radboud Univ.)
   uses SMT (Z3) and encodes the single-loop constraint via a graph property from Zantema
   and Joosten: assign each part of the connected component a natural number, where each
   non-starting part is connected to a part with a strictly smaller number. The thesis
   applies this approach to Slitherlink, Masyu, Shingoki, Nurikabe, Hitori, and Hashi.
   Source: <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.

4. **Specialised solvers using pattern propagation + backtracking.** Carleton College's
   comps project surveys these and benchmarks against brute force.
   Source: <https://cs.carleton.edu/cs_comps/1516/slither/index.php>.

**Generator strategies.** Liam Appelbe's Medium post documents a two-mode pipeline. Quoting
the earlier MDPI Algorithms 2012 paper's terminology:
- **Top-down (Shirai's algorithm):** Start with an empty grid (many solutions). Repeatedly
  add a random number into a random cell until exactly one solution remains.
- **Bottom-up:** Start with a known cycle. Fill all cells with their compatible numbers.
  Remove numbers one by one, stopping just before uniqueness breaks.

Sources: <https://liamappelbe.medium.com/how-to-generate-slither-link-puzzles-6c65510b2ba1>,
<https://www.mdpi.com/1999-4893/5/2/176>.

Difficulty is estimated by the recursive depth required by the solver during generation,
per Liam Appelbe's post.

**Complexity.** Yato 2000, "On the NP-completeness of the Slither Link puzzle," IPSJ SIG
Notes ALgorithms 74 (2000) 25-32, proves Slitherlink NP-complete by reduction from
Hamiltonian path on restricted graphs. The proof also yields ASP-completeness ("Another
Solution Problem") meaning verifying uniqueness is also NP-complete.
Sources: <https://www.semanticscholar.org/paper/On-the-NP-completeness-of-the-Slither-Link-Puzzle-Yato/4ec510eee1b76b2bfac1d2f7ca4e52ce30b50178>,
<https://www.researchgate.net/publication/238205893_Complexity_and_Completeness_of_Finding_Another_Solution_and_Its_Application_to_Puzzles>.

A second paper, "Selected Slither Link Variants are NP-complete," covers other Slitherlink
variants. Source: <https://www.jstage.jst.go.jp/article/ipsjjip/20/3/20_709/_pdf>.

The 2024 paper "ASP-Completeness of Hamiltonicity in Grid Graphs, with Applications to
Loop Puzzles" (Brunner, Chung, Demaine, Hendrickson, Tockman; FUN 2024) builds a
"T-metacell" framework and uses it to prove ASP-completeness of 38 loop-drawing puzzles.
Sources: <https://arxiv.org/abs/2405.08377>,
<https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FUN.2024.23>.

### 2.2 Masyu

**Rules.** Wikipedia: "Masyu is played on a rectangular grid where solvers draw a single
continuous loop through all circled cells. The loop must enter and exit each cell at
90-degree angles." White circles: travel straight, with a turn in the previous or next
cell. Black circles: turn on the circle, with straight in the next and previous cells.
Source: <https://en.wikipedia.org/wiki/Masyu>.

**History.** First published 2000, *Puzzle Communication Nikoli* issue 90 (gmpuzzles
"Masyu Rules and Info" says "Communication 90," authors 矢野龍王 (Yano Ryuoh) and
アセトニトリル (Acetonitrile)). The name change to "Masyu" came later in issue 103, due
to "a misreading by Nikoli's president."
Sources: <https://en.wikipedia.org/wiki/Masyu>, <https://www.gmpuzzles.com/blog/masyu-rules-and-info/>.

**Named techniques.** Searched sources name:
- "Black pearl one cell away from the edge acts like a black pearl on the edge"
- The 2-cells-straight forced rule for black pearls
- Edge-following deductions
- Border-walk strategy (start at the outside)

Sources: <https://www.keepitsimplepuzzles.com/how-to-solve-masyu-puzzles/>,
<https://www.puzzle-masyu.com/>, <https://krazydad.com/masyu/tutorial/>,
<https://www.gmpuzzles.com/blog/masyu-rules-and-info/>.

**Solver structure.** Same options as Slitherlink: SAT/SMT encoding, CSP DSL, custom
pattern propagator. The Copris-puzzles project ships a Masyu solver tested on 430
instances of a Masyu puzzle database; with GlueMiniSat 2.2.10 backend.
Source: <https://cspsat.gitlab.io/copris-puzzles/masyu/index.html>.
Knijff 2021 also implements Masyu in SMT.
Source: <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.

**Complexity.** Friedman 2002, "Pearl Puzzles are NP-complete," via reduction from
Hamiltonian circuit in cubic planar graphs.
Source: <https://www.researchgate.net/publication/2532689_Pearl_Puzzles_are_NP-complete>.

**Generator strategies.** Knijff 2021 generates Slitherlink and Masyu puzzles using the
top-down / bottom-up SMT approach: instantiate solver in `count-solutions` mode, add/remove
clues until uniqueness flips.
Source: <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.

### 2.3 Hashiwokakero (Hashi)

**Rules.** Wikipedia: Connect all islands with horizontal/vertical bridges (max 2 per
pair); bridge count at each island equals its label; all islands form one connected
network. Source: <https://en.wikipedia.org/wiki/Hashiwokakero>.

**History.** Debuted in *Puzzle Communication Nikoli* #31 (September 1990). Source:
same Wikipedia article. Conceptis launched their version October 12, 2007 with
"fourteen puzzle sizes ranging from 8x8 to 20x26 with seven difficulty levels."
Source: <https://www.conceptispuzzles.com/index.aspx?uri=info/news/241>.

**Named techniques.** From multiple sources:
- "Just Enough Neighbor"
- "One Unsolved Neighbor"
- "Few Neighbor"
- "Leftovers"
- "Isolation" (preventing partial-component closure)
- High-value forcing: "An island showing '3' in a corner, '5' along the outside edge, or
  '7' anywhere must have at least one bridge radiating from it in each valid direction";
  "A '4' in a corner, '6' along the border, or '8' anywhere must have two bridges in each
  direction."

Sources: <https://www.hashi.info/how-to-solve>,
<https://puzzlegenius.org/hashiwokakero/>,
<https://www.keepitsimplepuzzles.com/how-to-solve-hashi-puzzles/>.

**Solver structure.** Three main approaches:

1. **Hashi-specific propagation + DFS.** Malik (BEEI 2015) combines Hashi-specific
   propagation rules with depth-first search. Source:
   <https://beei.org/index.php/EEI/article/view/227>.

2. **Branch-and-cut ILP.** Coelho, Laporte, Lindbeck, Vidal (2019), "Benchmark Instances
   and Branch-and-Cut Algorithm for the Hashiwokakero Puzzle," arXiv:1905.00973. Integer
   programming with dynamically generated connectivity cuts; solves hard puzzles up to
   400 islands. Source: <https://arxiv.org/abs/1905.00973>.

3. **SMT with graph-property connectivity.** Knijff 2021.
   Source: <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.

4. **Highly optimized hand-built solvers.** `PhoenixSmaug/hashi` advertises itself as
   "A highly efficient solver for the Hashiwokakero logic puzzle."
   Source: <https://github.com/PhoenixSmaug/hashi>.

**Complexity.** Andersson 2009, "Hashiwokakero is NP-complete," *Information Processing
Letters* 109(19):1145-1146. Reduction from Hamiltonian cycle in unit-distance graphs.
Sources: <https://www.sciencedirect.com/science/article/abs/pii/S002001900900235X>,
<https://pure.au.dk/portal/en/publications/hashiwokakero-is-npcomplete(22d54450-7c30-11de-b4c2-000ea68e967b).html>.

**Generator strategies.** Multiple Hashi generators exist
(<https://miniwebtool.com/hashi-bridges-puzzle-generator/>,
<https://sudokutodo.com/bridges-generator>, <https://hashi-puzzles.com/generator/>),
but I did not find a public technical description of their algorithms beyond
"generate-then-verify-uniqueness via solver." **Unverified** as to specific industrial
strategy.

### 2.4 Generator strategies for pure-deduction puzzles (cross-cutting)

All Slitherlink, Masyu, and Hashi sources I found converge on a generate-then-verify
pattern that mirrors the Numberlink/Flow Free pattern in §1.3:

1. Construct a candidate solution (Hamiltonian/loop/bridge layout) using a randomized
   constructor.
2. Derive the candidate puzzle (numbers, circles, island labels) from the solution.
3. Run a solver in enumeration mode (or with a second-solution check) on the candidate.
4. If the candidate has exactly one solution and the solver can find it using only the
   "allowed" deduction set (for difficulty grading), keep it; otherwise mutate clues
   (add/remove) and retry.

This pattern is documented in:
- PuzzleMadness's Numberlink pipeline (§1.3).
- Liam Appelbe's Slitherlink generator post.
  <https://liamappelbe.medium.com/how-to-generate-slither-link-puzzles-6c65510b2ba1>.
- Knijff 2021 for Slitherlink and Masyu.
  <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.
- MDPI Algorithms 2012 paper's "Shirai" top-down and "bottom-up" formulations.
  <https://www.mdpi.com/1999-4893/5/2/176>.

Difficulty grading is typically the recursive depth of the solver, or the level of
deduction technique needed (basic vs advanced vs hypothetical).
Source: <https://liamappelbe.medium.com/how-to-generate-slither-link-puzzles-6c65510b2ba1>.

**Nikoli's hand-craft policy.** Nikoli is publicly proud that their puzzles are
hand-crafted by enthusiasts (their Slitherlink Nintendo Switch release advertises this).
Source: <https://www.nikoli.co.jp/en/puzzles/slitherlink/>. **Unverified**: precise
quote on the "hand-crafted" claim attribution.

---

## 3. Single-path constraint with row/column counts

### 3.1 What we are actually looking for

Our game: a single connected non-branching non-crossing path from S to G on a grid,
plus row/column counts (single number per row/column = number of path cells in that
row/column), plus revealed in-grid hints (arrows or segment shapes).

The combination of "single path on a grid" and "row/column count clues" is unusual.
Let's go through the closest known puzzles.

### 3.2 Conceptis Monorail / IBA Monorail / Round Trip / Grand Tour

**Important clarification.** Despite the Web-search assistant initially associating
"Monorail" with Conceptis, the Monorail app is **not a Conceptis product.** It is by
IBA Puzzles (Glenn Iba and Aaron Iba). Source: Glenn Iba's own page,
<http://glenniba.com/monorail/monorailpuzzles.html>; App Store and Google Play listings
<https://apps.apple.com/us/app/monorail/id431435215>,
<https://play.google.com/store/apps/details?id=com.ibapuzzles.monorail>.

The Iba page also gives the lineage: "Round Trip puzzles were invented by Stitch (his
initials are S.E.W.) and first published in Dell Champion Variety Puzzles in the early
1990's." Source: <http://glenniba.com/monorail/monorailpuzzles.html>.

**Monorail / Round Trip / Grand Tour rules (Iba's G4G8 paper, primary source).**
The paper "Hamiltonian Cycle Puzzles" by Glenn A. Iba (G4G8 Exchange Book) gives the
exact rules I confirmed by direct PDF read:

- Grid of equally spaced vertices.
- Edges are vertical/horizontal between neighbors.
- Some edges are pre-drawn (the puzzle's clues).
- The solver finds the unique Hamiltonian cycle that includes all pre-drawn edges.
- Shading the interior reveals a hidden picture.

Source (PDF): <http://glenniba.com/G4G8%20exchange%20paper.pdf>. Read directly from PDF
at the time of this research; key quote: "find the unique Hamiltonian cycle that includes
all of the edges drawn explicitly in the problem diagram."

**OneWayTrip variant.** Iba's site describes OneWayTrip puzzles as "the object is to form
a single closed path connecting Start (S) and End (E), where the path must visit every
vertex exactly once and include all the given permanent links." That is the **Hamiltonian
S-to-E path** version. This is the closest commercial reference to our game except for
two differences:
1. OneWayTrip has clues as pre-drawn edges, not row/column counts.
2. OneWayTrip requires Hamiltonian coverage (every cell on the path).

Source: <http://glenniba.com/OneWayTripHexBranch/OneWayTrip.html> (linked from Iba's main
page).

**No row/column counts in Monorail/Round Trip/Grand Tour.** Tanya Khovanova's writeup
confirms: "the highlighted edges are chosen to guarantee a unique solution to the puzzle.
To begin the puzzle, a few of the points are already connected to insure a unique solution."
No mention of edge clues, only of pre-drawn edges.
Source: <http://blog.tanyakhovanova.com/2008/08/grand-tour-puzzles/>.

**Solving strategies from Iba's G4G8 paper** (read directly from PDF; section "Hints
and strategies for solving"):
1. Don't guess; uniqueness is guaranteed.
2. Each vertex ends with exactly 2 edges; track open / endpoint / filled status.
3. If an open vertex has exactly 2 available neighbors, both edges are forced (corners
   are the most common case).
4. Avoid premature short cycles (a connection between two endpoints of one partial path
   creating a cycle smaller than all vertices is forbidden).
5. Avoid edges that would isolate a vertex.
6. Open vertex with 3 available neighbors: exactly 2 of the 3 are in the path; if 2
   would create a cycle, the third is forced.
7. **Region parity.** Any solution path crosses any region boundary an even number of
   times; if an edge would force odd parity, rule it out. (This is the Jordan-curve
   argument used in Slitherlink solving too.)

Source: read from PDF saved at `/tmp/iba_g4g8.pdf`, mirrored on
<http://glenniba.com/G4G8%20exchange%20paper.pdf>.

So: **Monorail / Round Trip / Grand Tour / OneWayTrip have no row/column counts**. Their
clues are pre-drawn edges. They do, however, share the "Hamiltonian on a grid" or
"S-to-G covering path on a grid" structure with our game.

### 3.3 Pathonogram (Google Play)

Pathonogram is the closest direct match to our concept that I found. The Google Play
listing describes it as "a game that combines the classical rules of Nonograms with
pathfinding. More specifically, users must use the information about rows and columns to
find parts of the path on the grid, and use the logic of pathbuilding to correctly
connect them."

Source: <https://play.google.com/store/apps/details?id=com.NikitaDezhic.com.unity.template.mobile2D>.
(The direct WebFetch returned 404 once but the description was successfully extracted by
WebSearch.)

**Unverified specifics**: I could not pull the full app rules (whether single-path or
multi-path, whether row clues are single counts or sequences, whether full coverage is
required). The dev's name on the listing is Nikita Dezhic; release tagged August 17,
2023 per the search result. This is a low-budget independent game; I could not find any
algorithm writeup or interview by the dev. **Unverified** beyond the store description.

### 3.4 Search for "path nonogram" / "connected nonogram"

I searched "connected nonogram" and "path nonogram" multiple times. No commercial puzzle
beyond Pathonogram surfaced. The closest matches in Nikoli-style puzzles were Yajilin
(arrows-in-grid, loop, count-shaded-cells-in-row/column) and Country Road (loop +
per-region counts), neither of which is a single-path-with-row/col-counts puzzle.

- Yajilin: <https://en.wikipedia.org/wiki/Yajilin>. "For each indicative cell, its number
  indicates the count of the black cells that lie in that row or column in the direction
  of its arrow." That's a count, but of *shaded cells in the direction of an arrow*,
  not of path cells in a row/column.
- Country Road: <https://mellowmelon.wordpress.com/country-road/>,
  <https://www.cross-plus-a.com/html/cros7ctrd.htm>. "The number in a region indicates
  how many cells of this region are visited by the loop." Counts per *region*, not per
  row/column. And the path is a loop.

The 2022 framework paper "A Framework for Loop and Path Puzzle Satisfiability NP-Hardness
Results" by Hadyn Tang covers many genres but I could not extract a list of which puzzles
combine "single path / loop" with "row/column counts of path cells."
Source: <https://arxiv.org/abs/2202.02046>.

### 3.5 Datagenetics' "Hamiltonian Path Puzzle" and Papadopoulos' "Number Trail"

Two adjacent designs:

- Datagenetics blog (October 2021), "Hamiltonian Path Puzzle." Describes a generic
  Hamiltonian path puzzle on a grid. Source: <https://datagenetics.com/blog/october12021/index.html>.
- Nikos Papadopoulos, "Building a Hamiltonian path puzzle: Number Trail." The puzzle is
  "draw one continuous line that visits every cell exactly once, passing through numbered
  clues in order." The clues are sequence-ordered waypoints, not row/column counts. The
  puzzle generator uses Warnsdorff's rule (from knight's-tour generation) and "places walls
  only on edges that are not part of the known solution path, so solvability is guaranteed
  by construction." Source: <https://www.4rknova.com/blog/2026/04/24/number-trail>.

Neither is the same as our puzzle, but both are closer than Numberlink to the spirit of
"trace a single path."

### 3.6 Verdict

**There is no widely-documented commercial puzzle that combines exactly "single S/G
path on a grid" + "row/column counts of path cells" + "in-grid hint arrows/segments."**
The closest is **Pathonogram** (Google Play, 2023, indie). The closest in *Hamiltonian
spirit* is **IBA Monorail / Round Trip / Grand Tour / OneWayTrip**, but those use
pre-drawn edges as clues, not counts. Conceptis does **not** publish a Monorail-style
puzzle (verified by browsing their puzzle catalogue link from
<https://www.conceptispuzzles.com/>; the search results confirm Conceptis's catalogue is
Hashi, Slitherlink, Kakuro, Sym-a-Pix, Battleships, Nurikabe, Block-a-Pix, Dot-a-Pix,
CalcuDoku, Maze-a-Pix, Skyscrapers).
Source: <https://hoverdia.com/Conceptis.html> mirroring their list.

This is a relatively open design space.

---

## 4. Path representation in solvers

The main encoding choices identified across the sources:

### 4.1 Edge variables

One boolean per (undirected) grid edge. Constraints are local per-vertex (degree 2 for
path interior, degree 1 for S and G in our case; degree 0 or 2 for vertices not on the
path).

Example implementations:
- Torvaney's Flow Free solver. <https://torvaney.github.io/projects/flow-solver.html>.
- Most SAT-based Slitherlink solvers (each grid edge is a variable; per-cell number
  constraints; per-vertex 0/2-degree constraints). Westreicher 2011:
  <https://david-westreicher.github.io/static/papers/ba-thesis.pdf>; agill123/SlitherLink:
  <https://github.com/agill123/SlitherLink>.
- Coelho et al. branch-and-cut for Hashi uses edge / bridge variables (with up to 2
  bridges per edge for multiplicity). <https://arxiv.org/abs/1905.00973>.

Edge encoding is natural when the puzzle clues are local at vertices or edges (Slitherlink,
Masyu, our row/column counts of path cells map cleanly to "sum of edge incidences").

### 4.2 Cell-plus-direction variables

For each cell, one boolean per direction (N/E/S/W) indicating an outgoing edge. Reflexivity
constraints enforce that the neighbor in the chosen direction agrees.

Example: `Huy1711/Numberlink-solver-SAT4J`, with explicit `Xij,k` (k = LEFT/RIGHT/UP/DOWN)
and reflexivity constraints `Xij,1 -> X(i)(j-1),2`.
Source: <https://github.com/Huy1711/Numberlink-solver-SAT4J>.

### 4.3 Cell-plus-color (Flow Free / multi-pair Numberlink)

For each cell and each color (path label), one boolean: "this cell is on path k." Plus
per-cell "exactly one color" and per-pair "neighbor agreement" constraints. Used in:
- Yet Another Math Programming Consultant's MIP model
  <http://yetanothermathprogrammingconsultant.blogspot.com/2017/09/numberlink-models.html>.
- sysid's Pyomo reproduction
  <https://sysid.github.io/numberlink-puzzle/>.
- Copris-puzzles Numberlink solver
  <https://cspsat.gitlab.io/copris-puzzles/numberlink/index.html>.

For our single-pair puzzle the color dimension collapses, leaving "cell is on path"
booleans plus path-shape constraints. This is essentially the same as a binary-fill
nonogram with extra connectivity constraints.

### 4.4 Connectivity constraint encodings

Connectivity (single connected component, no extra loops) is the hard constraint for SAT.
Common encodings:

- **Lazy / cutting-plane.** Solve without the connectivity constraint; if a stray loop /
  disconnected component appears, add a constraint forbidding *that specific* component
  and re-solve. Used in the Hashi branch-and-cut paper (subtour-elimination cuts à la
  TSP). Source: <https://arxiv.org/abs/1905.00973>.

- **Spanning-tree / numbering trick.** Assign each cell on the path a natural number
  representing distance from S. Adjacent path cells must differ by 1; S is fixed at 1.
  This forces a path. Used in Knijff's SMT encoding (with a variant for loops).
  Source: <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.

- **Cell-direction with reflexivity.** As in the Numberlink-SAT4J encoding above.
  Connectivity is enforced because the directional pointers form a 2-regular subgraph
  with exactly two degree-1 endpoints; combined with the "no disjoint loops" check, it
  is a simple path. The "no disjoint loops" is the postprocessing step the
  `uguryavuz/numberlink-solver` README admits it is missing.
  Source: <https://github.com/uguryavuz/numberlink-solver>.

### 4.5 Hamiltonian-path-specific encodings

When the path is required to cover every cell, the problem becomes Hamiltonian path
between two specified endpoints in a (subgraph of a) grid graph. Standard ILP encodings:

- Miller-Tucker-Zemlin (MTZ) subtour elimination using a position variable per cell
  (1..n), with `u_i - u_j + n * x_{ij} <= n - 1` style constraints. Standard TSP material;
  see Wikipedia <https://en.wikipedia.org/wiki/Travelling_salesman_problem> and the
  Coelho et al. Hashi paper for a related cut-generation strategy.

- DFW / single-commodity flow encoding: pump a unit of "flow" from S to G, force every
  path cell to be on the flow path.

- Itai-Papadimitriou-Szwarcfiter 1982 give a constructive **polynomial-time** algorithm
  for Hamiltonian s-t path in **rectangular** grid graphs, with explicit necessary and
  sufficient conditions on (parity of grid, positions of s and t). Source:
  <https://epubs.siam.org/doi/10.1137/0211056>; PDF mirror:
  <https://csaws.cs.technion.ac.il/~itai/publications/Algorithms/Hamilton-paths.pdf>.

**Unverified** for our case: whether Itai-Papadimitriou-Szwarcfiter's poly-time algorithm
adapts cleanly when row/column count clues are added (these are global linear constraints).

### 4.6 Choice for our game (informational, not prescriptive)

Given:
- Small grids (5x5 to ~15x15) per `GAME_CONTEXT.md`.
- Row/column count clues (linear constraints).
- In-grid hint arrows/segments (local cell/edge constraints).
- Single S/G pair.
- Uniqueness required (open question 6 in `GAME_CONTEXT.md`).

The most common solver pattern in the literature for puzzles in this size range:
SAT/SMT/CP-SAT with edge variables, per-cell row/column count cardinality constraints,
per-vertex degree constraints, plus a connectivity constraint via the numbering trick
or lazy cuts. Generator then is "generate solution path, derive clues, verify uniqueness."

**This is descriptive, not a recommendation.** The question of which encoding to use
for our exact puzzle is open and should be re-evaluated with a prototype.

---

## 5. Hamiltonian path / TSP relevance

### 5.1 Hamiltonian path NP-completeness (canonical reference)

Garey and Johnson 1979, *Computers and Intractability: A Guide to the Theory of
NP-Completeness*, is the canonical reference. Wikipedia cites it as the foundational
work for Hamiltonian path NP-completeness on general graphs.
Source: <https://en.wikipedia.org/wiki/Hamiltonian_path_problem>.

### 5.2 Grid graphs

**Subgraphs of the square grid: Hamiltonian path NP-complete.** Itai, Papadimitriou,
and Szwarcfiter, "Hamilton Paths in Grid Graphs," *SIAM Journal on Computing* 11(4):676-686,
1982. Proves the Hamilton path (and circuit) problem for general grid graphs (arbitrary
subgraphs of the integer grid) is NP-complete.
Sources: <https://epubs.siam.org/doi/10.1137/0211056>,
PDF: <https://csaws.cs.technion.ac.il/~itai/publications/Algorithms/Hamilton-paths.pdf>.

**Rectangular grid graphs (full m x n rectangle): Hamiltonian path between two specified
endpoints is polynomial-time decidable.** Same paper. They give "necessary and sufficient
conditions" and a constructive algorithm.

So: if we want a Hamiltonian-path version of our game (path covers every cell) on a
**full rectangle** with fixed S and G, deciding *existence* is poly-time and parities
are well-understood. Adding row/column count clues (which collapse to one specific
path among many) preserves the structure but does change the decision question.

### 5.3 Implications for puzzle apps

**The general lesson from the literature.** Real puzzle apps for NP-complete puzzle
genres handle complexity by:

- Restricting grid sizes to small (5x5 to 20x20 typical).
- Pre-generating puzzles offline, not on-device.
- Storing the solution alongside the puzzle (no on-device solving needed for win check).
- Optionally running a smaller "hint" solver on-device.

Big Duck Games' Flow Free ships "Over 2,000 free puzzles" plus DLC packs
(<https://www.bigduckgames.com/flowfree>). Conceptis ships pre-vetted puzzle packs
(<https://www.conceptispuzzles.com/index.aspx?uri=info/news/241> for Hashi: "fourteen
puzzle sizes ranging from 8x8 to 20x26 with seven difficulty levels"). IBA Monorail
ships "880 total puzzles across three packs" (<https://apps.apple.com/us/app/monorail/id431435215>).

The pattern is: **NP-completeness is irrelevant in practice**, because the publisher
generates and verifies puzzles offline (often hand-crafted or solver-validated), then
ships them. NP-completeness only matters if you want to *generate* and *grade* puzzles
at runtime on user devices, or for very large grids.

### 5.4 ASP-completeness (uniqueness verification)

For our game we care about uniqueness. The "Another Solution Problem" (ASP) is "given an
instance and one solution, decide if another solution exists." ASP-completeness implies
NP-completeness and means *verifying uniqueness is also NP-hard*.

- Yato and Seta 2003 proved ASP-completeness for Slitherlink, Cross Sum, and Number Place
  (Sudoku). Source: <https://www.researchgate.net/publication/238205893_Complexity_and_Completeness_of_Finding_Another_Solution_and_Its_Application_to_Puzzles>.
- Brunner, Chung, Demaine, Hendrickson, Tockman 2024 prove ASP-completeness for 38
  loop-drawing puzzles via the T-metacell framework over Hamiltonicity in max-degree-3
  grid graphs.
  Sources: <https://arxiv.org/abs/2405.08377>,
  <https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FUN.2024.23>.

**Practical implication:** uniqueness verification for our puzzle is unlikely to admit
a poly-time algorithm. The standard practice (see §1.3 and §2.4) is to invoke an
all-solutions or solution-counting solver, capped at finding the second solution.

---

## 6. Summary of confirmed and "unverified" claims

### Confirmed

- Flow Free requires full-cell coverage: yes
  (<https://en.wikipedia.org/wiki/Flow_Free>, <https://www.bigduckgames.com/flowfree>).
- Numberlink without cover-all rule: NP-complete (Lynch 1975, via the Adcock et al. paper).
- Numberlink with fewest-corners rule: NP-complete (Kotsuma & Takenaga 2010, IEICE Tech.
  Report; cited in <https://arxiv.org/abs/1410.5845> and <https://www.isnphard.com/i/numberlink/>).
- Numberlink with cover-all-cells rule ("Zig-Zag Numberlink"): NP-complete (Adcock et al.
  2014, <https://arxiv.org/abs/1410.5845>).
- Slitherlink: NP-complete (Yato 2000) and ASP-complete (Yato-Seta 2003).
- Masyu: NP-complete (Friedman 2002, "Pearl Puzzles are NP-complete").
- Hashi: NP-complete (Andersson 2009, IPL 109(19)).
- Hamiltonian path on subgraph of grid: NP-complete (Itai-Papadimitriou-Szwarcfiter 1982).
- Hamiltonian s-to-t path on **full rectangle** grid: polynomial-time (same paper).
- Garey & Johnson 1979 is the canonical NP-completeness reference (Wikipedia citation).
- Monorail (iOS/Android) is NOT Conceptis. It is IBA Puzzles (Glenn and Aaron Iba), and
  the puzzle type is "Round Trip" invented by Stitch / S.E.W. in Dell Champion Variety
  Puzzles in the early 1990s (<http://glenniba.com/monorail/monorailpuzzles.html>).
- Conceptis catalogue (no Monorail): Hashi, Slitherlink, Kakuro, Sym-a-Pix, Battleships,
  Nurikabe, Block-a-Pix, Dot-a-Pix, CalcuDoku, Maze-a-Pix, Skyscrapers
  (<https://hoverdia.com/Conceptis.html>, mirroring their site).
- Pathonogram (Google Play, Nikita Dezhic, August 2023) is the closest direct analog to
  our intended puzzle, but I could not retrieve full rule details
  (<https://play.google.com/store/apps/details?id=com.NikitaDezhic.com.unity.template.mobile2D>).
- Real puzzle apps generate and validate offline (large pre-shipped puzzle banks);
  NP-completeness of the puzzle genre is not a runtime concern. Source pattern: Flow Free
  (2000+ puzzles), Conceptis Hashi launch (14 sizes x 7 difficulties), IBA Monorail
  (880 puzzles).

### Unverified / open

- Specific star counts for less-popular OSS Numberlink solvers. Only `thomasahle/numberlink`
  (101 stars) was directly confirmed by GitHub fetch.
- Whether the Kotsuma-Takenaga 2010 paper went through rigorous peer review (isnphard.com
  flags this as uncertain).
- Whether Conceptis publishes any puzzle that combines "single connected path / loop on a
  grid" with "row/column counts of path cells." Searches surfaced none beyond Yajilin /
  Country Road, neither of which matches our rules.
- Whether DLX (Dancing Links / Algorithm X) has any published Numberlink solver. None
  appeared in searches; structurally Numberlink is not naturally an exact-cover problem.
- Full rules of Pathonogram beyond the store description (whether full coverage is required,
  whether clues are sequences or single counts, whether mistakes are silent or live-validated).
- Whether any combination of "single S-G path" + "row/col counts" + "no full-coverage
  requirement" has a known polynomial algorithm or complexity result. Itai-Papadimitriou-
  Szwarcfiter handles the full-coverage case on rectangles. The non-coverage case with
  count clues is, to my reading of the searches, an unexplored region.
- Whether Big Duck Games (Flow Free) has publicly disclosed their generator algorithm.
  Searches found no developer interview discussing the algorithm.
- The exact algorithms used by industrial generators (Conceptis's Hashi pipeline,
  Nikoli's hand-craft workflow). Only high-level statements are publicly available.

---

## 7. References (consolidated)

### Wikipedia and high-level reference

- Numberlink: <https://en.wikipedia.org/wiki/Numberlink>
- Flow Free: <https://en.wikipedia.org/wiki/Flow_Free>
- Slitherlink: <https://en.wikipedia.org/wiki/Slitherlink>
- Masyu: <https://en.wikipedia.org/wiki/Masyu>
- Hashiwokakero: <https://en.wikipedia.org/wiki/Hashiwokakero>
- Yajilin: <https://en.wikipedia.org/wiki/Yajilin>
- Hamiltonian path problem: <https://en.wikipedia.org/wiki/Hamiltonian_path_problem>
- Dancing Links: <https://en.wikipedia.org/wiki/Dancing_links>
- Nikoli (publisher): <https://en.wikipedia.org/wiki/Nikoli_(publisher)>

### Complexity results (papers)

- Adcock, Demaine, Demaine, O'Brien, Reidl, Sánchez Villaamil, Sullivan, "Zig-Zag
  Numberlink is NP-Complete," arXiv:1410.5845 (2014), *JIP* 23(3) (2015).
  <https://arxiv.org/abs/1410.5845>; <https://dspace.mit.edu/handle/1721.1/100008>;
  <http://martindemaine.org/papers/Numberlink_JIP/>.
- Kotsuma, Takenaga, "NP-completeness and enumeration of number link puzzle," IEICE
  Technical Report (2010). Cited in the Adcock paper.
- Lynch, "The equivalence of theorem proving and the interconnection problem," ACM SIGDA
  Newsletter 5 (1975) 31-65. Cited in the Adcock paper and Schrijver's *Paths in Graphs*
  monograph <https://ir.cwi.nl/pub/2220/2220D.pdf>.
- Yato, "On the NP-completeness of the Slither Link Puzzle," IPSJ SIG Notes 2000.
  <https://www.semanticscholar.org/paper/On-the-NP-completeness-of-the-Slither-Link-Puzzle-Yato/4ec510eee1b76b2bfac1d2f7ca4e52ce30b50178>.
- Yato, Seta, "Complexity and Completeness of Finding Another Solution and Its Application
  to Puzzles," IEICE Trans. 2003.
  <https://www.researchgate.net/publication/238205893_Complexity_and_Completeness_of_Finding_Another_Solution_and_Its_Application_to_Puzzles>.
- Friedman, "Pearl Puzzles are NP-complete" (2002).
  <https://www.researchgate.net/publication/2532689_Pearl_Puzzles_are_NP-complete>.
- Andersson, "Hashiwokakero is NP-complete," IPL 109(19) (2009).
  <https://www.sciencedirect.com/science/article/abs/pii/S002001900900235X>;
  <https://pure.au.dk/portal/en/publications/hashiwokakero-is-npcomplete(22d54450-7c30-11de-b4c2-000ea68e967b).html>.
- Itai, Papadimitriou, Szwarcfiter, "Hamilton Paths in Grid Graphs," SICOMP 11(4) (1982).
  <https://epubs.siam.org/doi/10.1137/0211056>;
  <https://csaws.cs.technion.ac.il/~itai/publications/Algorithms/Hamilton-paths.pdf>.
- Brunner, Chung, Demaine, Hendrickson, Tockman, "ASP-Completeness of Hamiltonicity in
  Grid Graphs, with Applications to Loop Puzzles," FUN 2024, arXiv:2405.08377.
  <https://arxiv.org/abs/2405.08377>;
  <https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.FUN.2024.23>.
- Tang, "A Framework for Loop and Path Puzzle Satisfiability NP-Hardness Results,"
  arXiv:2202.02046 (2022). <https://arxiv.org/abs/2202.02046>.
- Garey and Johnson, *Computers and Intractability* (1979). Cited via the Wikipedia
  Hamiltonian-path article: <https://en.wikipedia.org/wiki/Hamiltonian_path_problem>.

### Enumeration / ZDD

- "Finding All Solutions and Instances of Numberlink and Slitherlink by ZDDs,"
  *Algorithms* (MDPI) 5(2):176-213 (2012).
  <https://www.mdpi.com/1999-4893/5/2/176>;
  <https://github.com/kunisura/algorithms2012>.

### SMT / SAT / CSP solvers and theses

- Knijff, "Solving and generating puzzles with a connectivity constraint," Bachelor
  thesis, Radboud University, 2021.
  <https://www.cs.ru.nl/bachelors-theses/2021/Gerhard_van_der_Knijff___1006946___Solving_and_generating_puzzles_with_a_connectivity_constraint.pdf>.
- Westreicher, "Slitherlink Reloaded," bachelor thesis, Innsbruck, 2011.
  <https://david-westreicher.github.io/static/papers/ba-thesis.pdf>.
- Tamura, Copris constraint DSL + Slitherlink, Masyu, Numberlink solvers using Sugar +
  GlueMiniSat. <https://cspsat.gitlab.io/copris-puzzles/slitherlink/index.html>,
  <https://cspsat.gitlab.io/copris-puzzles/masyu/index.html>,
  <https://cspsat.gitlab.io/copris-puzzles/numberlink/index.html>.
- Tamura, "System Description of a SAT-based CSP Solver Sugar."
  <https://tamura70.gitlab.io/papers/pdf/cpai08t.pdf>.
- "Solving Hashiwokakero Puzzle Game with Hashi Solving Techniques and DFS," Malik,
  BEEI 2015. <https://beei.org/index.php/EEI/article/view/227>.
- Coelho, Laporte, Lindbeck, Vidal, "Benchmark Instances and Branch-and-Cut Algorithm
  for the Hashiwokakero Puzzle," arXiv:1905.00973 (2019).
  <https://arxiv.org/abs/1905.00973>.

### OSS solvers (Numberlink / Flow Free)

- `thomasahle/numberlink` (Go, 101 stars). <https://github.com/thomasahle/numberlink>.
- `uguryavuz/numberlink-solver` (Python + OR-Tools).
  <https://github.com/uguryavuz/numberlink-solver>.
- `Huy1711/Numberlink-solver-SAT4J` (Java + SAT4J).
  <https://github.com/Huy1711/Numberlink-solver-SAT4J>.
- `kstarzyk/numberlink-solver` (Haskell + Prolog).
  <https://github.com/kstarzyk/numberlink-solver>.
- `michaellaszlo/numberlink-solver` (JavaScript).
  <https://github.com/michaellaszlo/numberlink-solver>.
- `Torvaney/flow-solver` (Clojure + sat4j). <https://github.com/Torvaney/flow-solver>.
- `HoustonWeHaveABug/FlowFree` (C, solver + generator).
  <https://github.com/HoustonWeHaveABug/FlowFree>.
- `lohchness/flow-free-solver` (C + Dijkstra).
  <https://github.com/lohchness/flow-free-solver>.
- `andy327/flow-solver` (Scala). <https://github.com/andy327/flow-solver>.
- `adriacabeza/FlowFreeSolver` (Prolog + picosat).
  <https://github.com/adriacabeza/FlowFreeSolver>.
- `MusadiqPasha/FlowFree-Solver` (Python + Z3).
  <https://github.com/MusadiqPasha/FlowFree-Solver>.
- `leophagus/Flow-Free-Solver` (SAT, mesh routing framing).
  <https://github.com/leophagus/Flow-Free-Solver>.
- `kunisura/algorithms2012` (Numberlink+Slitherlink, ZDD).
  <https://github.com/kunisura/algorithms2012>.
- Matt Zucker's solver writeup. <https://mzucker.github.io/2016/08/28/flow-solver.html>.

### OSS solvers (Slitherlink / Masyu / Hashi)

- `agill123/SlitherLink` (CP + web UI). <https://github.com/agill123/SlitherLink>.
- `japdlsd/slither-link-sat`. <https://github.com/japdlsd/slither-link-sat>.
- Carleton College comps project survey.
  <https://cs.carleton.edu/cs_comps/1516/slither/index.php>.
- `PhoenixSmaug/hashi` (highly optimized solver).
  <https://github.com/PhoenixSmaug/hashi>.
- `erthium/hashiwokakero` (generator + solver).
  <https://github.com/erthium/hashiwokakero>.

### Generator writeups

- PuzzleMadness Numberlink pipeline. <https://puzzlemadness.co.uk/howwemakenumberlink/>.
- Liam Appelbe, "How to generate Slither Link puzzles."
  <https://liamappelbe.medium.com/how-to-generate-slither-link-puzzles-6c65510b2ba1>.
- Doug Osborne, "The Level Generator" (Flow-style).
  <https://doug-osborne.com/the-level-generator/>.

### Mathematical / industrial references

- "Yet Another Math Programming Consultant" Numberlink models.
  <http://yetanothermathprogrammingconsultant.blogspot.com/2017/09/numberlink-models.html>.
- sysid blog Pyomo / CBC reproduction. <https://sysid.github.io/numberlink-puzzle/>.
- Complexity of Games catalogue (Numberlink page).
  <https://www.isnphard.com/i/numberlink/>.

### Single-path + row/column count puzzles (closest references)

- Iba, "Hamiltonian Cycle Puzzles," G4G8 Exchange Book (paper).
  <http://glenniba.com/G4G8%20exchange%20paper.pdf>.
- Iba, Monorail puzzle page. <http://glenniba.com/monorail/monorailpuzzles.html>.
- Iba, Grand Tour. <http://glenniba.com/grandtourhexbranch/GrandTour.html>.
- Iba, OneWayTrip. <http://glenniba.com/OneWayTripHexBranch/OneWayTrip.html>.
- Khovanova on Grand Tour. <http://blog.tanyakhovanova.com/2008/08/grand-tour-puzzles/>.
- IBA Monorail App Store page. <https://apps.apple.com/us/app/monorail/id431435215>.
- Pathonogram on Google Play.
  <https://play.google.com/store/apps/details?id=com.NikitaDezhic.com.unity.template.mobile2D>.
- Papadopoulos, "Building a Hamiltonian path puzzle: Number Trail."
  <https://www.4rknova.com/blog/2026/04/24/number-trail>.
- Datagenetics, Hamiltonian Path Puzzle.
  <https://datagenetics.com/blog/october12021/index.html>.

### Conceptis catalogue

- <https://www.conceptispuzzles.com/>.
- Hashi launch news (2007).
  <https://www.conceptispuzzles.com/index.aspx?uri=info/news/241>.
- Slitherlink techniques.
  <https://www.conceptispuzzles.com/index.aspx?uri=puzzle/slitherlink/techniques>.
- Hoverdia mirror of Conceptis puzzle list.
  <https://hoverdia.com/Conceptis.html>.

### Flow Free / Big Duck Games

- <https://www.bigduckgames.com/flowfree>.
- <https://bigduckgames.wordpress.com/>.
- Wikipedia: <https://en.wikipedia.org/wiki/Flow_Free>.


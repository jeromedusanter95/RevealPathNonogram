# 01 Nonogram Research

Survey of solver techniques, generation pipelines, complexity results, and commercial references for classic nonograms (also called paint-by-numbers, Picross, Griddlers, Hanjie, Pic-a-Pix, Japanese crosswords). Every claim below is followed by a citation in `[source: ...]` form. Where a source is paywalled or could not be verified, that is stated explicitly.

> Scope note. This document covers the classic nonogram (each cell binary, runs-of-filled-cells clues per row and column). It does not yet cover the connected-path variant that is the topic of this project. That research belongs in a follow-up document.

---

## Table of contents

1. Origin and naming history (so terminology in citations is unambiguous)
2. Complexity results
3. Human-style deduction techniques
4. Line solvers and constraint-propagation algorithms
5. Survey of open-source nonogram solvers
6. Generator techniques
7. Difficulty rating methods
8. Commercial references
9. Simon Tatham's "Pattern" puzzle (source-level analysis)
10. Open questions and what remains unverified

---

## 1. Origin and naming history

The puzzle was invented independently in Japan around 1987. Non Ishida (a graphics editor) won a 1987 Tokyo competition with grid pictures designed using skyscraper lights, and Tetsuya Nishio (a puzzler) independently invented identical puzzles published in another magazine. [source: https://en.wikipedia.org/wiki/Nonogram] [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/history]

The English name "nonogram" was coined by James Dalgety of The Puzzle Museum in the UK, after Non Ishida. The Sunday Telegraph began publishing Non Ishida's puzzles weekly from 1990. [source: https://en.wikipedia.org/wiki/Nonogram, citing Dalgety, "Origins of Cross Reference Grid & Picture Grid Puzzles", Puzzle Museum, http://puzzlemuseum.com/griddler/gridhist.htm] [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/history]

Other names in active use: "Pic-a-Pix" (Conceptis, coined in 1994 by Dave Green and Igor Lerner); "Picross" (Nintendo, "Mario's Picross", 1995); "Hanjie" (UK); "Griddlers"; "Paint by Numbers"; "Japanese puzzles"; "Japanese crosswords". [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/history] [source: https://en.wikipedia.org/wiki/Nonogram]

This matters for citation searches: academic papers often use "Japanese puzzle" or "paint-by-number". Wolter's solver survey and the webpbn.com database both use "paint-by-number". [source: https://webpbn.com/survey/]

---

## 2. Complexity results

### 2.1 General solving is NP-complete

The foundational result is by Nobuhisa Ueda and Tadaaki Nagao: "NP-completeness results for NONOGRAM via Parsimonious Reductions", Technical Report TR96-0008, Department of Computer Science, Tokyo Institute of Technology, May 1996. The reduction proves NP-completeness via a parsimonious reduction from 3-Dimensional Matching (3DM) to NONOGRAM. [source: https://en.wikipedia.org/wiki/Nonogram, ref 5: "Ueda, Nobuhisa; Nagao, Tadaaki. NP-completeness results for NONOGRAM via Parsimonious Reductions. Technical Report TR96-0008, Department of Computer Science, Tokyo Institute of Technology, 1996. CiteSeerX:10.1.1.57.5277"] [source: https://github.com/mgfzemor/Nonogram, README: "Presents a reduction from 3DM to Nonogram"]

A "parsimonious" reduction preserves the number of solutions, so the NP-completeness result carries over to counting/uniqueness questions. [source: https://en.everybodywiki.com/Another_Solution_Problem_(ASP)] [source: Yato & Seta paper, see 2.2 below]

The Ueda-Nagao 1996 technical report itself is a preprint, not a journal publication. It is cited by name in essentially every later paper on nonogram complexity. The original is on CiteSeerX (10.1.1.57.5277). The reduction has been re-derived in several student projects (see `mgfzemor/Nonogram` GitHub repo for an implementation that constructs an explicit 3DM → Nonogram instance). [source: https://github.com/mgfzemor/Nonogram]

The 2009 Batenburg & Kosters paper (Pattern Recognition 42:1672-1683) cites Ueda & Nagao for the NP-hardness result and also notes that NP-hardness follows from the fact that "Nonograms can be considered as a generalization of the reconstruction problem for hv-convex sets in discrete tomography, which is NP-hard". They cite Woeginger, "The reconstruction of polyominoes from their orthogonal projections", Information Processing Letters 77:225-229 (2001) for that. [source: /tmp/bako2009.txt lines 7-29, ref [7] and [8] in the Constructing Simple Nonograms reference list at /tmp/constru.txt lines 1116-1118]

### 2.2 Another Solution Problem (ASP) is NP-complete

Yato & Seta defined and studied the Another Solution Problem (ASP): given an instance and a solution to it, decide whether a different solution exists. They proved ASP-completeness with respect to parsimonious reductions for Slither Link, Cross Sum and Number Place. [source: Yato, Takayuki; Seta, Takahiro. "Complexity and Completeness of Finding Another Solution and Its Application to Puzzles." IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, vol. E86-A, no. 5, pp. 1052-1060, May 2003. https://globals.ieice.org/en_transactions/fundamentals/10.1587/e86-a_5_1052/_p] [source: https://www.semanticscholar.org/paper/Complexity-and-Completeness-of-Finding-Another-and-Yato-Seta/aa8091f44bd25d23bb53fb9af6257dfeba2355dc] [source: preprint PDF: https://www-imai.is.s.u-tokyo.ac.jp/~yato/data2/SIGAL87-2.pdf]

Because the Ueda-Nagao reduction from 3DM to Nonogram is parsimonious, ASP-completeness for 3DM carries over to ASP-completeness for Nonogram. This is the formal sense in which "checking that a candidate solution is unique" is hard for the general nonogram problem. [source: https://en.everybodywiki.com/Another_Solution_Problem_(ASP)]

### 2.3 The INFERENCE problem is co-NP-complete

A more recent thesis (Aaron Foote, Wesleyan, advisor Danny Krizanc, 2024) refines the complexity picture by studying the INFERENCE problem: given a partially filled grid and the row/column clues, decide whether the value of any unfilled cell can be deduced (i.e. is the same in every solution extending the partial filling). The thesis proves INFERENCE is co-NP-complete, by reduction from Boolean unsatisfiability. [source: Foote, "On the Complexity and Threshold Behavior of Playing Nonogram Puzzles", Wesleyan Honors Thesis, April 2024, https://digitalcollections.wesleyan.edu/_flysystem/fedora/2024-07/1239_377473.pdf, Chapter 2 Theorems 1 and 2, /tmp/foote.txt lines 79-103, 841-1204] [source: companion conference paper, Foote & Krizanc, "Nonogram: Complexity of Inference and Phase Transition Behavior", arXiv:2507.07283, https://arxiv.org/html/2507.07283v1]

Practical consequence for puzzle design: if a generator wants to guarantee "every cell of the puzzle is deducible from the clues", verifying that property exactly is in general intractable. Real puzzles work around this by restricting to a subclass (see §6.1 on "simple nonograms").

### 2.4 Phase transition behavior

Foote & Krizanc also establish, experimentally, a phase transition in inferability around filled-cell density 0.39 to 0.42 for square grids: below the threshold, almost no cells are inferable; above it, almost all are. The transition sharpens as grid size grows. [source: https://arxiv.org/html/2507.07283v1, abstract and §4] [source: /tmp/foote.txt lines 2779-2937]

Practically: in published puzzles (their scraped sample is from a puzzle site), difficulty correlates with proximity to the threshold, and the puzzles with unique solutions cluster *above* the threshold (denser puzzles), since random sparse puzzles almost never have unique solutions. [source: /tmp/foote.txt lines 2885-2937, "Below the phase transition threshold, puzzles with only one solution are virtually a non-occurrence"]

### 2.5 Special cases that are polynomial

A nonogram with a single block per row (i.e. each row clue is a single integer) is equivalent to a problem in discrete tomography (DT), reconstructing an hv-convex polyomino. That special case is polynomial-time solvable. The general DT problem with just row and column linesums (the relaxation of nonograms that drops the "this is a run of length r" structure) is also polynomial via network flow. [source: Batenburg & Kosters 2009, /tmp/bako2009.txt lines 152-156, 397-417: "The DT problem can be solved in polynomial time" via transportation/network flow] [source: ref [4,5] in that paper] [source: cited Brunetti & Daurat 2003, https://doi.org/10.1016/S0304-3975(03)00050-1]

This is the basis for the "2-SAT relaxation" approach (§4.4 below): use the polynomial DT relaxation to extract pairwise constraints over pixels, then combine those constraints via 2-SAT (also polynomial), and only fall back to branching when these relaxations are exhausted.

---

## 3. Human-style deduction techniques

### 3.1 Canonical list (Wikipedia)

The Wikipedia article "Nonogram" enumerates the standard catalogue of techniques under its "Solution techniques" section. The full list of section headings, in order: Simple boxes, Simple spaces, Forcing, Glue, Joining and splitting, Punctuating, Mercury, Contradictions, Mathematical approach, Deeper recursion, Multiple rows. [source: https://en.wikipedia.org/wiki/Nonogram, "Solution techniques" section]

Each opening sentence, quoted from the article:

- **Simple boxes**: "At the beginning of the solution, a simple method can be used to determine as many boxes as possible." This is the classical *overlap rule*: a block of length r in a line of length ℓ must overlap itself when pushed leftmost vs rightmost; the overlap region is filled. [source: https://en.wikipedia.org/wiki/Nonogram]
- **Simple spaces**: "This method consists of determining spaces by searching for cells that are out of range of any possible blocks." [source: https://en.wikipedia.org/wiki/Nonogram]
- **Forcing**: "In this method, the significance of the spaces will be shown." (A known space in the middle of a line can force a block to one side or the other.) [source: https://en.wikipedia.org/wiki/Nonogram]
- **Glue**: "Sometimes, there is a box near the border that is not farther from the border than the length of the first clue." (Anchors the first/last block to the border.) [source: https://en.wikipedia.org/wiki/Nonogram]
- **Joining and splitting**: "Boxes closer to each other may be sometimes joined together into one block or split by a space." [source: https://en.wikipedia.org/wiki/Nonogram]
- **Punctuating**: "To solve the puzzle, it is usually also very important to enclose each bound or completed block of boxes [by] separating spaces." [source: https://en.wikipedia.org/wiki/Nonogram]
- **Mercury**: "Mercury is a special case of Simple spaces technique." Named after how liquid mercury pulls back from container walls: if a known box lies the same distance from a border as the first clue's length, the first cell must be a space. [source: https://en.wikipedia.org/wiki/Nonogram]
- **Contradictions**: "Some more difficult puzzles may also require advanced reasoning." (Try a cell as filled or empty, derive a contradiction, conclude the opposite.) [source: https://en.wikipedia.org/wiki/Nonogram]
- **Mathematical approach**: "It is possible to get a start to a puzzle using a mathematical technique to fill in blocks." (Sum of clue lengths plus mandatory gaps, compared against line length.) [source: https://en.wikipedia.org/wiki/Nonogram]
- **Deeper recursion**: "Some puzzles may require to go deeper with searching for the contradictions." (Nested contradiction; usually classed as computer-only territory.) [source: https://en.wikipedia.org/wiki/Nonogram]
- **Multiple rows**: "In some cases, reasoning over a set of rows may also lead to the next step of the solution." (Cross-line deduction.) [source: https://en.wikipedia.org/wiki/Nonogram]

> Note. The task brief mentioned "Wikibooks Nonograms/Solving" as a known catalogue. As of this research, `https://en.wikibooks.org/wiki/Nonograms/Solving` returns HTTP 404 [source: WebFetch attempt to that URL on May 16 2026 returned 404]. The Wikipedia "Solution techniques" section appears to be the canonical replacement and is what later writeups cite.

### 3.2 Activity Workshop tutorial (independent terminology)

An older tutorial by Activity Workshop uses a slightly different vocabulary: "Overlap", "Minimum Range", "Maximum Range", "Small Gaps", "Multiple Blocks". The semantics overlap with Wikipedia's list but the names differ. The Activity Workshop is widely linked from amateur solver guides. [source: https://activityworkshop.net/puzzlesgames/nonograms/tutorial.html]

The Overlap technique is the same as Wikipedia's Simple boxes. Minimum Range and Maximum Range correspond to Glue. Small Gaps corresponds to Simple spaces. Multiple Blocks is a specific Joining and splitting case. [source: https://activityworkshop.net/puzzlesgames/nonograms/tutorial.html, side-by-side comparison with https://en.wikipedia.org/wiki/Nonogram]

### 3.3 nonograms.org (Russian/English site) catalogue

`nonograms.org` (run by KyberPrizrak / Chugunnyy K.A. since 2009) publishes its own list under "Methods of solving Japanese crosswords": Superposition of extreme positions; Pushing off from the walls; Inaccessibility; Doesn't fit in; Division; Double positioning; Colours at intersection. [source: https://www.nonograms.org/methods] [source: site copyright statement at https://www.nonograms.org/]

These map onto Wikipedia's list (Superposition = Simple boxes / Overlap; Pushing off from walls = Glue; Inaccessibility = Simple spaces; Doesn't fit in = Joining and splitting; Division = a Forcing/Punctuating composite; Double positioning = a contradictions-lite technique; Colours at intersection is specific to multicolor variants). [source: side-by-side from https://www.nonograms.org/methods and https://en.wikipedia.org/wiki/Nonogram]

### 3.4 Conceptis Puzzles tutorial

Conceptis Puzzles documents techniques implicitly through a step-by-step walkthrough rather than naming each rule. The walkthrough explicitly covers: starting with the longest blocks; single-block overlap (same as Simple boxes); using painted squares to constrain perpendicular lines (cross-line propagation); marking empty squares; accounting for completed clues; and color-specific spacing rules for Color Pic-a-Pix. [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/techniques]

### 3.5 What "human-solvable without guessing" usually means

In the literature, "solvable by pure logic" / "without guessing" / "without trial and error" almost always means: solvable by repeated application of a **line solver** that uses only one row or column at a time, until the grid is filled. This is the "simple" class of Batenburg, Henstra, Kosters & Palenstijn (2009): "A Nonogram description is called simple if it can be reconstructed by applying a sequence of Settle operations, each time using only information from a single row or column. In other words, it is never necessary to consider information from several rows and columns simultaneously. Nearly all Nonograms that appear in puzzle collections satisfy this property." [source: /tmp/constru.txt lines 175-185, paper at https://liacs.leidenuniv.nl/~kosterswa/constru.pdf]

That definition is what Simon Tatham's Pattern generator enforces (§9), what webpbn.com calls a "good puzzle" [source: https://webpbn.com/faq.html, "any puzzle you have to solve by trial and error is defective"], and what Conceptis means by "logically solvable" [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix].

There is an important nuance: a puzzle can have a unique solution but still not be solvable by pure line-solver logic. The dom puzzles (Greifer's n-Dom benchmark on webpbn) are the classic example: every line by itself is highly underconstrained, but the combination forces a unique solution that humans solve by global reasoning. [source: https://webpbn.com/survey/dom.html, "Computers are anything but holistic thinkers, so the shortcuts used by humans are unavailable to them"] [source: https://webpbn.com/survey/dom.html, "there must be part of at least one 3 in every row"]

---

## 4. Line solvers and constraint-propagation algorithms

A nonogram solver is typically built as: (1) a **line solver** that, given a single line's clue and a partial assignment of its cells, deduces every cell value forced by that clue alone; (2) a propagation loop that re-runs the line solver on rows whose columns just changed and vice versa; (3) a fallback search when propagation stalls (probing, depth-first guessing, backtracking, or SAT/ILP).

### 4.1 Line solver: leftmost/rightmost overlap (the "fast" algorithm)

Push every block as far left as possible while respecting the clue; push every block as far right; for each cell, if both placements agree, that cell is determined. This is the standard "fast" algorithm. Steven Simpson's writeup names it directly: "pushes all blocks to their left-most positions, then to their right-most, and compares these two extremes. Where blocks overlap, solids are deduced; overlapping gaps reveal empty cells." It is fast but incomplete: it can miss some forced cells. [source: https://stevocity.me.uk/nonogram/theory]

Jan Wolter's pbnsolve uses this as its base: "Uses a 'left-right overlap algorithm' that finds leftmost and rightmost possible block placements, then intersects them to identify cells that must be specific colors". [source: https://webpbn.com/pbnsolve.html]

### 4.2 Line solver: complete enumeration

Enumerate every valid placement of the clue's blocks in the line and intersect them. Complete but exponential in the number of free positions. Simpson again: "the original algorithm is called 'complete'. It systematically finds all valid arrangements of solids, and generates a complete result from that." Worst-case complexity is O(x^n) for n blocks where x is the free space. [source: https://stevocity.me.uk/nonogram/theory]

### 4.3 Line solver: dynamic programming

The mature solution is dynamic programming on `Fix(i, j)`: whether the first i cells can adhere to the first j clue blocks. Batenburg & Kosters give the recursion explicitly (Proposition 1 in their 2009 paper), with worst-case complexity O(k · ℓ²) where ℓ is the line length and k is the number of blocks; "in practice, especially when using lazy evaluation, the complexity is much lower". The procedure that fills in all cells forced by a clue is called **Settle**. [source: Batenburg & Kosters 2009, /tmp/bako2009.txt lines 322-378, equation (1)]

For the same DP, Victor Franco Sánchez's writeup gives the recurrence R(x, i) "first x cells fillable using first i blocks", an O(n·k) variant after precomputing nearest forbidden cells, plus arc-consistency domain pruning by backward traversal of the DP table; he frames the whole solver as a Constraint Satisfaction Problem with backtracking and a "solution-count" heuristic for variable selection. [source: https://web.mat.upc.edu/victor.franco.sanchez/nonograms/]

Wu, Sun et al. (2013) give the **fast DP method** with worst-case O(k·ℓ) (one factor of ℓ better than Batenburg-Kosters). This is the line solver inside LalaFrogKK. [source: https://cgilab.nctu.edu.tw/~icwu/aigames/LalaFrogKK.html: "the fast DP method for line solving has a time complexity in the worst case of O(kl) only, where the grid size is l×l and k is the average number of integers in one constraint, in contrast to the time complexity for the best line-solving method in the past which is O(kl²)"] [source: paper PDF: https://ir.lib.nycu.edu.tw/bitstream/11536/22772/1/000324586300005.pdf]

### 4.4 Beyond line solvers: 2-SAT, DT relaxation, probing, SAT, ILP, CSP

**2-SAT + Discrete Tomography relaxation (Batenburg & Kosters 2009)**: per-line DP gives single-pixel deductions; the DT relaxation (just linesums, polynomial via network flow) gives more single-pixel and pairwise constraints; the pairwise constraints are encoded as 2-SAT clauses (which are polynomial via the dependency graph); the union of these polynomial-time techniques solves a wide class of "non-simple" nonograms without branching. [source: /tmp/bako2009.txt abstract and §3-§4, lines 14-30 and 387-499]

**Probing (Wolter, pbnsolve)**: when logic stalls, generate a list of candidate guesses, run the logic engine on each without committing, and pick the guess whose contradiction-derived deductions advance the puzzle the most. pbnsolve's "Plod & Sprint" hybrid switches between probing and depth-first search based on the rate of contradictions. [source: https://webpbn.com/pbnsolve.html] [source: pbnsolve README at https://github.com/cygy/pbnsolve/blob/master/pbnsolve/README]

**Fully probing (Wu, Sun et al.)**: a stricter version of probing where every possible cell-value is tested; used in LalaFrogKK before falling back to backtracking. [source: https://cgilab.nctu.edu.tw/~icwu/aigames/LalaFrogKK.html: "fully probing (FP) methods are used to solve more pixels before running backtracking"]

**SAT**: encode each cell as a Boolean variable, encode each clue's regular-expression constraint as a set of clauses, hand to a SAT solver. Foote 2024 uses this CNF encoding via regular expressions to make his phase-transition experiments tractable. [source: /tmp/foote.txt lines 38-43 (abstract) and Chapter 3, "we implement an efficient encoding of a Nonogram board as a boolean formula in Conjunctive Normal Form (CNF) through the use of regular expressions"] [source: tsionyx/nonogrid offers an optional SAT-solver feature: "Optional SAT solver uses results of previous phases to more effectively explore solution space", https://github.com/tsionyx/nonogrid]

**ILP**: two examples in Wolter's survey use integer programming: Robert Bosch's GLPK-based IP solver, and Andrew Makhorin's GLPK MathProg example. [source: https://webpbn.com/survey/, "IP Solver (Robert Bosch) - C/GLPK", "Example IP Solver (Andrew Makhorin) - MathProg/GLPK"]

**General CSP / constraint programming**: several solvers express the puzzle as a CSP and use off-the-shelf solvers: Gecode (Mikael Lagerkvist), MiniZinc with Gecode or G12 Lazyfd backends (Hakan Kjellerstrand), JaCoP (Java), Copris (Naoyuki Tamura, Scala on top of SAT). The MiniZinc/G12 Lazyfd JaCoP solver in particular solved every puzzle in the full 2,491 webpbn black-and-white set in under 15 minutes, unique among the surveyed solvers at the time. [source: https://webpbn.com/survey/] [source: https://www.hakank.org/constraint_programming_blog/2010/03/survey_of_nonogram_solvers_upd.html]

**Dancing Links (DLX)**: Knuth's exact-cover algorithm can encode nonogram solving but the encoding is large, so dedicated solvers outperform it. The TypeScript `dlxlib-demos` package by taylorjg demonstrates the encoding for nonogram and several other puzzles. [source: https://github.com/topics/nonogram-solver, repo description: "React/TypeScript web app demonstrating Dancing Links algorithm across multiple puzzle types including nonograms"] [source: WebSearch result: "Knuth's dancing-links method can be used to solve nonograms, but unfortunately, the sizes of the translated problems are usually too large to solve efficiently"]

**Genetic algorithms**: documented but generally inferior to dedicated logic-based solvers; covered in Salcedo-Sanz et al. (2007) "Solving Japanese Puzzles with Heuristics" (IEEE CIG 2007). [source: https://www.semanticscholar.org/paper/Solving-Japanese-Puzzles-with-Heuristics-Salcedo-Sanz-Ort%C3%ADz-Garc%C3%ADa/1e6c8cd4a8e72ec3abd1ce3cbf20c4366a007453]

---

## 5. Survey of open-source nonogram solvers

The single best comparative reference is **Jan Wolter's Survey of Paint-by-Number Puzzle Solvers** at https://webpbn.com/survey/. It benchmarks 23 solvers on (a) 30 hand-picked puzzles, (b) all 2,491 black-and-white puzzles on webpbn as of Oct 2009, (c) 3,232 multicolor puzzles, and (d) 5,000 randomly generated 30×30 puzzles. Test machine: 2.6GHz AMD Phenom II X4 810, 8GB RAM, OpenSUSE 11.2, gcc 4.4.1 -O2. [source: https://webpbn.com/survey/]

> Caveat on dates. The Wolter survey was last updated September 25, 2013 [source: https://en.wikipedia.org/wiki/Nonogram, reference 9]. It does not include solvers developed later (e.g. LalaFrogKK's 2013 paper, Requiem 2019, the TAAI tournament winners after 2011, tsionyx's pynogram/nonogrid). For the post-2013 landscape the best survey is informal: the Wikipedia article's "Notable Algorithms & Solvers" section [source: https://en.wikipedia.org/wiki/Nonogram] and the GitHub topic pages [source: https://github.com/topics/nonogram-solver, https://github.com/topics/nonogram].

### 5.1 The 23 solvers in Wolter's survey

Listed by category, with language [source: https://webpbn.com/survey/]:

Dedicated stand-alone solvers (13): pbnsolve (Wolter, C), Nonogram Solver (Mirek & Petr Olšák, C), Nonogram Solver (Steve Simpson, C99), Ben-Gurion University Solver (Java), Naughty (Kuang-che Wu, C++), JSolver (Evgeniy Syromolotov, C++), Nonogram Solver (Jakub Wilk, C), Games::Nonogram (Kenichi Ishigaki, Perl), Nonogram Solver (Richard Wareham, C#), Paint by Numbers Solver (Vladimir Sukhoy, C++), Nonogram Solver (Kyle Keen, Python), Solver (Frans Faase, C++), Nonogram Solver (Yuvai Lando, Racket).

Constraint-programming / general-purpose (7): Gecode Nonogram Example (C++/Gecode), MiniZinc Nonogram Solver (Gecode), MiniZinc Nonogram Solver (G12 Lazyfd), IP Solver (Bosch, C/GLPK), IP Solver (Makhorin, MathProg/GLPK), Copris Nonogram Solver (Tamura, Java), Copris Multicolor Solver (Wolter, Java).

Embedded solvers (3): Griddlers Solver (Simlovic), QNonograms (Meshcheryakov), webpbn.com Javascript Helper (Wolter).

### 5.2 Uniqueness checking

Wolter is explicit: "Only two solvers were 'consciously designed as validators': pbnsolve and the Ben-Gurion University Solver. The document notes that 'a validator must try to find a second' solution, requiring complete exploration of the search space rather than stopping after finding one solution." [source: https://webpbn.com/survey/, paraphrased]

This matters for puzzle generators: if you re-use any other solver in a generation loop, you need to confirm it actually searches for a second solution after finding the first; many solvers stop at the first.

### 5.3 Notable solvers in detail

**pbnsolve (Jan Wolter, C, Apache 2.0)** is the reference solver for the field. Algorithms: Line Solver (left-right overlap), Cache Line Solver (hash table of previous results, 80%-90% cache hit rates on large puzzles), Exhaustive Check, Contradiction Check (looks "a couple levels down"), Guessing with heuristics G1-G6 (default G4, "based on the heuristic functions used by Steve Simpson's solver"), Probing P1-P4, hybrid Plod & Sprint. Build uses libxml2 and gcc -O2 ("makes pbnsolve runs more than twice as fast"). Inputs: XML, .NON, .MK, .G, .NIN, .CWD, .LP, PBM. [source: https://webpbn.com/pbnsolve.html] [source: pbnsolve README at https://github.com/cygy/pbnsolve/blob/master/pbnsolve/README]

The pbnsolve source is on Google Code originally; GitHub mirrors include `cygy/pbnsolve` and `avi-levy/pbnsolve` ("Automatically exported from code.google.com/p/pbnsolve"). [source: https://github.com/cygy/pbnsolve] [source: https://github.com/avi-levy/pbnsolve]

The `FiveLakesStudio/PicrossSolver` repository wraps pbnsolve specifically for unique-solution validation, exposing the `-u` flag and reporting "UNIQUE DEPTH-%d SOLUTION", "UNIQUE LINE SOLUTION", or "FOUND MULTIPLE SOLUTIONS". [source: https://github.com/FiveLakesStudio/PicrossSolver]

**Steve Simpson's solver (C99)** at Lancaster University: implements both the fast algorithm and the complete algorithm, and a hybrid "fcomp" combining their strengths. Also implements an "Olšák" line solver (a variant where, after the fast pass, the algorithm makes targeted local guesses inside the line to reach completeness while staying fast). When deterministic deduction is exhausted, it bifurcates: pairs of guesses on a cell, with backtracking. [source: https://stevocity.me.uk/nonogram/theory] [source: https://stevocity.me.uk/nonogram/ls-olsak]

> Note. Steve Simpson's site was previously hosted under lancaster.ac.uk; the current canonical URL is https://stevocity.me.uk/nonogram/. Old links into `www.comp.lancs.ac.uk/~ss/nonogram/links.html` are dead. The Lancaster URL is the one cited by the Batenburg-et-al 2009 paper [source: /tmp/constru.txt reference [6]] but content has moved.

**Petr & Mirek Olšák's solver (C, GPL)**: "linesolver which gets most of the logically available information quickly, then gets the rest by closer inspection". Like the fast algorithm but, where the two extremes agree (i.e. the cell looks undetermined), it makes an in-line conjecture for the opposite state and checks for inconsistency. If inconsistent, eliminate the guessed state. Almost as fast as the pure fast algorithm but complete in many cases. Only solver in the survey besides pbnsolve that handles multicolor and triddler puzzles. [source: https://stevocity.me.uk/nonogram/ls-olsak] [source: https://webpbn.com/survey/]

**BGU Solver (Berend, Pomeranz, Rabani, Raziel; Java)** published as Berend, Pomeranz, Rabani, Raziel, "Nonograms: Combinatorial questions and algorithms", Discrete Applied Mathematics 169:30-42 (2014). Excels on hard puzzles and on random puzzles: "second place on Webpbn human-designed puzzles and first place on random puzzles" in Wolter's survey. Released as a runnable JAR (`bgusolver.jar`) with CLI and GUI modes. [source: https://cris.bgu.ac.il/en/publications/nonograms-combinatorial-questions-and-algorithms/] [source: https://www.sciencedirect.com/science/article/pii/S0166218X14000080] [source: WebSearch result citing the BGU project page; the page itself (https://www.cs.bgu.ac.il/~berend/nonograms/) returned 403 in this research, but its existence is confirmed by multiple secondary citations including pynogram's README and the Wolter survey]

**Naughty (Kuang-che Wu, C++, Apache 2.0)**: bit-vector line solver (both fast heuristic and DP variants), line-solver result caching, 2-depth contradiction analysis, one-level min-max ordering. Versions v20 → v85 (2nd place group A, 3rd group B at TAAI 2011) → v88 (first public release). [source: http://kcwu.csie.org/~kcwu/nonogram/naughty/] [source: http://kcwu.csie.org/~kcwu/nonogram/taai11/]

Kuang-che Wu also maintains a curated bibliography of nonogram academic papers at http://ref.kcwu.csie.org/nonograms/. [source: http://kcwu.csie.org/~kcwu/nonogram/naughty/]

**LalaFrogKK (Chen, Kuo, Kang, Sun, Wu; C++)** at https://github.com/CGI-LAB/Nonogram, paper "An Efficient Approach to Solving Nonograms" by I-Chen Wu et al., IEEE Transactions on Computational Intelligence and AI in Games (2013). Three parts: line-solving propagation, fully probing, backtracking. Line solver is O(k·ℓ) DP. "Won all the champions of all Computer Olympiad/TAAI/TCGA Nonogram tournaments since TAAI 2011 and till Computer Olympiad 2015". [source: https://cgilab.nctu.edu.tw/~icwu/aigames/LalaFrogKK.html] [source: https://github.com/CGI-LAB/Nonogram] [source: paper PDF at https://ir.lib.nycu.edu.tw/bitstream/11536/22772/1/000324586300005.pdf]

### 5.4 Top GitHub repos (sorted by stars), May 2026

From the GitHub topic page `nonogram` sorted by stars [source: https://github.com/topics/nonogram?o=desc&s=stars]:

1. **HandsomeOne/Nonogram** (TypeScript, 150 stars) — editor + solver + game library, no dependencies. Includes random generator via `Editor.refresh()`. README does not document the solver algorithm explicitly and does not document uniqueness checking. [source: https://github.com/HandsomeOne/Nonogram]
2. **Izaron/Nonograms** (C++, 62 stars) — "very fast japan crosswords (aka nonograms) solver and generator", supports color and image-to-puzzle conversion, ImageMagick dependency. Solver algorithm not documented in the README itself; a blog post is linked. [source: https://github.com/Izaron/Nonograms]
3. **halfburnttoast/Dungeon-Cross** (Python, 35 stars) — reimplementation of Zachtronics' "Dungeons and Diagrams" (a nonogram variant). [source: https://github.com/topics/nonogram?o=desc&s=stars]
4. **tsionyx/nonogrid** (Rust, 32 stars) — line solver + propagation, probing phase computing P = N + R + C (neighbors + row solution rates + column solution rates) for cell-priority, optional SAT solver via feature flag, supports TOML, XML (webpbn), and nonograms.org formats. Web build at https://tsionyx.github.io/nono/. Multi-solution finder. [source: https://github.com/tsionyx/nonogrid]
5. **tsionyx/pynogram** (Python, 32 stars) — same author, Python sibling. Implements line solver, references "BGU Nonograms Project", relaxation methods, finite-state automata approach, and Wolter's pbnsolve techniques. Supports webpbn.com and nonograms.org as remote puzzle sources, ncurses real-time visualization, SVG output. [source: https://github.com/tsionyx/pynogram]
6. **SmilingWayne/PuzzleSolver** (Python, 29 stars) — 100+ logic-puzzle solvers via OR-Tools, includes nonogram. [source: https://github.com/topics/nonogram?o=desc&s=stars]

From the `nonogram-solver` topic [source: https://github.com/topics/nonogram-solver]:

1. **tsionyx/pynogram** and **tsionyx/nonogrid** (32 stars each, both above)
2. **pierre-dejoue/picross-solver** (C++, 10 stars) — C++17 library, CMake, optional Catch2 (tests) and pnm++ (PBM image I/O). Categorises puzzle difficulty as LINE (line-solvable only), BRANCH (needs backtracking), or MULT (multiple solutions). Validates solution uniqueness. Supports Simpson's .NON, Wilk's .NIN, native format, and PBM. Has CLI and GUI applications. [source: https://github.com/pierre-dejoue/picross-solver]
3. **fedimser/nonolab** (Java, 6 stars) — creation, solving, and analysis tools.
4. **taylorjg/dlxlib-demos** (TypeScript, 6 stars) — demonstrates Dancing Links across multiple puzzles including nonograms.
5. **sofianedjerbi/NonogramSolver** (Python, 5 stars) — SAT-solver approach.

### 5.5 Uniqueness/human-solvability classification: who does what

| Solver | Lang | Line solver | Search | Uniqueness | "Human-solvable" classification |
|---|---|---|---|---|---|
| pbnsolve | C | left-right overlap + cache | probing + DFS | Yes (validator mode) | Reports LINE vs DEPTH-k solution. [source: https://github.com/cygy/pbnsolve/blob/master/pbnsolve/README] |
| BGU Solver | Java | DP + DT + 2-SAT relaxation | search | Yes (validator) | Implicit (paper distinguishes "simple") |
| Simpson nonogram | C99 | complete / fast / fcomp / olsak | bifurcation + backtracking | Not explicitly documented as a validator | n/a [source: https://stevocity.me.uk/nonogram/theory] |
| Olšák solver | C | fast + local conjectures | unknown | Multicolor capable | n/a [source: https://stevocity.me.uk/nonogram/ls-olsak] |
| LalaFrogKK | C++ | O(k·ℓ) DP | fully probing + backtracking | Optimized for speed, not validation focus | n/a [source: https://cgilab.nctu.edu.tw/~icwu/aigames/LalaFrogKK.html] |
| Naughty | C++ | bit-vector fast + DP | 2-depth contradiction | Yes (uniqueness check option) | n/a [source: http://kcwu.csie.org/~kcwu/nonogram/naughty/] |
| pierre-dejoue/picross-solver | C++ | iterate rows/cols | backtracking | Yes (validates uniqueness) | Explicit: LINE / BRANCH / MULT categories [source: https://github.com/pierre-dejoue/picross-solver] |
| tsionyx/nonogrid | Rust | line + propagation | probing → optional SAT → backtracking | Yes (multi-solution finder) | n/a [source: https://github.com/tsionyx/nonogrid] |
| Tatham Pattern | C | recursive enumeration | line-only, no branching | Implicit (generator only keeps line-solvable) | Explicit: only line-solvable puzzles are kept (§9) |

The picross-solver `LINE / BRANCH / MULT` taxonomy is one of the cleanest explicit classifications of human-solvability among open-source solvers. [source: https://github.com/pierre-dejoue/picross-solver]

---

## 6. Generator techniques

### 6.1 The standard pipeline: random fill → derive clues → solve → check

The dominant pattern in published academic generators and in open-source code:

1. Generate a candidate filled grid (random pixels, possibly biased toward clustered regions; or driven from a source image).
2. Compute row/column clues directly from the grid by run-length encoding.
3. Run a deterministic line-solver-only solver on the clues from a blank starting grid.
4. If the line solver completes the grid (i.e. the puzzle is line-solvable), accept; else discard or perturb and retry.

This is essentially what Simon Tatham's Pattern does (§9) and what Batenburg, Henstra, Kosters & Palenstijn describe in "Constructing Simple Nonograms of Varying Difficulty" (2009). [source: /tmp/constru.txt] [source: pattern.c at https://raw.githubusercontent.com/samuellwn/puzzles/master/pattern.c]

A subtle but crucial point: step 3 must reject puzzles that need any guessing/branching, *not* just puzzles with no solution. The reason: a non-simple puzzle can still have a unique solution but require search to find it. For a casual puzzle game targeting humans, "unique solution" is necessary but not sufficient. "Line-solvable" (Batenburg's simple class) is the practical target. [source: /tmp/constru.txt lines 175-185]

### 6.2 Batenburg, Henstra, Kosters & Palenstijn (2009) "Generate" and "Vary"

The algorithm is parameterised on a grey-level input image P (so the generated puzzles resemble a picture) and a set L of previously generated puzzles (so successive puzzles look different). Pseudo-code [source: /tmp/constru.txt Figures 7 and 8]:

```
Generate(P, L):
  p ← Init(P);                              -- e.g. threshold or edge-detect
  U ← FullSettle(p);                        -- set of cells still unknown after line-solver
  while U ≠ ∅:                              -- not line-solvable yet
    p ← Adapt(p, U, P, L);                  -- flip one unknown cell to 1 to make it more solvable
    U ← FullSettle(p)
  return (p, Difficulty(p))

Adapt(p, U, P, L):                          -- choose which 0→1 flip to make
  for each (i,j) in U (random order):
    if p[i][j] == 0:
      tentatively flip; score = α·|FullSettle(p_new)| + β·P[i][j] + γ·Σ_{L∈L} L[i][j]
      keep best
  apply best flip
```

`α`, `β`, `γ` are non-negative parameters. α prefers grids with few remaining unknowns (more solvable). β prefers pixels that are dark in the source image (resemblance). γ prefers pixels that were white in previously generated puzzles (diversity). [source: /tmp/constru.txt lines 868-893]

`Vary(p, P, L, depth)` is a variant that does up to `depth` extra 0→1 flips after each successful Generate, recording every line-solvable puzzle it passes through, to give the user a range of difficulties. [source: /tmp/constru.txt lines 894-916]

The output of Batenburg-et-al on standard images (e.g. an apple, Alan Turing's portrait) is shown in their paper with annotated difficulties (e.g. 15, 16, 22 sweeps for Turing portraits at 30x38). [source: /tmp/constru.txt Figures 10, 12, 13 and surrounding text]

### 6.3 Roucairol & Cazenave (2024) "Generating Difficult and Fun Nonograms"

A different optimization regime: the generator is a tree search over rectangle-flip moves (swap the value of every cell in some chosen rectangle), using Monte-Carlo Tree Search variants (UCT, RAVE, NMCS, LNMCS, NRPA) and deterministic baselines (BFS, BEAM). The score function is a hand-written "difficulty" or "fun" metric computed by running a human-like solver and recording metrics. [source: /tmp/nonogram2024.txt §3, lines 177-235]

Key choices:

- **Move set**: flip the value of every cell in a randomly chosen rectangle. "This simple single move allows the search algorithms to reach diverse grids in fewer moves than setting the value of each cell." [source: /tmp/nonogram2024.txt lines 188-197]
- **Solver**: a line-solver-with-overlap that mimics human play. It uses a stack of rows/cols last modified, processes them, and only falls back to "edge solving" (a deterministic-guessing technique) when no line move is found. Crucially, the authors do not allow nested deterministic guessing: "If a nonogram is solvable but necessitates the use of nested deterministic guessing it is deemed unsolvable by the solver, and discarded during the generation process. This is not a problem since deterministic guessing is almost never used in most nonogram games, and never in a nested fashion to the best of our knowledge." [source: /tmp/nonogram2024.txt lines 157-167]
- **Difficulty score**: `difficulty(N) = n(N) + g(N) · 50 + sqrt(d(N)) · 10`, where n = number of steps, g = number of deterministic guesses used, d = number of times the solver had to backtrack to a faraway row/col. The coefficient 50 reflects that "a long backtracking is approximately 10 times more complex and time-consuming for a human than executing moves found directly. A deterministic guessing can be simple or very hard". [source: /tmp/nonogram2024.txt lines 351-365]
- **Fun score**: `fun(N) = 4 · b(N) · w(N) / s(N)² − k(N)·u(N) + 5 − max(d(N),5) − g(N)²`, where b/w = black/white cell counts, s = grid size, k = kurtosis of move-length distribution, u = number of unique move lengths. Strongly penalizes deterministic guessing (`g²`). Goal: produce puzzles that are not just hard but enjoyable. [source: /tmp/nonogram2024.txt lines 438-457]
- **Results**: in 60s per puzzle on a single Core i5-13600K, MCTS variants (UCT, RAVE, LNMCS) consistently produced harder puzzles than BFS/BEAM. At 15×15 the standard deviation of difficulty is high (≈30), suggesting the algorithm is at its limit. [source: /tmp/nonogram2024.txt §4, lines 251-318]
- **Code**: https://github.com/RoucairolMilo/nonoGen [source: /tmp/nonogram2024.txt line 601-602]

This paper is the closest thing in the literature to a generator that explicitly optimizes for *player experience* rather than just unique-solution-existence.

### 6.4 Simon Tatham's Pattern generator (loop-until-line-solvable)

Tatham's approach is simpler than the academic ones, and ships in a widely-used puzzle pack. The structure of `generate_soluble()` in `pattern.c` [source: https://raw.githubusercontent.com/samuellwn/puzzles/master/pattern.c, lines 641-703]:

```
do {
  ntries++;
  generate(rs, w, h, grid);     -- random + cellular-automaton bias, then 50/50 threshold
  if any row or column is solid black or solid white (and w>2 / h>2):
    continue;                   -- too easy, retry
  ok = solve_puzzle(NULL, grid, ...);  -- pure line-solver-only solver, no branching
} while (!ok);
```

`generate()` itself starts uniformly random, then applies one step of a smoothing cellular automaton ("set each square to the average of the surrounding nine cells") to "gently bias this in favour of some reasonably thick areas of white and black, while retaining some randomness and fine detail", then thresholds at the median value so half the cells are black [source: pattern.c lines 242-322].

`solve_puzzle()` is pure line solving with no branching: "Process rows/columns individually. Deductions involving more than one row and/or column at a time are not supported. Take care to only process rows/columns which have been changed since they were previously processed. Also, prioritize rows/columns which have had the most changes since their previous processing, as they promise the greatest benefit." [source: pattern.c lines 569-577]

`do_row()` calls `do_recurse()`, which "basically tries all possible ways the given rows of black blocks can be laid out in the row/column being examined. Special care is taken to avoid checking the tail of a row/column if the same conditions have already been checked during this recursion. The algorithm also takes care to cut its losses as soon as an invalid (partial) solution is detected." [source: pattern.c lines 356-417]

What this means: **every Tatham puzzle is guaranteed solvable by pure single-line deduction with no guessing**. The retry-until-line-solvable loop trades CPU at generation time for trivial solvability for the player. This is the simplest, most robust pattern in the literature and is likely what most casual puzzle apps actually do. [source: full pattern.c analysis above, especially the loop at lines 660-695]

Default sizes: 10×10, 15×15, 20×20, 25×25, 30×30 (the last two omitted on SLOW_SYSTEM). [source: pattern.c lines 74-82]

### 6.5 Other reported generator approaches

- **Ortiz-Garcia, Salcedo-Sanz, Leiva-Murillo, Perez-Bellido, Portilla-Figueras (2007)**: "Automated generation and visualization of picture-logic puzzles", Computers and Graphics 31:750-760. Cited by Batenburg et al for the related problem of constructing uniquely-solvable nonograms. [source: /tmp/constru.txt reference [3], lines 1107-1109]
- **Salcedo-Sanz et al. (2007)** at IEEE CIG: heuristic + genetic algorithms for solving and constructing. [source: https://www.semanticscholar.org/paper/Solving-Japanese-Puzzles-with-Heuristics-Salcedo-Sanz-Ort%C3%ADz-Garc%C3%ADa/1e6c8cd4a8e72ec3abd1ce3cbf20c4366a007453]
- **`Izaron/Nonograms` (C++)** advertises a generator alongside the solver but the README does not describe the generator algorithm; the linked blog post would presumably have detail. [source: https://github.com/Izaron/Nonograms]
- **`HandsomeOne/Nonogram` (TS)** `.refresh()` method "Randomly generates the grid" with a tunable threshold; no documented uniqueness check. [source: https://github.com/HandsomeOne/Nonogram]

### 6.6 Generation from images: thresholding and edge detection

When the input is a picture (so the puzzle resembles something recognisable), the canonical preprocessing pipeline before solver-based filtering is:

1. Reduce to greyscale.
2. Apply a threshold (Batenburg et al target ~35% black) or an edge detection filter.
3. Optionally remove rows/columns that are entirely empty (they make the puzzle visually less interesting and trivially constrained). [source: /tmp/constru.txt Figures 10, 12, 13 and surrounding text, lines 916-975]

webpbn.com explicitly recommends in its FAQ: "recognizable imagery with white space", "puzzles should depict something identifiable and include substantial blank areas to remain interesting", and "using fewer colors is preferable, particularly favoring two-color black-and-white designs". [source: https://webpbn.com/faq.html]

---

## 7. Difficulty rating methods

There is no universal scale. Five distinct approaches appear in the literature.

### 7.1 Sweeps to solve (Batenburg, Henstra, Kosters & Palenstijn 2009)

For simple-class puzzles, run the line-solver alternating horizontal and vertical sweeps; count sweeps to completion. Difficulty bounded above by m·n + 1 since each sweep (except possibly the first) must fix at least one new pixel. They prove the upper bound (1/2)·m·n is achievable asymptotically and exhibit explicit families reaching it. [source: /tmp/constru.txt Figure 2 (Difficulty algorithm), lines 192-201, Theorem 4.5 lines 498ff]

Empirical observation: difficulty distribution is heavily skewed toward low values, but a small fraction of puzzles is much harder. For 6×6 puzzles, 70.76% of images yield a simple-type puzzle; average difficulty is 4.51, maximum is 26. [source: /tmp/constru.txt lines 235-238]

Sweeps are easy to compute and order-independent (modulo the choice to start with rows or columns, which differs by at most 1). [source: /tmp/constru.txt lines 224-229]

### 7.2 Total solver propagations / steps (Foote 2024)

The Foote thesis (which uses a SAT-based solver internally) measures "propagations-per-tile" rather than total propagations, so the metric is size-agnostic. Empirically, sampled-from-the-web puzzles with player-rated difficulty levels {2, 3, ..., 9} show monotonically increasing average propagations-per-tile (31, 50, 68, 92, 107, 120, 147, 166), with ANOVA significance for differences between every consecutive pair except {8, 9}. [source: /tmp/foote.txt lines 3110-3196]

### 7.3 Combined metric (Roucairol & Cazenave 2024)

`difficulty = n + 50·g + 10·sqrt(d)`. n = number of basic line-solver steps; g = number of times the human-like solver had to apply edge-solving (a deterministic-guessing technique); d = number of times the solver had to "backtrack" to a row/column that is not in the vicinity of the last cell modified (a proxy for the cognitive cost of attention-switching). [source: /tmp/nonogram2024.txt lines 351-365]

The point of this metric is to reflect *player experience*. Tediousness (lots of trivial line moves) is rated low; cognitive complexity (guessing, attention switches) is rated high.

### 7.4 Time to solve (raw)

The simplest signal: the wall-clock time the solver takes on the puzzle. Used as both a generator objective and a difficulty proxy in Roucairol & Cazenave 2024 [source: /tmp/nonogram2024.txt lines 245-262] and in Wolter's solver survey [source: https://webpbn.com/survey/].

This is a crude metric for human difficulty (computers and humans find different things hard, witness the n-Dom puzzles, §3.5) but it is unambiguous.

### 7.5 Player community ratings

The webpbn.com site collects community ratings; nonograms.com / Conceptis assign internal difficulty stars. No published documentation of how Conceptis or Easybrain assign their difficulty stars. They state only that "puzzles have a unique solution" and "are top quality" and that they have "different difficulty levels". [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix] [source: https://easybrain.com/nonogram] [source: webpbn community ratings: https://webpbn.com/faq.html]

The Foote thesis's empirical study uses these community ratings as ground truth and shows they correlate well with propagations-per-tile (§7.2). [source: /tmp/foote.txt lines 3193-3199]

---

## 8. Commercial references

### 8.1 Conceptis Puzzles (Pic-a-Pix)

Conceptis is the most-cited commercial publisher of nonograms. Founded in Israel; the founders are Dave Green (American, executive) and Igor Lerner (algorithm/engineering). Green encountered the puzzle in Tokyo in 1994; he and Lerner "develop[ed] the computer algorithm" and "invent[ed] the name Pic-a-Pix". [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/history]

Conceptis is explicit that they use computer assistance but also that algorithms alone are not enough. Dave Green, in the founders interview at https://www.conceptispuzzles.com/index.aspx?uri=info/article/111: "The software algorithm element is only a small, albeit crucial part of the puzzle creation process. Thanks to it, our artists and creative staff can create puzzles that are more beautiful and more sophisticated, in a shorter period of time." [source: https://www.conceptispuzzles.com/index.aspx?uri=info/article/111]

Conceptis claims their puzzles are "manually created by artists" and have unique solutions [source: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix]. No further technical detail is publicly available about their algorithm. Multiple research-style queries on the Conceptis site, blog, and via Google did not produce a documented description of their generator or solver. [source: WebSearch query "Dave Green Conceptis interview puzzle algorithm Pic-a-Pix" returned only marketing/articles, not technical pieces, https://www.conceptispuzzles.com/index.aspx?uri=info/article/111 is the closest]

### 8.2 Nonogram.com (Easybrain)

The mobile app `Nonogram.com` is owned and operated by Easybrain (Cyprus / Belarus), released June 26, 2019 [source: https://apps.apple.com/us/app/nonogram-com-number-games/id1452992954] [source: https://easybrain.com/nonogram] [source: https://easybrain.fandom.com/wiki/Nonogram.com — but this fandom URL returned 403 in this research, so the existence is from the App Store and Easybrain corporate site only].

Easybrain does not publish any technical description of how their puzzles are generated. The marketing copy claims "thousands of challenging griddlers", "daily challenges", "seasonal events" [source: https://easybrain.com/nonogram], but no algorithmic details, no developer interviews, no GDC-style talk could be located. WebSearch queries on `Easybrain Tigris owner` did not yield technical sources. [source: WebSearch "nonograms.com Easybrain Tigris owner mobile app", no relevant technical hits]

Note: a separate domain `nonograms.com` (no `.com` suffix vs Easybrain's `Nonogram.com`) is sometimes confused with this app. The brief refers to `nonograms.com`; this is most likely a reference to the Easybrain product but could also be `nonograms.org` (KyberPrizrak), which is a long-running Russian community site [source: https://www.nonograms.org/, copyright "© 2009-2026 Chugunnyy K.A."]. nonograms.org publishes its solving methods catalogue (§3.3) but again no documented generator.

### 8.3 Picross S (Jupiter)

Jupiter Corporation is the developer of Nintendo's Picross series since 1995 (Mario's Picross, Game Boy). They continue to self-publish the Picross S series on Switch. In a 2023 VGC interview, managing director Norichika Meguro was asked about the design philosophy ("Do you have the idea of the item in your head, or do you make the puzzle first then think, 'oh, that looks like a car'?") and responded that it was "a very philosophical question, and a difficult one to answer", then pivoted away. [source: https://www.videogameschronicle.com/features/picross-developer-jupiter-on-nearly-30-years-of-puzzling-prowess/]

No technical detail on Jupiter's pipeline is publicly available. Their puzzles are widely understood to be hand-authored (every Picross S game ships hundreds of unique, themed puzzles) but this is not explicitly documented in the available sources. **Unverified.**

### 8.4 webpbn.com (Web Paint-by-Number)

A community / database / archive run by Jan Wolter at https://webpbn.com/. The site hosts puzzles uploaded by users; provides validator services through the on-server pbnsolve; offers a small Javascript "helper" for in-browser line solving; and publishes the FAQ that articulates the community's quality standards. [source: https://webpbn.com/] [source: https://webpbn.com/faq.html]

The most-cited quote from webpbn for puzzle design is: "any puzzle you have to solve by trial and error is defective". And: "It's very easy to create puzzles that can have more than one different solution. This is undesirable because such puzzles cannot be solved by pure logic, they require guessing." [source: https://webpbn.com/faq.html]

webpbn does not categorically rate difficulty numerically; community ratings and flags ("question marks on the puzzle list") indicate problematic puzzles. [source: https://webpbn.com/faq.html]

### 8.5 nonograms.org (KyberPrizrak)

Run by Chugunnyy K.A. (handle "KyberPrizrak") since 2009 at https://www.nonograms.org/. Mix of user-submitted and curated puzzles, with explicit quality assurance: "all of them have no mistakes and have only one solution achieved without any 'guessing'". Features automatic mistake-checking and a "smart" hint system "that follow[s] solving logic rules". Method catalogue in §3.3. [source: https://www.nonograms.org/]

### 8.6 Pictopix (Tomlab)

Pictopix is a desktop nonogram game; referenced from the Wikipedia article via a Rock, Paper, Shotgun review. [source: https://en.wikipedia.org/wiki/Nonogram, reference 4: Walker, John. "Wot I Think: Fantastic picross puzzler Pictopix", Rock, Paper, Shotgun, January 12, 2017. https://www.rockpapershotgun.com/2017/01/12/pictopix-review/]

No detailed dev interview located. **Unverified** beyond the existence and reception.

### 8.7 What is NOT publicly documented

For the design of this project, the practical situation is: the *engine* of every major commercial nonogram app appears to be undocumented externally. There is no published GDC talk, no technical blog post from Conceptis / Easybrain / Jupiter explaining their pipelines. The academic literature (Batenburg, Wu, Roucairol, Foote) is the only source of detailed information on generation and difficulty rating. The open-source code (Simon Tatham, pbnsolve, picross-solver, tsionyx) is the only direct evidence of working pipelines.

This is a known gap; the only way to fill it would be direct contact with the studios, and there is no guarantee they would share their pipeline.

---

## 9. Simon Tatham's "Pattern" puzzle (source-level analysis)

This section is direct analysis of the source code, since it is the most accessible and well-documented public implementation of a complete generator + solver for the simple class. The source is in `pattern.c` of Simon Tatham's Portable Puzzle Collection, MIT licensed.

- Canonical home: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/
- Web playable Pattern: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/pattern.html
- Documentation: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/doc/pattern.html
- Source git: https://git.tartarus.org/?p=simon/puzzles.git (returned 403 to WebFetch; mirror at https://github.com/ghewgill/puzzles works)
- Raw source used in this analysis: https://raw.githubusercontent.com/samuellwn/puzzles/master/pattern.c (downloaded to /tmp/pattern.c, 2,255 lines)

### 9.1 Documented design

Tatham's documentation states: "Pattern, also known as nonograms, is a logic puzzle where players fill a grid with black or white squares. Beside each row of the grid are listed, in order, the lengths of the runs of black squares on that row; above each column are listed, in order, the lengths of the runs of black squares in that column." [source: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/doc/pattern.html]

He notes that the puzzle was "first encountered around 1995 under the nonogram name" and that "Unlike traditional versions that reveal pictures upon completion, this implementation generates random patterns, which has an unexpected benefit: players must rely on logical deduction rather than visual pattern recognition." This is an explicit design statement: the picture-recognition aspect is *removed* so the only way to win is by deduction. [source: same]

The only parameters are width and height. [source: same]

### 9.2 Generator (`generate_soluble`)

The generator's core loop, in `pattern.c` [source: /tmp/pattern.c lines 641-703]:

```c
static unsigned char *generate_soluble(random_state *rs, int w, int h) {
    /* ... */
    do {
        ntries++;
        generate(rs, w, h, grid);
        /* reject if any row or col is entirely black or entirely white,
           unless w<=2 / h<=2 because then it's impossible to avoid */
        if (!ok) continue;
        ok = solve_puzzle(NULL, grid, w, h, matrix, workspace,
                          changed_h, changed_w, rowdata, 0);
    } while (!ok);
    /* ... */
}
```

This is the textbook "random fill → derive clues → solve → keep iff solve succeeds" pipeline of §6.1, with the solver being line-solver-only (no branching), so by construction every puzzle that ships is line-solvable. No explicit uniqueness check is needed: the line solver always returns a *unique* solution when it succeeds, because it derives every forced cell.

### 9.3 Random fill (`generate`)

[source: /tmp/pattern.c lines 242-322]. Two stages:

1. Uniform random in `[0, 1)` per cell.
2. One smoothing step: each cell becomes the mean of its 3×3 neighbourhood (with a special case for 2×n grids to avoid identical rows). "We want to gently bias this in favour of some reasonably thick areas of white and black, while retaining some randomness and fine detail."

Then a threshold at the median value so exactly half the cells are black (or as close as the integer count permits). This is significant: it sets the density at the 50% mark, which is well above Foote's 0.39-0.42 phase transition, ensuring most puzzles are inferable. [source: /tmp/pattern.c lines 311-319]

### 9.4 Line solver (`solve_puzzle`, `do_row`, `do_recurse`)

[source: /tmp/pattern.c lines 485-637]. The structure:

- For each row/column, count how many cells *must* be deduced from the clue alone (based on the sum of clues plus minimum gaps vs the line length). This produces `changed_h[i]` and `changed_w[i]` arrays.
- Loop over rows and columns in descending order of `changed`, so the rows that promise the most progress are solved first.
- For each line, call `do_row`, which calls `do_recurse` to enumerate placements of the clue blocks.

`do_recurse` (lines 356-417): "This algorithm basically tries all possible ways the given rows of black blocks can be laid out in the row/column being examined. Special care is taken to avoid checking the tail of a row/column if the same conditions have already been checked during this recursion. The algorithm also takes care to cut its losses as soon as an invalid (partial) solution is detected." This is the *complete* line solver (every placement enumerated, intersected), with memoisation by `minpos_done`/`maxpos_done`/`minpos_ok`/`maxpos_ok` arrays to avoid redundant work.

`solve_puzzle` keeps iterating sweeps over the changed rows/cols until no row/col was changed. If at the end any cell is still unknown, `ok = FALSE` and the generator throws away this puzzle.

### 9.5 What this proves

Tatham's source confirms that a complete, shipping, well-known nonogram implementation:

1. Uses pure line-solver-only deduction as both its solver and its difficulty filter.
2. Generates puzzles by a retry loop that throws away anything not line-solvable.
3. Has no uniqueness check separate from the line solver, because a successful line-solver run *is* a uniqueness proof (the deduction at every step is forced).
4. Has no branching/probing/2-SAT/SAT/ILP fallback. The puzzles it produces are all in Batenburg's "simple" class.
5. Targets density 50% by a median threshold, which is empirically a good operating point for inferability (Foote phase transition).
6. Preset sizes are 10×10 through 30×30. [source: /tmp/pattern.c lines 74-82]

For this project's design, Tatham's `pattern.c` is a strong reference implementation: short (2,255 lines, much of it boilerplate UI/serialization), deterministic, MIT-licensed.

---

## 10. Open questions and what remains unverified

- **Wikibooks "Nonograms/Solving" page** mentioned in the brief: URL `https://en.wikibooks.org/wiki/Nonograms/Solving` returns HTTP 404. The Wikipedia "Solution techniques" section is the apparent replacement; it contains the canonical named techniques (§3.1). It is possible the Wikibooks content was merged into Wikipedia at some point. **Unverified** beyond "the URL no longer exists".
- **BGU project home page** at https://www.cs.bgu.ac.il/~berend/nonograms/ returned 403 in this research. The paper (DAM 2014) and downloadable JAR are documented from secondary sources (Wolter survey, pynogram README, ResearchGate listing). **Partially verified.**
- **Steve Simpson's "Lancaster" pages**: Lancaster URLs in old references are dead. The current canonical URL appears to be https://stevocity.me.uk/nonogram/. The original Simpson nonolib / nonogram / nonowimp software is documented at https://stevocity.me.uk/nonogram/theory and at http://www.lancaster.ac.uk/~simpsons/software/pkg-nonowimp.html (which redirects). **Verified content, slightly migrated.**
- **Wolter survey freshness**: last updated September 25, 2013 per Wikipedia ref [9]. Does not include LalaFrogKK's full development arc, Requiem (2019), or post-2013 solvers/tournaments. The Wikipedia article and Wu's curated bibliography (http://ref.kcwu.csie.org/nonograms/) are the only later catalogues found in this research. **Verified but dated.**
- **Conceptis / Easybrain / Jupiter generator details**: not publicly documented beyond marketing copy. **Confirmed gap.**
- **n-Dom puzzles**: explicit "this is hard for solvers but possible for humans" example, used in Wolter's survey [source: https://webpbn.com/survey/dom.html]. The Joshua Greifer-designed dom puzzles are a known stress test for the line-solver-only approach.
- **Picross 3D**: a Nintendo / HAL Laboratory variant; mentioned in the GBAtemp forum thread on puzzle generation but not pursued in this research as it is out of scope. [source: https://gbatemp.net/threads/picross-3d-puzzle-generating-algorithm.623880/]
- **Simon Tatham's git repo**: https://git.tartarus.org/?p=simon/puzzles.git;a=blob_plain;f=pattern.c;hb=HEAD returned 403 to WebFetch (likely user-agent restriction). The GitHub mirror at https://github.com/samuellwn/puzzles is current enough that the raw URL worked, and the code in this analysis comes from that. **Verified.**

### 10.1 Reference URLs cited above (deduplicated)

Primary sources:

- Wikipedia: https://en.wikipedia.org/wiki/Nonogram
- Wolter solver survey: https://webpbn.com/survey/
- Wolter pbnsolve: https://webpbn.com/pbnsolve.html
- Wolter webpbn FAQ: https://webpbn.com/faq.html
- Wolter dom puzzle benchmark: https://webpbn.com/survey/dom.html
- Steve Simpson theory: https://stevocity.me.uk/nonogram/theory
- Steve Simpson Olšák line solver: https://stevocity.me.uk/nonogram/ls-olsak
- Conceptis Pic-a-Pix overview: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix
- Conceptis Pic-a-Pix history: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/history
- Conceptis Pic-a-Pix techniques: https://www.conceptispuzzles.com/index.aspx?uri=puzzle/pic-a-pix/techniques
- Conceptis founders interview: https://www.conceptispuzzles.com/index.aspx?uri=info/article/111
- nonograms.org methods: https://www.nonograms.org/methods
- Easybrain Nonogram.com: https://easybrain.com/nonogram
- Activity Workshop tutorial: https://activityworkshop.net/puzzlesgames/nonograms/tutorial.html
- Simon Tatham collection home: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/
- Pattern documentation: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/doc/pattern.html
- Pattern source (mirror): https://raw.githubusercontent.com/samuellwn/puzzles/master/pattern.c
- LalaFrogKK page: https://cgilab.nctu.edu.tw/~icwu/aigames/LalaFrogKK.html
- LalaFrogKK github: https://github.com/CGI-LAB/Nonogram
- Naughty (Kuang-che Wu): http://kcwu.csie.org/~kcwu/nonogram/naughty/
- Kuang-che Wu bibliography: http://ref.kcwu.csie.org/nonograms/
- Roucairol & Cazenave 2024 PDF: https://www.lamsade.dauphine.fr/~cazenave/papers/Nonogram2024.pdf (extracted to /tmp/nonogram2024.txt)
- Roucairol nonoGen code: https://github.com/RoucairolMilo/nonoGen
- Batenburg, Henstra, Kosters, Palenstijn 2009 PDF: https://liacs.leidenuniv.nl/~kosterswa/constru.pdf (extracted to /tmp/constru.txt)
- Batenburg & Kosters 2009 PDF: https://homepages.cwi.nl/~kbatenbu/papers/bako_pr_2009.pdf (extracted to /tmp/bako2009.txt)
- Foote 2024 thesis PDF: https://digitalcollections.wesleyan.edu/_flysystem/fedora/2024-07/1239_377473.pdf (extracted to /tmp/foote.txt)
- Foote & Krizanc arXiv 2024: https://arxiv.org/html/2507.07283v1
- Yato & Seta 2003 (IEICE): https://globals.ieice.org/en_transactions/fundamentals/10.1587/e86-a_5_1052/_p
- Yato & Seta 2003 (preprint): https://www-imai.is.s.u-tokyo.ac.jp/~yato/data2/SIGAL87-2.pdf
- Ueda & Nagao 1996 TR (no live URL; CiteSeerX:10.1.1.57.5277)
- Ueda-Nagao reduction implementation: https://github.com/mgfzemor/Nonogram
- Berend, Pomeranz, Rabani, Raziel 2014 (DAM): https://cris.bgu.ac.il/en/publications/nonograms-combinatorial-questions-and-algorithms/ (Discrete Applied Mathematics 169:30-42, doi:10.1016/j.dam.2014.01.004)
- Wu, Sun et al 2013 PDF: https://ir.lib.nycu.edu.tw/bitstream/11536/22772/1/000324586300005.pdf
- Victor Franco Sánchez writeup: https://web.mat.upc.edu/victor.franco.sanchez/nonograms/
- Salcedo-Sanz et al 2007: https://www.semanticscholar.org/paper/Solving-Japanese-Puzzles-with-Heuristics-Salcedo-Sanz-Ort%C3%ADz-Garc%C3%ADa/1e6c8cd4a8e72ec3abd1ce3cbf20c4366a007453
- pbnsolve mirror (cygy): https://github.com/cygy/pbnsolve
- pbnsolve mirror (avi-levy): https://github.com/avi-levy/pbnsolve
- FiveLakesStudio/PicrossSolver: https://github.com/FiveLakesStudio/PicrossSolver
- HandsomeOne/Nonogram: https://github.com/HandsomeOne/Nonogram
- Izaron/Nonograms: https://github.com/Izaron/Nonograms
- tsionyx/nonogrid: https://github.com/tsionyx/nonogrid
- tsionyx/pynogram: https://github.com/tsionyx/pynogram
- pierre-dejoue/picross-solver: https://github.com/pierre-dejoue/picross-solver
- GitHub topic nonogram: https://github.com/topics/nonogram
- GitHub topic nonogram-solver: https://github.com/topics/nonogram-solver
- Chess Programming Wiki, Nonogram: https://www.chessprogramming.org/Nonogram
- VGC Jupiter Picross interview: https://www.videogameschronicle.com/features/picross-developer-jupiter-on-nearly-30-years-of-puzzling-prowess/
- Hakank's CP blog post on the survey: https://www.hakank.org/constraint_programming_blog/2010/03/survey_of_nonogram_solvers_upd.html
- TAAI 2011 nonogram tournament: http://kcwu.csie.org/~kcwu/nonogram/taai11/

Wikipedia bibliography (transcribed from the article's reference list):

- Salcedo-Sanz, Sancho et al. "Solving Japanese Puzzles with Heuristics", 2007 IEEE Symposium on Computational Intelligence and Games, IEEE, April 2007. doi:10.1109/CIG.2007.368102
- Dalgety, James. "Origins of Cross Reference Grid & Picture Grid Puzzles." Puzzle Museum. http://puzzlemuseum.com/griddler/gridhist.htm
- Games Magazine Presents Paint by Numbers. Random House, 1994. ISBN 0-8129-2384-7
- Walker, John. "Wot I Think: Fantastic picross puzzler Pictopix." Rock, Paper, Shotgun, January 12, 2017. https://www.rockpapershotgun.com/2017/01/12/pictopix-review/
- Ueda, Nobuhisa; Nagao, Tadaaki. "NP-completeness results for NONOGRAM via Parsimonious Reductions." Technical Report TR96-0008, Department of Computer Science, Tokyo Institute of Technology, 1996. CiteSeerX:10.1.1.57.5277
- van Rijn, Jan N. Playing Games: The complexity of Klondike, Mahjong, Nonograms and Animal Chess. Master's thesis, Leiden Institute of Advanced Computer Science, Leiden University, 2012.
- Hoogeboom, Hendrik Jan; Kosters, Walter; van Rijn, Jan N.; Vis, Jonathan K. "Acyclic Constraint Logic and Games." ICGA Journal, vol. 37, no. 1, 2014, pp. 3-16. doi:10.3233/ICG-2014-37102
- Brunetti, Sara; Daurat, Alain. "An algorithm reconstructing convex lattice sets." Theoretical Computer Science, vol. 304, no. 1-3, 2003, pp. 35-57. doi:10.1016/S0304-3975(03)00050-1
- Wolter, Jan. "Survey of Paint-by-Number Puzzle Solvers." September 25, 2013. http://webpbn.com/survey/
- Batenburg, K.J; Kosters, W.A. "Solving Nonograms by combining relaxations." Pattern Recognition, vol. 42, no. 8, 2009, pp. 1672-1683. doi:10.1016/j.patcog.2008.12.003

[source: https://en.wikipedia.org/wiki/Nonogram, reference list as enumerated by WebFetch on 2026-05-16]

---

## End of document

Compiled 2026-05-16. Every claim in this document has been linked to a source URL, paper, or specific file path (with line numbers when the source is a downloaded PDF text extraction). Items marked "Unverified" or "Confirmed gap" are explicit acknowledgements that no source was found.

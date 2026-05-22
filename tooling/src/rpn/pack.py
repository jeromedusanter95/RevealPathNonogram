"""JSON serialization for generated puzzle packs.

Format spec in `design/02_generator.md` §5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rpn.generator import GeneratedPuzzle
from rpn.model import Cell, Direction, Segment


# Version 4 removes all legacy solver-perspective scores (clue_ambiguity,
# score, tier_*, line/path_tactic_steps, by_tactic). The pack now carries
# only player-experience metrics. perceived_score is the sole ranking key.
_VERSION = 4


def write_pack(
    path: Path, pack_id: str, puzzles: list[GeneratedPuzzle]
) -> None:
    payload: dict[str, Any] = {
        "version": _VERSION,
        "pack_id": pack_id,
        "puzzles": [_puzzle_to_dict(p, i) for i, p in enumerate(puzzles, start=1)],
    }
    path.write_text(json.dumps(payload, indent=2))


def _puzzle_to_dict(p: GeneratedPuzzle, index: int) -> dict[str, Any]:
    return {
        "id": f"{p.difficulty.grid_size[0]}x{p.difficulty.grid_size[1]}_{index:03d}",
        "width": p.puzzle.width,
        "height": p.puzzle.height,
        "start": [p.puzzle.start.col, p.puzzle.start.row],
        "goal": [p.puzzle.goal.col, p.puzzle.goal.row],
        "row_counts": list(p.puzzle.row_counts),
        "col_counts": list(p.puzzle.col_counts),
        "hints": [_segment_to_dict(s) for s in p.puzzle.hints],
        "solution_path": [[c.col, c.row] for c in p.solution_path],
        "difficulty": {
            "hint_count": p.difficulty.hint_count,
            "path_length": p.difficulty.path_length,
            "n_decisions": p.difficulty.n_decisions,
            "decision_ratio": round(p.difficulty.decision_ratio, 3),
            "total_decision_weight": p.difficulty.total_decision_weight,
            "perceived_score": round(p.difficulty.perceived_score, 2),
            # Per-decision detail used by the playtest viewer to highlight
            # decision tiles. Each entry: [step, n_candidates, trap_depth, weight].
            # step is 1-indexed; tip cell = solution_path[step - 1].
            "decisions": [list(d) for d in p.difficulty.decisions],
        },
        "seed": p.seed,
    }


def _segment_to_dict(s: Segment) -> dict[str, Any]:
    return {
        "cell": [s.cell.col, s.cell.row],
        "sides": sorted(d.value for d in s.sides),
    }

"""Command-line interface for puzzle generation.

Usage:
  python -m rpn.cli new --width 5 --height 5 --count 10 --out packs/easy_5x5.json
  python -m rpn.cli stats packs/easy_5x5.json
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import click

from rpn.generator import GeneratorConfig, generate
from rpn.pack import write_pack


@click.group()
def cli() -> None:
    """Reveal-path nonogram puzzle generator."""


@cli.command(name="new")
@click.option("--width", type=int, required=True, help="Grid width.")
@click.option("--height", type=int, required=True, help="Grid height.")
@click.option("--count", type=int, default=10, help="Number of puzzles to generate.")
@click.option(
    "--density", type=float, default=0.55, help="Target path density (0-1)."
)
@click.option(
    "--hints",
    type=str,
    default=None,
    help="Target hint count. Integer for absolute (e.g. '6'), float for "
    "fraction of path cells (e.g. '0.5'). Omit for the minimal hint set "
    "(dig-holes result, hardest).",
)
@click.option("--seed-start", type=int, default=0, help="First random seed.")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output JSON file.",
)
@click.option(
    "--pack-id",
    type=str,
    default=None,
    help="Pack ID (defaults to '{width}x{height}_pack').",
)
def cmd_new(
    width: int,
    height: int,
    count: int,
    density: float,
    hints: str | None,
    seed_start: int,
    out: Path,
    pack_id: str | None,
) -> None:
    """Generate a new pack of puzzles."""
    if pack_id is None:
        pack_id = f"{width}x{height}_pack"

    target_hints: int | float | None = None
    if hints is not None:
        try:
            if "." in hints:
                target_hints = float(hints)
            else:
                target_hints = int(hints)
        except ValueError:
            raise click.BadParameter(f"--hints must be int or float, got {hints!r}")

    config = GeneratorConfig(
        width=width,
        height=height,
        target_density=density,
        target_hints=target_hints,
    )

    out.parent.mkdir(parents=True, exist_ok=True)

    puzzles = []
    start_time = time.time()
    seed = seed_start
    attempts = 0
    max_attempts = count * 5

    while len(puzzles) < count and attempts < max_attempts:
        result = generate(config, seed=seed)
        attempts += 1
        seed += 1
        if result is not None:
            puzzles.append(result)
            click.echo(
                f"  [{len(puzzles)}/{count}] path={len(result.solution_path)} "
                f"hints={result.difficulty.hint_count} "
                f"decisions={result.difficulty.n_decisions} "
                f"pscore={result.difficulty.perceived_score:.1f}"
            )

    elapsed = time.time() - start_time
    click.echo(
        f"\nGenerated {len(puzzles)}/{count} puzzles in {elapsed:.1f}s "
        f"({attempts} attempts)."
    )

    write_pack(out, pack_id, puzzles)
    click.echo(f"Wrote {out}")


@cli.command(name="build-pack")
@click.option(
    "--sizes",
    type=str,
    default="5",
    help="Comma-separated grid sizes (square). e.g. '5' for 5x5, '5,7,10' "
    "for a mixed-size pack. Each size contributes candidates to every band, "
    "unless overridden by --band-sizes.",
)
@click.option(
    "--band-sizes",
    type=str,
    default="",
    help="Per-band size override, e.g. 'divinity=5+7' (sizes joined by '+', "
    "entries by ','). Useful when a band's constraints make large-grid "
    "generation prohibitively slow (e.g. divinity 10x10).",
)
@click.option(
    "--per-difficulty",
    type=int,
    default=5,
    help="Number of puzzles per difficulty band (final output).",
)
@click.option(
    "--pool-multiplier",
    type=int,
    default=8,
    help="Pool size per (band, size) = per_difficulty * pool_multiplier. "
    "Bigger = better score spread, slower.",
)
@click.option(
    "--density", type=float, default=0.55, help="Target path density (0-1)."
)
@click.option(
    "--difficulties",
    type=str,
    default="easy:6,medium:4,difficult:3,expert:2,divinity:1:2+3+4:safe-endpoints+diagonal-endpoints",
    help="Comma-separated 'name:hints[:clues[:flags]]' entries. "
    "hints = int (absolute) or float ('.' = fraction). "
    "clues = '+'-separated allowed clue values. "
    "flags = '+'-separated named flags: 'safe-endpoints', 'diagonal-endpoints'.",
)
@click.option("--seed-start", type=int, default=1000, help="First random seed.")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output JSON file.",
)
def cmd_build_pack(
    sizes: str,
    band_sizes: str,
    per_difficulty: int,
    pool_multiplier: int,
    density: float,
    difficulties: str,
    seed_start: int,
    out: Path,
) -> None:
    """Generate a pack with bands assigned by perceived_score, across sizes.

    Strategy: for each (band, size) combination, generate a pool of candidates.
    Merge all candidates, sort by `perceived_score` (size + path length +
    weighted decisions). Within each band, pick `per_difficulty` candidates
    evenly spaced from the pool of that band's matching candidates.

    Grid sizes mix freely within a band: a 5x5 with many deep decision traps
    can outrank a 10x10 with few decisions.
    """
    size_list = _parse_sizes(sizes)
    bands = _parse_difficulties(difficulties)
    band_size_overrides = _parse_band_sizes(band_sizes, {b.name for b in bands})
    pool_per_combo = per_difficulty * pool_multiplier
    out.parent.mkdir(parents=True, exist_ok=True)

    seed = seed_start
    total_start = time.time()
    merged_pool: list[tuple[int, object]] = []  # (band_index, GeneratedPuzzle)

    for band_index, band in enumerate(bands):
        filter_msg = ""
        if band.allowed_clues is not None:
            filter_msg += f", clues in {sorted(band.allowed_clues)}"
        if band.forbid_endpoint_auto_lines:
            filter_msg += ", safe-endpoints"
        if band.require_diagonal_endpoints:
            filter_msg += ", diagonal-endpoints"
        band_sizes_for_loop = band_size_overrides.get(band.name, size_list)
        for w, h in band_sizes_for_loop:
            click.echo(
                f"\n== generating pool for band '{band.name}' (size {w}x{h}, "
                f"hints={band.hints}{filter_msg}), pool size = {pool_per_combo} =="
            )
            config = GeneratorConfig(
                width=w,
                height=h,
                target_density=density,
                target_hints=band.hints,
                allowed_clue_values=band.allowed_clues,
                forbid_endpoint_auto_lines=band.forbid_endpoint_auto_lines,
                require_diagonal_endpoints=band.require_diagonal_endpoints,
            )
            pool_count = 0
            attempts = 0
            max_attempts = pool_per_combo * 200
            while pool_count < pool_per_combo and attempts < max_attempts:
                result = generate(config, seed=seed)
                attempts += 1
                seed += 1
                if result is not None:
                    merged_pool.append((band_index, result))
                    pool_count += 1
            click.echo(
                f"  produced {pool_count}/{pool_per_combo} candidates "
                f"after {attempts} attempts"
            )

    # Hybrid band assignment:
    # 1. Sort the entire merged pool by perceived_score (easiest -> hardest).
    # 2. The last band (typically the hardest, e.g. 'divinity') keeps its
    #    structural constraints (clue restrictions, safe endpoints, etc.);
    #    only candidates from that band's pool are eligible for the last band.
    # 3. For the remaining bands, draw from a global view: every non-last-band
    #    slot can be filled by any non-last-band-generated puzzle, so the
    #    progression follows perceived_score, not hint count.
    merged_pool.sort(key=lambda entry: entry[1].difficulty.perceived_score)

    last_band_index = len(bands) - 1
    # Eligible-for-divinity candidates: only those generated under the last
    # band's constraints qualify.
    divinity_eligible = [i for i, (bi, _p) in enumerate(merged_pool) if bi == last_band_index]
    # Everything else is the hybrid pool (still sorted by perceived_score).
    hybrid_pool = [i for i, (bi, _p) in enumerate(merged_pool) if bi != last_band_index]

    used_indices: set[int] = set()
    picked_with_band: list[tuple[int, object]] = []

    # Bands 0..last-1: pick from hybrid_pool evenly spaced. Each band gets a
    # contiguous slice of the sorted hybrid_pool.
    non_divinity_bands = len(bands) - 1
    if non_divinity_bands > 0:
        if not hybrid_pool:
            click.echo("WARNING: no hybrid candidates available for non-divinity bands")
        else:
            total_picks = non_divinity_bands * per_difficulty
            if total_picks >= len(hybrid_pool):
                # Not enough candidates for one each: take them all sequentially.
                chosen_global = hybrid_pool[:]
            else:
                chosen_global = []
                step_indices = sorted(
                    set(
                        round(j * (len(hybrid_pool) - 1) / (total_picks - 1))
                        for j in range(total_picks)
                    )
                )
                chosen_global = [hybrid_pool[k] for k in step_indices]
                # If duplicates collapsed, fill out by walking hybrid_pool linearly.
                if len(chosen_global) < total_picks:
                    extras = [
                        i for i in hybrid_pool if i not in chosen_global
                    ]
                    chosen_global += extras[: total_picks - len(chosen_global)]
            for slot, idx in enumerate(chosen_global):
                used_indices.add(idx)
                picked_with_band.append(merged_pool[idx])

    # Last band: divinity. Pick the hardest per_difficulty from divinity_eligible.
    if not divinity_eligible:
        click.echo(f"WARNING: band {bands[last_band_index].name} has no candidates")
    else:
        unique_div = [i for i in divinity_eligible if i not in used_indices]
        if len(unique_div) >= per_difficulty:
            chosen = []
            for j in range(per_difficulty):
                idx_in_candidates = round(
                    j * (len(unique_div) - 1) / (per_difficulty - 1)
                )
                chosen.append(unique_div[idx_in_candidates])
        else:
            chosen = unique_div
            click.echo(
                f"WARNING: band {bands[last_band_index].name} only has "
                f"{len(chosen)} eligible candidates (wanted {per_difficulty})"
            )
        for i in chosen:
            used_indices.add(i)
            picked_with_band.append(merged_pool[i])

    picked = [p for _, p in picked_with_band]

    band_meta: list[tuple[str, int, int | float]] = []
    for band_index, band in enumerate(bands):
        start = band_index * per_difficulty
        band_meta.append((band.name, start, band.hints))

    click.echo(
        f"\nMerged pool size: {len(merged_pool)}. Selecting {len(picked)} puzzles.\n"
    )
    click.echo(
        f"{'lvl':<4} {'band':<10} {'size':<6} {'pscore':<8} {'dec':<4} "
        f"{'dw':<5} {'hints':<5} {'path':<4}"
    )
    for i, p in enumerate(picked, start=1):
        band_idx = (i - 1) // per_difficulty
        band_name = bands[band_idx].name if band_idx < len(bands) else "?"
        w, h = p.difficulty.grid_size
        click.echo(
            f"{i:<4} {band_name:<10} {w}x{h:<3} "
            f"{p.difficulty.perceived_score:<8.1f} "
            f"{p.difficulty.n_decisions:<4} "
            f"{p.difficulty.total_decision_weight:<5} "
            f"{p.difficulty.hint_count:<5} {p.difficulty.path_length:<4}"
        )

    elapsed = time.time() - total_start
    click.echo(f"\nGenerated {len(picked)} puzzles in {elapsed:.1f}s.")

    pack_id = _build_pack_id(size_list, "multi")
    _write_multi_pack(out, pack_id, picked, band_meta)
    click.echo(f"Wrote {out}")


def _parse_sizes(spec: str) -> list[tuple[int, int]]:
    """Parse '--sizes' into a list of (w, h). For now only square sizes are
    accepted; '5,7,10' becomes [(5,5), (7,7), (10,10)]."""
    sizes: list[tuple[int, int]] = []
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            n = int(raw)
        except ValueError:
            raise click.BadParameter(f"bad size {raw!r}, expected integer")
        if n < 2:
            raise click.BadParameter(f"size must be >= 2, got {n}")
        sizes.append((n, n))
    if not sizes:
        raise click.BadParameter("--sizes must list at least one size")
    return sizes


def _parse_band_sizes(
    spec: str, known_bands: set[str]
) -> dict[str, list[tuple[int, int]]]:
    """Parse 'band=sizes,band=sizes' into a per-band size override map.

    Example: 'divinity=5,7' returns {'divinity': [(5,5), (7,7)]}.
    Empty string returns {}. Bands not mentioned use the global --sizes list.
    """
    result: dict[str, list[tuple[int, int]]] = {}
    if not spec.strip():
        return result
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise click.BadParameter(
                f"--band-sizes entry must be 'name=sizes', got {entry!r}"
            )
        name, raw_sizes = entry.split("=", 1)
        name = name.strip()
        if name not in known_bands:
            raise click.BadParameter(
                f"--band-sizes references unknown band {name!r}; "
                f"known bands: {sorted(known_bands)}"
            )
        sizes_for_band: list[tuple[int, int]] = []
        for raw in raw_sizes.split("+"):
            raw = raw.strip()
            if not raw:
                continue
            try:
                n = int(raw)
            except ValueError:
                raise click.BadParameter(
                    f"--band-sizes size must be int, got {raw!r} in entry {entry!r}"
                )
            if n < 2:
                raise click.BadParameter(f"size must be >= 2, got {n}")
            sizes_for_band.append((n, n))
        if not sizes_for_band:
            raise click.BadParameter(f"--band-sizes entry {entry!r} has no sizes")
        result[name] = sizes_for_band
    return result


def _build_pack_id(sizes: list[tuple[int, int]], suffix: str) -> str:
    if len(sizes) == 1:
        w, h = sizes[0]
        return f"{w}x{h}_{suffix}"
    size_part = "_".join(f"{w}x{h}" for w, h in sizes)
    return f"{size_part}_{suffix}"


@dataclass(frozen=True, slots=True)
class _BandSpec:
    name: str
    hints: int | float
    allowed_clues: frozenset[int] | None
    forbid_endpoint_auto_lines: bool
    require_diagonal_endpoints: bool


def _parse_difficulties(spec: str) -> list[_BandSpec]:
    """Parse 'name:hints[:clues[:flags]]' entries.

    - `hints`: int (absolute) or float with a '.' (fraction of path cells).
    - `clues`: optional '+'-separated list of allowed row/column clue values
      (e.g. '2+3+4'). Omit by leaving the field empty (e.g. 'expert:2::safe-endpoints').
    - `flags`: optional '+'-separated list of named flags. Supported:
        safe-endpoints: forbid endpoint-auto-lines (see generator.py).
    """
    result: list[_BandSpec] = []
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) not in (2, 3, 4):
            raise click.BadParameter(
                f"difficulty entry must be 'name:hints[:clues[:flags]]', got {entry!r}"
            )
        name = parts[0].strip()
        raw_hints = parts[1].strip()
        if not name or not raw_hints:
            raise click.BadParameter(f"malformed difficulty entry: {entry!r}")
        hints: int | float
        try:
            hints = float(raw_hints) if "." in raw_hints else int(raw_hints)
        except ValueError:
            raise click.BadParameter(f"bad hints value in entry: {entry!r}")
        allowed: frozenset[int] | None = None
        if len(parts) >= 3 and parts[2].strip():
            try:
                allowed = frozenset(int(v) for v in parts[2].strip().split("+") if v)
            except ValueError:
                raise click.BadParameter(f"bad clues spec in entry: {entry!r}")
        flags: set[str] = set()
        if len(parts) == 4 and parts[3].strip():
            flags = {f.strip() for f in parts[3].strip().split("+") if f.strip()}
        unknown = flags - {"safe-endpoints", "diagonal-endpoints"}
        if unknown:
            raise click.BadParameter(
                f"unknown flag(s) {sorted(unknown)} in entry {entry!r}"
            )
        result.append(
            _BandSpec(
                name=name,
                hints=hints,
                allowed_clues=allowed,
                forbid_endpoint_auto_lines="safe-endpoints" in flags,
                require_diagonal_endpoints="diagonal-endpoints" in flags,
            )
        )
    return result


def _write_multi_pack(
    out: Path,
    pack_id: str,
    puzzles: list,
    band_meta: list[tuple[str, int, int | float]],
) -> None:
    from rpn.pack import _puzzle_to_dict

    # Compute which band each puzzle belongs to.
    band_for_index: dict[int, str] = {}
    for i, (name, start, _) in enumerate(band_meta):
        end = band_meta[i + 1][1] if i + 1 < len(band_meta) else len(puzzles)
        for j in range(start, end):
            band_for_index[j] = name

    payload = {
        "version": 2,
        "pack_id": pack_id,
        "difficulties": [
            {"name": name, "start_index": start, "hints_target": str(t)}
            for name, start, t in band_meta
        ],
        "puzzles": [],
    }
    for idx, p in enumerate(puzzles):
        d = _puzzle_to_dict(p, idx + 1)
        d["difficulty_name"] = band_for_index.get(idx, "unknown")
        payload["puzzles"].append(d)

    out.write_text(json.dumps(payload, indent=2))


@cli.command(name="curve")
@click.option("--width", type=int, required=True, help="Grid width.")
@click.option("--height", type=int, required=True, help="Grid height.")
@click.option(
    "--count",
    type=int,
    default=20,
    help="Number of levels in the final pack (evenly spaced by difficulty).",
)
@click.option(
    "--pool",
    type=int,
    default=200,
    help="Pool size to sample from. Larger = better spread, slower.",
)
@click.option("--density", type=float, default=0.55)
@click.option("--seed-start", type=int, default=1000)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
)
def cmd_curve(
    width: int,
    height: int,
    count: int,
    pool: int,
    density: float,
    seed_start: int,
    out: Path,
) -> None:
    """Generate a large pool, then pick `count` puzzles spaced from easiest to hardest.

    The output pack's Level 1 is the easiest puzzle in the pool, Level `count`
    the hardest, with the rest evenly spaced between them by perceived_score.
    No fixed hint targets: dig-holes alone decides each puzzle's hint count.
    """
    out.parent.mkdir(parents=True, exist_ok=True)

    config = GeneratorConfig(
        width=width, height=height, target_density=density, target_hints=None
    )
    candidates = []
    seed = seed_start
    attempts = 0
    max_attempts = pool * 3
    start_time = time.time()

    click.echo(f"Generating pool of {pool} candidates...")
    while len(candidates) < pool and attempts < max_attempts:
        result = generate(config, seed=seed)
        attempts += 1
        seed += 1
        if result is not None:
            candidates.append(result)
            if len(candidates) % 25 == 0:
                click.echo(f"  {len(candidates)}/{pool}...")

    elapsed = time.time() - start_time
    click.echo(f"Pool ready: {len(candidates)} puzzles in {elapsed:.1f}s.\n")

    if len(candidates) < count:
        click.echo(
            f"WARNING: pool of {len(candidates)} < requested count {count}; using all."
        )

    # Sort by perceived_score (ascending = easiest first).
    candidates.sort(key=lambda p: p.difficulty.perceived_score)

    # Pick `count` puzzles evenly spaced from index 0 to index len-1.
    if count >= len(candidates):
        picked = candidates
    else:
        picked = []
        for i in range(count):
            idx = round(i * (len(candidates) - 1) / (count - 1))
            picked.append(candidates[idx])

    click.echo(f"Selected {len(picked)} puzzles, sorted from easiest to hardest:")
    click.echo(
        f"{'level':<6} {'pscore':<8} {'dec':<4} {'dw':<5} {'hints':<6} {'path':<5}"
    )
    for i, p in enumerate(picked, start=1):
        click.echo(
            f"{i:<6} {p.difficulty.perceived_score:<8.2f} "
            f"{p.difficulty.n_decisions:<4} "
            f"{p.difficulty.total_decision_weight:<5} "
            f"{p.difficulty.hint_count:<6} {p.difficulty.path_length:<5}"
        )

    pack_id = f"{width}x{height}_curve"
    write_pack(out, pack_id, picked)
    click.echo(f"\nWrote {out}")


@cli.command(name="stats")
@click.argument("pack_file", type=click.Path(exists=True, path_type=Path))
def cmd_stats(pack_file: Path) -> None:
    """Print summary statistics about a pack."""
    data = json.loads(pack_file.read_text())
    puzzles = data["puzzles"]
    click.echo(f"Pack: {data['pack_id']}  ({len(puzzles)} puzzles)")
    click.echo()

    if not puzzles:
        return

    by_hints: dict[int, int] = {}
    by_path_len: dict[int, int] = {}
    for p in puzzles:
        hints = p["difficulty"]["hint_count"]
        path_len = p["difficulty"]["path_length"]
        by_hints[hints] = by_hints.get(hints, 0) + 1
        by_path_len[path_len] = by_path_len.get(path_len, 0) + 1

    click.echo("Hint count distribution:")
    for k in sorted(by_hints):
        click.echo(f"  {k:>3} hints: {by_hints[k]}")
    click.echo()
    click.echo("Path length distribution:")
    for k in sorted(by_path_len):
        click.echo(f"  {k:>3} cells: {by_path_len[k]}")


if __name__ == "__main__":
    cli()

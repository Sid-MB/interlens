# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# [rational_agents: viz] 2026-07-29

"""The file-writing layer: run directory in, HTML pages plus an index on disk out.

Kept apart from :mod:`~interlens.arena.viz.page` (which is pure ``payload -> string``) so every renderer stays
testable without touching a filesystem, and so a caller that wants the HTML in memory — to embed it, serve it, or
diff it — never has to write a file to get it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .compare import DEFAULT_PAIR_KEY, pair_runs
from .episode import RunDir
from .page import render_compare_html, render_episode_html, render_index_html


def render_episode(run: str | Path, episode_path: str | Path, *, reconstruct: bool = True,
                   annotations_dirname: str = "annotations") -> str:
    """The interactive HTML for one episode of a run, as a string. ``annotations_dirname`` selects the per-run
    annotation subdirectory (see :class:`~interlens.arena.viz.episode.RunDir`)."""
    return render_episode_html(RunDir(run, annotations_dirname=annotations_dirname)
                               .payload(episode_path, reconstruct=reconstruct))


def render_compare(left_run: str | Path, right_run: str | Path, *, index: int = 0,
                   pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY, reconstruct: bool = True,
                   annotations_dirname: str = "annotations") -> str:
    """The interactive HTML for the ``index``-th matched pair between two runs, as a string.
    ``annotations_dirname`` selects the per-run annotation subdirectory both sides are read with."""
    comparisons, report = pair_runs(left_run, right_run, pair_fields=pair_fields, limit=index + 1,
                                    reconstruct=reconstruct, annotations_dirname=annotations_dirname)
    if not comparisons:
        raise ValueError(f"no episode pairs matched on {list(pair_fields)}: {report}")
    return render_compare_html(comparisons[index])


def export_episode(run: str | Path, episode_path: str | Path, out_dir: str | Path, *,
                   reconstruct: bool = True, annotations_dirname: str = "annotations") -> Path:
    """Write one episode's page into ``out_dir`` as ``<episode_id>.html`` and return its path.
    ``annotations_dirname`` selects the per-run annotation subdirectory (see
    :class:`~interlens.arena.viz.episode.RunDir`)."""
    payload = RunDir(run, annotations_dirname=annotations_dirname).payload(episode_path, reconstruct=reconstruct)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{payload['episode']['episode_id']}.html"
    path.write_text(render_episode_html(payload))
    return path


def export_run(run: str | Path, out_dir: str | Path, *, limit: int | None = None,
               reconstruct: bool = True, annotations_dirname: str = "annotations") -> dict:
    """Render every episode of a run to its own page in ``out_dir``, plus an ``index.html`` listing them with the
    numbers that say which are worth opening. Returns a manifest (also written as ``manifest.json``).

    ``limit`` renders only the first ``limit`` episodes in sorted path order — the fast path for a spot check on a
    campaign cell with hundreds of episodes. ``annotations_dirname`` selects which per-run annotation subdirectory
    the post-hoc oracles are read from (default ``"annotations"``; e.g. ``"annotations_v1"`` for a re-annotated
    set — see :class:`~interlens.arena.viz.episode.RunDir`)."""
    run_dir = RunDir(run, annotations_dirname=annotations_dirname)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = run_dir.episode_files()[:limit] if limit is not None else run_dir.episode_files()
    rows, failures = [], []
    for f in files:
        try:
            payload = run_dir.payload(f, reconstruct=reconstruct)
        except Exception as exc:                       # one unreadable episode must not lose the whole export
            failures.append({"episode": str(f), "error": f"{type(exc).__name__}: {exc}"})
            continue
        ep, out = payload["episode"], payload.get("outcome") or {}
        name = f"{ep['episode_id']}.html"
        (out_dir / name).write_text(render_episode_html(payload))
        rows.append({"href": name, "label": ep["episode_id"], "model": ep.get("model"), "arm": ep.get("arm"),
                     "seed": ep.get("seed"), "deal": bool(out.get("deal")), "primary": out.get("primary"),
                     "usw": out.get("usw"), "esw": out.get("esw"),
                     "regret": (payload.get("annotation_summary") or {}).get("total_regret")})
    note = (f"{len(rows)} episode(s) from <code>{run_dir.root}</code>. "
            + (f"{len(failures)} episode(s) failed to render." if failures else ""))
    (out_dir / "index.html").write_text(render_index_html(rows, f"Episodes — {run_dir.root.name}", note))
    manifest = {"run": str(run_dir.root), "out_dir": str(out_dir), "n_episodes": len(rows),
                "index": str(out_dir / "index.html"), "failures": failures,
                "pages": [str(out_dir / r["href"]) for r in rows]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def export_comparison(left_run: str | Path, right_run: str | Path, out_dir: str | Path, *,
                      limit: int | None = None, pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
                      reconstruct: bool = True, select: str = "first",
                      annotations_dirname: str = "annotations") -> dict:
    """Pair two runs on ``pair_fields`` and write one comparison page per matched pair, plus an index and the
    pairing report. Returns a manifest (also written as ``manifest.json``).

    ``select`` (see :data:`~interlens.arena.viz.compare.SELECTIONS`) decides which pairs a ``limit`` keeps —
    ``"largest-effect"`` or ``"deal-flip"`` rather than the arbitrary first few. ``annotations_dirname`` selects
    which per-run annotation subdirectory BOTH sides read their post-hoc oracles from (default ``"annotations"``;
    e.g. ``"annotations_v1"`` — see :class:`~interlens.arena.viz.episode.RunDir`).

    The pairing report is part of the deliverable, not a log line: it names how many episodes matched, which keys
    went unmatched, and how the rendered pairs were selected, so a partially-complete campaign is visible as
    partial rather than quietly rendering whichever cells happened to finish."""
    comparisons, report = pair_runs(left_run, right_run, pair_fields=pair_fields, limit=limit,
                                    reconstruct=reconstruct, select=select,
                                    annotations_dirname=annotations_dirname)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for cmp_payload in comparisons:
        le, re_ = cmp_payload["left"]["episode"], cmp_payload["right"]["episode"]
        name = f"compare-{le['episode_id']}--{re_['episode_id']}.html"
        (out_dir / name).write_text(render_compare_html(cmp_payload))
        focal = cmp_payload.get("focal_seats") or []
        scores = {r["metric"]: r for r in cmp_payload["scores"]}
        rows.append({"href": name,
                     "label": f"{le['instance_id']} seed {le['seed']} · {le['arm']}"
                              + (f" · swapped {', '.join(f['name'] for f in focal)}" if focal else
                                 " · no seat swap"),
                     "model": f"{le.get('model')} vs {re_.get('model')}", "arm": le.get("arm"),
                     "seed": le.get("seed"),
                     "deal": bool((cmp_payload["right"].get("outcome") or {}).get("deal")),
                     "primary": scores.get("primary score", {}).get("delta"),
                     "usw": scores.get("joint welfare USW", {}).get("delta"),
                     "esw": scores.get("egalitarian ESW", {}).get("delta"),
                     "regret": None})
    note = (f"{len(rows)} of {report['n_candidate_pairs']} matched pair(s), paired on "
            f"<code>{', '.join(pair_fields)}</code> and selected by <code>{select}</code>. "
            f"{report['n_left']} episode(s) left, {report['n_right']} right, "
            f"{report['n_matched_keys']} shared key(s). The primary/USW/worst-off columns are DELTAS "
            "(right minus left), not levels.")
    (out_dir / "index.html").write_text(render_index_html(rows, "Seat-swap comparisons", note))
    manifest = {"report": report, "out_dir": str(out_dir), "n_comparisons": len(rows),
                "index": str(out_dir / "index.html"), "pages": [str(out_dir / r["href"]) for r in rows]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest

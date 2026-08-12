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

from .chrome import distance_to_nbs, inject_nav, nav_group
from .compare import DEFAULT_PAIR_KEY, pair_runs
from .episode import RunDir
from .page import preference_visibility, render_compare_html, render_episode_html, render_index_html


def _parameter_fields(payload: dict) -> dict:
    """Return the parameter-set fields shown on run and comparison indexes.

    Current instances store ``solution.difficulty`` and therefore expose it as ``game.difficulty`` in a render
    payload. The episode, cell configuration, and manifest fallbacks accept campaign outputs that mirror the same
    metadata. ``score_differential`` is optional because an unpaired condition has no effect estimate unless its
    campaign wrote one explicitly.
    """
    ep, manifest, game = payload.get("episode") or {}, payload.get("manifest") or {}, payload.get("game") or {}
    cell = ep.get("cell_cfg") or {}
    difficulty = (game.get("difficulty") or ep.get("difficulty") or cell.get("difficulty")
                  or manifest.get("difficulty") or {})
    if isinstance(difficulty, (int, float)):
        difficulty = {"score": difficulty}
    if not isinstance(difficulty, dict):
        difficulty = {}
    tags = difficulty.get("tags") or ep.get("tags") or cell.get("tags") or manifest.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    components = difficulty.get("components") or {}
    component_text = (", ".join(f"{key}={value:.3g}" if isinstance(value, float) else f"{key}={value}"
                                for key, value in sorted(components.items()))
                      if isinstance(components, dict) else "")
    return {
        # ``scalar`` is the campaign schema; ``score`` is accepted for already-generated prototype banks.
        "difficulty": (difficulty.get("scalar") if difficulty.get("scalar") is not None
                       else difficulty.get("score")),
        "difficulty_tags": ", ".join(str(tag) for tag in tags),
        "difficulty_components": component_text,
        "score_diff": (ep.get("score_differential") if ep.get("score_differential") is not None
                       else manifest.get("score_differential")),
    }


def _hazard_fields(payload: dict) -> dict:
    """The index's hazard column for one episode: every reason its numbers may not pair with another row's.

    Three sources, each of which has independently invalidated a comparison in this program and none of which
    the existing ``fabricated`` column can see: the run's vintage hazard file, a generation budget that is not
    the frozen protocol's, and an episode that spent turns saying nothing. Rendered as ``·``-separated flags so
    the index can turn each into its own badge, count them for sorting, and filter on "has any".
    """
    census, budget = payload.get("census") or {}, payload.get("budget") or {}
    ballots = payload.get("ballots") or {}
    flags, notes, detail = [], [], []
    if payload.get("vintage"):
        flags.append("SPOILED VINTAGE")
        detail.append(str((payload["vintage"] or {}).get("headline") or ""))
    if budget and not budget.get("default"):
        # INFORMATIONAL, not a hazard. A non-default budget is usually the arm's intended budget — the frozen
        # Opus cells run at a 16,384 API floor on purpose — and it is only ever a constraint on what the row
        # pairs WITH. Painting it the same red as a spoiled vintage would make every confirmatory episode look
        # broken and teach a reader to ignore the column.
        notes.append(f"budget {budget.get('effective')}")
        detail.append(f"generation budget {budget.get('effective')} tokens vs the frozen "
                      f"{'/'.join(str(c) for c in budget.get('frozen') or [])} — intended or not, it does not "
                      "pair with a default-cap run")
    if census.get("placeholder"):
        flags.append(f"{_pct(census.get('placeholder_rate'))} silent")
        detail.append(f"{census['placeholder']} of {census.get('n_turns')} turns published nothing")
    if ballots.get("n_abstentions"):
        flags.append(f"{ballots['n_abstentions']} no-ballot")
        detail.append(f"{ballots['n_abstentions']} seat(s) cast no ballot on the final vote")
    if ballots.get("n_mismatch"):
        flags.append(f"{ballots['n_mismatch']} vote mismatch")
        detail.append(f"{ballots['n_mismatch']} recorded ballot(s) disagree with the seat's own policy")
    return {"hazards": " · ".join(flags), "hazard_notes": " · ".join(notes),
            "hazard_detail": "; ".join(d for d in detail if d),
            "silent_pct": _pct_value(census.get("placeholder_rate")),
            "non_action_pct": _pct_value(census.get("non_action_rate"))}


def _merge_hazards(left: dict, right: dict) -> dict:
    """Union two episodes' hazard flags, keeping each flag once and the worse of each rate."""
    def union(key: str) -> str:
        both = [f for f in (left[key].split(" · ") + right[key].split(" · ")) if f]
        return " · ".join(dict.fromkeys(both))

    return {"hazards": union("hazards"), "hazard_notes": union("hazard_notes"),
            "hazard_detail": "; ".join(d for d in (left["hazard_detail"], right["hazard_detail"]) if d),
            "silent_pct": max(left["silent_pct"], right["silent_pct"]),
            "non_action_pct": max(left["non_action_pct"], right["non_action_pct"])}


def _pct_value(fraction) -> float:
    """A recorded rate as a percentage, rounded for a table cell; ``0.0`` for an absent rate."""
    return round(100 * (fraction or 0), 2)


def _pct(fraction) -> str:
    """A recorded rate as a short percentage label for a badge."""
    return f"{_pct_value(fraction):g}%"


def _link_pages(paths: list[Path], rows: list[dict]) -> None:
    """Give every written page its prev/next links and the picker of its siblings.

    Done as a second pass over the files rather than at render time because neither half knows enough on its own:
    a page is rendered from ONE payload and cannot know what else the run holds, while the exporter only knows the
    full set after the last page is written. So each page reserves a marker (see :data:`~.chrome.NAV_MARKER`) and
    this replaces it — a string substitution on an already-written file, no re-render and no second parse of the
    episode records."""
    for i, path in enumerate(paths):
        path.write_text(inject_nav(path.read_text(), nav_group(rows, i)))


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
    rows, paths, failures = [], [], []
    for f in files:
        try:
            payload = run_dir.payload(f, reconstruct=reconstruct)
        except Exception as exc:                       # one unreadable episode must not lose the whole export
            failures.append({"episode": str(f), "error": f"{type(exc).__name__}: {exc}"})
            continue
        ep, out = payload["episode"], payload.get("outcome") or {}
        gen = payload.get("generation") or {}
        name = f"{ep['episode_id']}.html"
        (out_dir / name).write_text(render_episode_html(payload))
        paths.append(out_dir / name)
        rows.append({"href": name, "label": ep["episode_id"], "model": ep.get("model"), "arm": ep.get("arm"),
                     "visibility": preference_visibility(payload),
                     "instance": ep.get("instance_id"), "seed": ep.get("seed"), "deal": bool(out.get("deal")),
                     "primary": out.get("primary"), "dist_nbs": distance_to_nbs(payload),
                     "usw": out.get("usw"), "esw": out.get("esw"),
                     "fabricated_pct": round(100 * (gen.get("fraction") or 0), 2),
                     "regret": (payload.get("annotation_summary") or {}).get("total_regret"),
                     **_hazard_fields(payload), **_parameter_fields(payload)})
    _link_pages(paths, rows)
    note = (f"{len(rows)} episode(s) from <code>{run_dir.root}</code>. "
            + (f"{len(failures)} episode(s) failed to render." if failures else ""))
    readme_path = run_dir.root / "README.md"
    readme = readme_path.read_text() if readme_path.is_file() else ""
    (out_dir / "index.html").write_text(
        render_index_html(rows, f"Episodes — {run_dir.root.name}", note, readme)
    )
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
    rows, paths = [], []
    for cmp_payload in comparisons:
        le, re_ = cmp_payload["left"]["episode"], cmp_payload["right"]["episode"]
        name = f"compare-{le['episode_id']}--{re_['episode_id']}.html"
        (out_dir / name).write_text(render_compare_html(cmp_payload))
        paths.append(out_dir / name)
        focal = cmp_payload.get("focal_seats") or []
        scores = {r["metric"]: r for r in cmp_payload["scores"]}
        fab = max((cmp_payload[side].get("generation") or {}).get("fraction") or 0 for side in ("left", "right"))
        parameter_fields = _parameter_fields(cmp_payload["left"])
        # ``score_table`` defines the comparison's normalized headline effect under this exact metric key.
        # Keep a defensive ``score`` alias for externally constructed comparison payloads.
        primary_score = scores.get("primary score") or scores.get("score") or {}
        parameter_fields["score_diff"] = primary_score.get("delta")
        rows.append({"href": name,
                     "label": f"{le['instance_id']} seed {le['seed']} · {le['arm']}"
                              + (f" · swapped {', '.join(f['name'] for f in focal)}" if focal else
                                 " · no seat swap"),
                     "model": f"{le.get('model')} vs {re_.get('model')}", "arm": le.get("arm"),
                     "visibility": preference_visibility(cmp_payload["left"]),
                     "instance": le.get("instance_id"), "seed": le.get("seed"),
                     "deal": bool((cmp_payload["right"].get("outcome") or {}).get("deal")),
                     "primary": scores.get("primary score", {}).get("delta"),
                     "dist_nbs": None,
                     "usw": scores.get("joint welfare USW", {}).get("delta"),
                     "esw": scores.get("egalitarian ESW", {}).get("delta"),
                     "fabricated_pct": round(100 * fab, 2),
                     "regret": None,
                     # A comparison inherits BOTH sides' hazards: a pair is only as poolable as its worse half,
                     # so the flags are unioned rather than taken from the left episode alone.
                     **_merge_hazards(_hazard_fields(cmp_payload["left"]),
                                      _hazard_fields(cmp_payload["right"])),
                     **parameter_fields})
    _link_pages(paths, rows)
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

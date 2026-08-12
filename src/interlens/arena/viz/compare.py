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

"""Seat-swap comparison: the same game instance played twice, with one seat's occupant swapped.

The scientific question this renders is a *substitution* effect — hold the instance, the seed, the arm, and every
other seat fixed; replace the occupant of one seat (a computable rational policy vs an LLM); read off what changed.
Two episodes that share an instance and seed start from the identical opening state and then diverge at the first
move the two occupants play differently, after which every later turn is a different state and the transcripts are
no longer aligned in any deeper sense than their turn slots. The renderer therefore does exactly two things:

1. **Align turn slots** on ``(round, phase, seat)`` — the fixed-rotation protocol makes those slots comparable —
   and mark the FIRST slot whose public behaviour differs as the divergence point. Everything after it is shown as
   two independent trajectories, never as a per-turn "diff", because after divergence the two seats are answering
   different questions.
2. **Quantify the outcome difference** with paired deltas on the metrics that carry the claim: the focal seat's
   surplus and its share of what was available to it, deal rate, joint welfare, the primary score, and each
   party's realized surplus.

Pairing is a *key*, not a heuristic: ``pair_key`` builds it from the fields that define "the same problem played
the same way", and an unmatched episode is reported rather than approximately matched.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .episode import RunDir, episode_payload

# The fields whose equality defines "the same problem, played the same way" — the default pairing key. ``arm``
# matters because the protocol arm (moves_only vs moves_chat) changes the action space, and ``cell`` because a
# sweep cell changes the situational config.
DEFAULT_PAIR_KEY = ("instance_id", "seed", "arm", "cell")


def pair_key(episode: dict, fields: tuple[str, ...] = DEFAULT_PAIR_KEY) -> tuple:
    """The pairing key of an episode: the tuple of its ``fields``. Two episodes with equal keys were played on the
    identical instance, seed, protocol arm, and sweep cell, and so differ only in who sat where."""
    return tuple(episode.get(f) for f in fields)


def _slot(turn: dict) -> tuple:
    """A turn's comparable slot in a fixed-rotation protocol: ``(round, phase, seat)``."""
    return (turn.get("round"), turn.get("phase"), turn.get("seat"))


def _public_signature(turn: dict | None) -> tuple | None:
    """What the rest of the table could observe of a turn: its action type, the deal or offer it named, and the
    public message. Reasoning is deliberately excluded — two occupants that made the same move have not diverged
    just because one of them was a policy with no scratchpad to record."""
    if turn is None:
        return None
    a = turn.get("action") or {}
    return (a.get("atype"), a.get("deal_index"), a.get("offer"), (a.get("message") or "").strip())


def _by_slot(turns: list[dict]) -> dict[tuple, dict]:
    """Turns keyed by ``(round, phase, seat, occurrence)``.

    The occurrence counter is load-bearing. A seat can legitimately take the SAME ``(round, phase, seat)`` slot
    twice — the engine's one-retry rule re-asks after a malformed response — and keying on the slot alone silently
    drops the first attempt, because the later turn overwrites it in the dict. That is exactly the turn worth
    seeing: on the contaminated campaign cells the dropped attempt is the ENGINE-FABRICATED one, so a comparison
    keyed without the counter under-reports the contamination it exists to show (measured: 24 of 24 fabricated
    turns invisible on one page). Counting occurrences also pairs first-attempt with first-attempt and retry with
    retry, rather than comparing one side's retry against the other side's original."""
    seen: dict[tuple, int] = {}
    out: dict[tuple, dict] = {}
    for t in turns:
        slot = _slot(t)
        n = seen.get(slot, 0)
        seen[slot] = n + 1
        out[(*slot, n)] = t
    return out


def align(left: dict, right: dict) -> tuple[list[dict], int | None]:
    """Align two episode payloads slot by slot and locate the divergence point.

    Returns ``(rows, divergence)`` where each row is ``{round, phase, seat, attempt, left_idx, right_idx,
    different}`` — the turn indices into each side's ``turns`` list, or ``None`` where only one side has that slot
    (one episode closed early, or only one side needed a retry) — and ``divergence`` is the row position of the
    FIRST behavioural difference, or ``None`` if the two episodes played identically throughout. ``attempt`` is 0
    for a seat's first go at a slot and 1+ for an engine retry (see :func:`_by_slot`)."""
    lt, rt = _by_slot(left.get("turns") or []), _by_slot(right.get("turns") or [])
    slots = list(lt) + [s for s in rt if s not in lt]
    slots.sort(key=lambda s: (min(lt.get(s, {}).get("idx", 10 ** 9), rt.get(s, {}).get("idx", 10 ** 9)), str(s)))
    rows = []
    for s in slots:
        l, r = lt.get(s), rt.get(s)
        rows.append({"round": s[0], "phase": s[1], "seat": s[2], "attempt": s[3],
                     "left_idx": (l or {}).get("idx"), "right_idx": (r or {}).get("idx"),
                     "left_kind": (l or {}).get("kind"), "right_kind": (r or {}).get("kind"),
                     "different": _public_signature(l) != _public_signature(r)})
    divergence = next((i for i, row in enumerate(rows) if row["different"]), None)
    return rows, divergence


def focal_seats(left: dict, right: dict) -> list[dict]:
    """The seats whose OCCUPANT KIND differs between the two episodes — the substitution being measured. Each entry
    is ``{party, name, left_kind, right_kind}``. An empty list means the two runs put the same kind of agent in
    every seat, which the page reports as "no seat swap detected" rather than inventing a focal seat."""
    lk = {s["name"]: s for s in left.get("seats") or []}
    out = []
    for seat in right.get("seats") or []:
        other = lk.get(seat["name"])
        if other and other.get("kind") != seat.get("kind"):
            out.append({"party": seat.get("party"), "name": seat.get("name"),
                        "left_kind": other.get("kind"), "right_kind": seat.get("kind")})
    return out


def _capture(payload: dict, party: int | None) -> float | None:
    """A party's share of the surplus that was available to it: realized surplus / its ideal surplus over the IR
    set. The scale-invariant per-seat outcome measure — raw points sit on private scales, so a seat's surplus is
    only comparable across instances once divided by the most it could have got."""
    game, outcome = payload.get("game"), payload.get("outcome") or {}
    realized = outcome.get("per_party_surplus") or outcome.get("realized_surplus")
    if not (game and realized and party is not None and party < len(realized)):
        return None
    ideal = (game.get("ideal_surplus") or [])
    if party >= len(ideal) or not ideal[party]:
        return None
    return round(float(realized[party]) / float(ideal[party]), 4)


def _mean(values, indices) -> float | None:
    """The mean of ``values`` at ``indices``, or ``None`` if none of them is a recorded number — so a metric that
    is absent on one side stays absent instead of averaging to a number that was never measured."""
    picked = [values[i] for i in indices if i < len(values) and isinstance(values[i], (int, float))]
    return round(sum(picked) / len(picked), 4) if picked else None


def score_table(left: dict, right: dict, focal: list[int] | int | None) -> list[dict]:
    """The quantified comparison: one row per metric with both values and the paired delta ``right - left``.

    ``focal`` is the party index (or list of them) whose occupant was swapped. A one-seat swap gets that seat's own
    surplus and capture; a swap that replaced several seats at once — a mixed table against an all-LLM table
    replaces every seat but one — gets the MEAN over the swapped set, labelled with its size, because attributing
    the effect to any single one of those seats would be wrong. The rows are omitted entirely when there is no swap
    to attribute an effect to.

    Every row carries ``higher_is_better`` so the page can colour a delta without guessing (``0`` means neither
    direction is better, e.g. rounds used), and ``None`` values pass through as ``None`` rather than zero — a
    metric that was not recorded is missing, not neutral."""
    parties = ([focal] if isinstance(focal, int) else list(focal or []))
    lo, ro = left.get("outcome") or {}, right.get("outcome") or {}
    rows: list[dict] = []

    def add(metric: str, lv, rv, *, better: int = 1, note: str = ""):
        delta = (round(float(rv) - float(lv), 4)
                 if isinstance(lv, (int, float)) and isinstance(rv, (int, float)) else None)
        rows.append({"metric": metric, "left": lv, "right": rv, "delta": delta,
                     "higher_is_better": better, "note": note})

    add("deal reached", int(bool(lo.get("deal"))), int(bool(ro.get("deal"))), note="1 = a deal closed")
    add("primary score", lo.get("primary"), ro.get("primary"), note="the scenario's normalized headline score")
    add("joint welfare USW", lo.get("usw"), ro.get("usw"), note="sum of realized surpluses (raw points)")
    add("egalitarian ESW", lo.get("esw"), ro.get("esw"), note="worst-off party's surplus")
    add("Nash welfare (geometric mean)", lo.get("nsw_geomean"), ro.get("nsw_geomean"),
        note="the readable form of the surplus product; 0 when any party is below threshold")
    add("Gini of surplus", lo.get("gini"), ro.get("gini"), better=-1, note="0 = equal split of surplus")
    add("IR violations", lo.get("n_ir_violations"), ro.get("n_ir_violations"), better=-1,
        note="parties that ended below their own threshold")
    if parties:
        one = len(parties) == 1
        label = "focal seat" if one else f"swapped seats (mean of {len(parties)})"
        lps, rps = (lo.get("per_party_surplus") or []), (ro.get("per_party_surplus") or [])
        add(f"{label} surplus", _mean(lps, parties), _mean(rps, parties),
            note="realized surplus of the seat(s) whose occupant was swapped, raw points")
        add(f"{label} capture",
            _mean([_capture(left, p) for p in parties], range(len(parties))),
            _mean([_capture(right, p) for p in parties], range(len(parties))),
            note="surplus / the most that seat could have got — scale-invariant, so comparable across instances")
    add("rounds used", left.get("episode", {}).get("rounds_used"), right.get("episode", {}).get("rounds_used"),
        better=0, note="")
    add("parse/legality errors",
        (lo.get("syntax_errors") or 0) + (lo.get("legality_errors") or 0),
        (ro.get("syntax_errors") or 0) + (ro.get("legality_errors") or 0), better=-1, note="")
    return rows


def compare_payload(left: dict, right: dict, *, left_label: str = "A", right_label: str = "B",
                    pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY) -> dict:
    """One seat-swap comparison, ready to render: both episode payloads, the slot alignment, the divergence point,
    the focal seat(s), and the score table.

    Both sides keep their FULL episode payload, so the comparison page reuses the same transcript and frontier
    renderer as a single-episode page — the frontier is drawn once, from the shared instance, with both
    trajectories on it. The two episodes are not required to be a valid pair; a mismatch on the pairing key is
    recorded in ``pairing.matched`` and surfaced as a warning instead of being rejected, because comparing two
    deliberately unrelated episodes is sometimes exactly what a reader wants."""
    rows, divergence = align(left, right)
    focal = focal_seats(left, right)
    focal_parties = [f["party"] for f in focal if f.get("party") is not None]
    lk, rk = pair_key(left.get("episode") or {}, pair_fields), pair_key(right.get("episode") or {}, pair_fields)
    return {
        "kind": "compare",
        "left": left, "right": right,
        "labels": {"left": left_label, "right": right_label},
        "pairing": {"fields": list(pair_fields), "left": list(lk), "right": list(rk), "matched": lk == rk,
                    "shared_game": (left.get("episode", {}).get("instance_id")
                                    == right.get("episode", {}).get("instance_id"))},
        "aligned": rows,
        "divergence": divergence,
        "focal_seats": focal,
        "focal_parties": focal_parties,
        "scores": score_table(left, right, focal_parties),
    }


# How to choose WHICH matched pairs to render when ``limit`` renders only some of them.
#   "first"          — the first pairs in sorted key order. Deterministic and arbitrary.
#   "largest-effect" — the pairs whose primary score moved MOST between the two conditions. What a reader wants
#                      when spot-checking a campaign: a limited sample of "first" pairs can easily be all
#                      no-deal-on-both, showing nothing, while the same budget spent on the largest movers shows
#                      the cases the aggregate effect is actually made of.
#   "deal-flip"      — pairs where a deal closed on exactly one side; the qualitative transition, ranked by effect.
#   "most-fabricated" — pairs ranked by how many turns the ENGINE fabricated rather than generated, on either
#                      side. For showing what a generation-failure bug actually did to a run: pairing a
#                      contaminated episode against its clean re-run makes the damage visible turn by turn, and
#                      the arbitrary "first" pairs are usually the least illustrative ones.
SELECTIONS = ("first", "largest-effect", "deal-flip", "most-fabricated")


def pair_runs(left_run: str | Path, right_run: str | Path, *, pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
              limit: int | None = None, reconstruct: bool = True,
              select: str = "first", annotations_dirname: str = "annotations") -> tuple[list[dict], dict]:
    """Pair every episode of one run against its key-matched counterpart in another, and build a comparison
    payload for each.

    Returns ``(comparisons, report)``. The report counts matched pairs and lists unmatched keys on each side, so a
    partially-complete campaign is visible as such. Where a key matches several episodes on a side (repeated
    seeds), they are zipped in sorted episode-id order and the multiplicity is recorded.

    ``select`` (one of :data:`SELECTIONS`) decides which pairs ``limit`` keeps. Ranking reads only each episode's
    stored ``outcome``, so choosing among hundreds of pairs costs nothing — the expensive payload build happens
    only for the pairs that survive the limit. The report records the selection, because "the 6 largest movers" and
    "6 arbitrary pairs" support very different readings of the same page count.

    ``annotations_dirname`` selects the per-run annotation subdirectory BOTH runs read their post-hoc oracles from
    (default ``"annotations"``; e.g. ``"annotations_v1"`` — see :class:`~interlens.arena.viz.episode.RunDir`).

    Both runs' geometry caches are per-``RunDir``; the LEFT run's geometry is used for both sides of a pair so the
    frontier is built once and the two trajectories are provably drawn against the same numbers."""
    if select not in SELECTIONS:
        raise ValueError(f"unknown pair selection {select!r}; choose one of {list(SELECTIONS)}")
    left_dir = RunDir(left_run, annotations_dirname=annotations_dirname)
    right_dir = RunDir(right_run, annotations_dirname=annotations_dirname)
    left_by_key, right_by_key = _group(left_dir, pair_fields), _group(right_dir, pair_fields)
    shared = sorted(set(left_by_key) & set(right_by_key), key=str)
    candidates, multiplicity = [], {}
    for key in shared:
        if len(left_by_key[key]) != len(right_by_key[key]):
            multiplicity[str(key)] = [len(left_by_key[key]), len(right_by_key[key])]
        candidates.extend(zip(sorted(left_by_key[key]), sorted(right_by_key[key])))
    if select != "first":
        candidates = _rank(candidates, select)
    chosen = candidates[:limit] if limit is not None else candidates
    comparisons = [
        compare_payload(left_dir.payload(lpath, reconstruct=reconstruct),
                        _payload_with_shared_geometry(right_dir, rpath, left_dir, reconstruct=reconstruct),
                        left_label=left_dir.root.name, right_label=right_dir.root.name, pair_fields=pair_fields)
        for lpath, rpath in chosen]
    report = {
        "left_run": str(left_dir.root), "right_run": str(right_dir.root),
        "pair_fields": list(pair_fields), "select": select,
        "n_left": sum(len(v) for v in left_by_key.values()),
        "n_right": sum(len(v) for v in right_by_key.values()),
        "n_matched_keys": len(shared), "n_candidate_pairs": len(candidates), "n_comparisons": len(comparisons),
        "unmatched_left": [str(k) for k in sorted(set(left_by_key) - set(right_by_key), key=str)][:50],
        "unmatched_right": [str(k) for k in sorted(set(right_by_key) - set(left_by_key), key=str)][:50],
        "uneven_multiplicity": multiplicity,
    }
    return comparisons, report


def _rank(candidates: list[tuple[Path, Path]], select: str) -> list[tuple[Path, Path]]:
    """Order candidate pairs by how much the outcome moved, reading only the stored ``outcome`` of each episode.

    ``deal-flip`` keeps only the pairs where exactly one side closed a deal; ``most-fabricated`` ranks by the count
    of engine-fabricated turns across the pair and drops pairs with none (there is nothing to show);
    ``largest-effect`` keeps everything. Ties break on the file paths so the choice is deterministic across runs."""
    import json
    from ..engine import gen_failures
    scored = []
    for lpath, rpath in candidates:
        try:
            left = json.loads(lpath.read_text())
            right = json.loads(rpath.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        lo, ro = (left.get("outcome") or {}), (right.get("outcome") or {})
        if select == "most-fabricated":
            n = len(gen_failures(left)) + len(gen_failures(right))
            if not n:
                continue
            scored.append((-n, str(lpath), str(rpath), (lpath, rpath)))
            continue
        flip = bool(lo.get("deal")) != bool(ro.get("deal"))
        if select == "deal-flip" and not flip:
            continue
        effect = abs(float(ro.get("primary") or 0.0) - float(lo.get("primary") or 0.0))
        scored.append((-effect, str(lpath), str(rpath), (lpath, rpath)))
    return [row[3] for row in sorted(scored)]


def _group(run: RunDir, pair_fields: tuple[str, ...]) -> dict[tuple, list[Path]]:
    """Episode file paths grouped by pairing key, reading only the key fields from each record."""
    import json
    out: dict[tuple, list[Path]] = {}
    for f in run.episode_files():
        try:
            ep = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if ep.get("episode_id"):
            out.setdefault(pair_key(ep, pair_fields), []).append(f)
    return out


def _payload_with_shared_geometry(run: RunDir, path: Path, geometry_from: RunDir, *,
                                 reconstruct: bool) -> dict[str, Any]:
    """The right side's payload built against the LEFT run's geometry for the shared instance, falling back to its
    own when the two runs' instance pools do not overlap (which the pairing report already flags)."""
    import json
    episode = json.loads(Path(path).read_text())
    geo = geometry_from.geometry(episode.get("instance_id")) or run.geometry(episode.get("instance_id"))
    instance = (geometry_from.instances.get(episode.get("instance_id"))
                or run.instances.get(episode.get("instance_id")))
    paths = {"run": str(run.root), "episode": str(Path(path).resolve())}
    if run.annotation_paths.get(episode.get("episode_id")):
        paths["annotation"] = str(run.annotation_paths[episode["episode_id"]])
    annotation = run.annotations.get(episode.get("episode_id"))
    # The run-level hazard and re-derivation sidecars come from THIS side's own run directory, never the
    # geometry donor's: whether one half of a pair carries a spoiled vintage is exactly the question a comparison
    # exists to answer, and inheriting the left run's answer would hide the mismatch it was built to show.
    if run.vintage:
        paths["vintage"] = run.vintage["path"]
    return episode_payload(episode, instance, annotation,
                           manifest=run.manifest, geometry=geo, reconstruct=reconstruct, paths=paths,
                           annotations_source=(run.annotations_dirname if annotation is not None else None),
                           vintage=run.vintage, derivation=run.derivation)

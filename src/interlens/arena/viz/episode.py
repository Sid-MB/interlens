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

"""One stored episode, turned into the single JSON payload the interactive page renders.

This is the data layer of the episode visualizer: it reads a run's three record stores — the ``Episode`` JSON, the
``Instance`` it was played on, and (optionally) the post-hoc annotation record — and merges them into one
self-describing dict. Everything the page shows is computed here; the browser only draws it.

What the merge adds beyond the raw records:

- **numbers on every turn** — the action's deal placed in the instance's geometry (per-party surplus vs each
  threshold, welfare scalars, distance below the frontier), plus per-oracle chosen/best/regret values.
- **the rational-agent counterfactual** — for every oracle that scored the turn, the action it would have taken
  instead, resolved to a deal and its numbers, so the page can show "the model did X (value v) where the oracle
  would have done Y (value v*), regret v* - v" side by side. Runs without a ``bestresponse`` oracle are reported
  as such rather than silently rendering an empty column.
- **seat identity** — which seats were played by an LLM and which by a computable policy, so a mixed table reads
  correctly and a seat-swap comparison knows its focal seat. Read from the run manifest's recorded invocation
  when available, else inferred from generation accounting (a policy seat emits zero output tokens).
- **prompt provenance** — the exact rendered view per turn, marked ``stored`` when the episode recorded it,
  ``reconstructed`` when it was re-derived by deterministic replay through the scenario state machine (current
  prompt code, so it can differ from what the model actually saw), or ``absent``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..actions import action_from_json
from .geometry import GameGeometry

# Oracles whose verdict names a full counterfactual DEAL rather than only a value, i.e. the ones that can drive
# the per-step "what would a rational agent have done here" column. ``bestresponse`` is the one the campaigns run.
COUNTERFACTUAL_ORACLES = ("bestresponse",)

# The provenance marker for a reconstructed view on a RETRY turn — a second turn in the same (round, phase, seat)
# slot, which the engine issued after a malformed first attempt. Replay re-issues the original request, so the
# reconstruction is the first attempt's prompt and is missing the repair instruction the model actually saw. Kept
# distinct from plain ``reconstructed`` so a prompt audit can see exactly which panels are known-incomplete.
RETRY_SOURCE = "reconstructed_pre_retry"


# --------------------------------------------------------------------------------- seat identity --
def seat_kinds(episode: dict, manifest: dict | None = None) -> dict:
    """Which seats an LLM played and which a computable policy played.

    Returns ``{"kinds": {seat_name: "llm" | "policy"}, "source": str, "detail": str}``. The manifest's recorded
    ``invocation`` is authoritative when present, because it names the table type exactly:
    ``all_llm`` / ``all_rational`` assign every seat; ``mixed`` puts the models in the leading seats and fills the
    rest with policies; ``reverse_mixed`` / ``advocate_mixed`` make exactly ``--rational-seat`` a policy.

    Without a manifest the kinds are INFERRED from generation accounting: a policy seat is pure Python, so every
    one of its turns records ``n_tokens_out == 0``, while an LLM seat generated text. The inference is reported as
    such (``source="inferred"``) so a reader never mistakes it for recorded ground truth."""
    seats = [s.get("name") for s in (episode.get("seats") or []) if s.get("name")]
    argv = list((manifest or {}).get("invocation") or [])

    def flag(name: str) -> str | None:
        return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None

    def flag_list(name: str) -> list[str]:
        if name not in argv:
            return []
        out = []
        for token in argv[argv.index(name) + 1:]:
            if token.startswith("--"):
                break
            out.append(token)
        return out

    table = flag("--table")
    if table == "all_llm":
        return {"kinds": {s: "llm" for s in seats}, "source": "manifest", "detail": "table=all_llm"}
    if table == "all_rational":
        return {"kinds": {s: "policy" for s in seats}, "source": "manifest", "detail": "table=all_rational"}
    if table == "mixed":
        n_models = max(1, len(flag_list("--models")))
        return {"kinds": {s: ("llm" if i < n_models else "policy") for i, s in enumerate(seats)},
                "source": "manifest", "detail": f"table=mixed, {n_models} model seat(s) lead the rotation"}
    if table in ("reverse_mixed", "advocate_mixed"):
        try:
            rational = int(flag("--rational-seat") or 0)
        except ValueError:
            rational = 0
        kind = "policy" if table == "reverse_mixed" else "advocate"
        return {"kinds": {s: (kind if i == rational else "llm") for i, s in enumerate(seats)},
                "source": "manifest", "detail": f"table={table}, rational seat {rational}"}

    # Inference: a computable-policy seat never generates tokens.
    out_by_seat: dict[str, list[int]] = {}
    for t in episode.get("turns") or []:
        out_by_seat.setdefault(t.get("seat"), []).append(int(t.get("n_tokens_out") or 0))
    kinds = {}
    for s in seats:
        counts = out_by_seat.get(s) or []
        kinds[s] = "policy" if (counts and max(counts) == 0) else "llm"
    return {"kinds": kinds, "source": "inferred",
            "detail": "inferred from per-turn output-token accounting (a policy seat generates none); "
                      "no run manifest was found to confirm it"}


# ------------------------------------------------------------------------------- oracle records --
def _oracle_records(episode: dict, annotation: dict | None) -> dict[int, dict[str, dict]]:
    """``{turn_idx: {oracle_name: record}}`` merged from the episode's inline ``round_checkpoints`` and the
    post-hoc annotation store. Annotation records win on a name collision: they are the later, re-scored pass
    (the campaigns' post-hoc ``bestresponse`` annotation is added this way and exists nowhere else)."""
    turns = episode.get("turns") or []
    by_round_seat = {(t.get("round"), t.get("seat")): t.get("idx") for t in turns}
    out: dict[int, dict[str, dict]] = {}

    def put(idx, name, rec):
        if idx is not None and name:
            out.setdefault(int(idx), {})[str(name)] = rec

    for rec in episode.get("round_checkpoints") or []:
        if rec.get("oracle") is None:            # a forked provisional probe, not an inline oracle verdict
            continue
        idx = rec.get("turn_idx")
        if idx is None or idx < 0:
            idx = by_round_seat.get((rec.get("round"), rec.get("seat")))
        put(idx, rec.get("oracle"), rec)
    for row in (annotation or {}).get("turns") or []:
        for name, rec in (row.get("oracle") or {}).items():
            put(row.get("turn_idx"), name, rec)
    return out


def _action_label(action: Any) -> str:
    """A compact human label for a stored action dict (``PROPOSE`` / ``ACCEPT P3`` / ``WALK`` / ``VOTE``)."""
    if not isinstance(action, dict):
        return "—"
    try:
        typed = action_from_json(action)
    except Exception:
        typed = None
    kind = (action.get("action") or action.get("atype") or action.get("type") or "").upper()
    if typed is not None:
        kind = typed.kind.upper()
    ref = action.get("offer_id") or action.get("offer") or action.get("id")
    return f"{kind} {ref}".strip() if ref else (kind or "—")


def _verdict_actions(verdict: dict) -> list[dict]:
    """A verdict's scored actions as ``[{key, label, deal, value}]``, reading BOTH stored ``action_values``
    shapes: the v1.1 ``{action_key: value}`` object (keys are the action's JSON, sorted) and the v1.0
    ``[{"action": {...}, "value": v}]`` list of pairs."""
    stored = verdict.get("action_values") or {}
    pairs: list[tuple[Any, Any]] = []
    if isinstance(stored, list):
        pairs = [(item.get("action"), item.get("value")) for item in stored if isinstance(item, dict)]
    elif isinstance(stored, dict):
        for key, value in stored.items():
            try:
                pairs.append((json.loads(key), value))
            except (TypeError, json.JSONDecodeError):
                pairs.append(({"action": key}, value))
    out = []
    for action, value in pairs:
        out.append({"label": _action_label(action), "deal": (action or {}).get("deal"),
                    "value": (round(float(value), 4) if isinstance(value, (int, float)) else None)})
    return out


def _best_action(verdict: dict) -> dict | None:
    """The verdict's ``best`` action as a dict, decoding the v1.1 action-key string or the v1.0 nested object."""
    best = verdict.get("best")
    if isinstance(best, str):
        try:
            return json.loads(best)
        except json.JSONDecodeError:
            return None
    return best if isinstance(best, dict) else None


def _oracle_payload(name: str, rec: dict, geo: GameGeometry | None) -> dict:
    """One oracle's read of one turn, with its counterfactual resolved into the game's geometry.

    ``best_deal_index`` is the deal the oracle would have put on the table. It prefers the verdict's
    ``extra.best_response_deal`` — a best-response oracle's *unconstrained* optimum, which is the honest answer to
    "what would a rational agent have done" even when its own best scored action was to accept a standing offer —
    and falls back to the deal carried by the best scored action."""
    verdict = rec.get("verdict") or {}
    extra = verdict.get("extra") or {}
    best = _best_action(verdict)
    deal = extra.get("best_response_deal")
    if deal is None and isinstance(best, dict):
        deal = best.get("deal")
    return {
        "oracle": name,
        "chosen_value": rec.get("chosen_value"),
        "best_value": rec.get("best_value"),
        "divergence": rec.get("divergence"),
        "flags": list(rec.get("flags") or verdict.get("flags") or []),
        "best_label": _action_label(best),
        "best_deal_index": (geo.deal_index(deal) if (geo is not None and deal is not None) else None),
        "action_values": _verdict_actions(verdict),
        "extra": {k: v for k, v in extra.items() if k != "surplus_loss"},
        "counterfactual": name in COUNTERFACTUAL_ORACLES,
    }


# ------------------------------------------------------------------------------ view provenance --
def reconstruct_views(episode: dict, instance: dict) -> dict[int, list[dict]]:
    """Re-derive each turn's rendered view by deterministic replay, for episodes recorded before the per-turn
    ``view`` field existed.

    Feeds the stored turns back through the scenario's state machine (``arena.replay``) and captures the
    ``SeatRequest.view`` the machine builds for each one. Exact for the state, but the prompt TEXT comes from
    today's prompt code — so a reconstructed view is what the current build would show a seat at that state, not a
    byte-guaranteed record of what the model saw, and the page labels it accordingly.

    One difference is systematic rather than a drift risk, and the caller marks it separately (see
    :data:`RETRY_SOURCE`): when a seat's malformed response triggered the engine's one retry, the LIVE retry view
    carried the failed attempt plus a repair instruction, while replay re-issues the original request. A retry
    turn's reconstruction is therefore the FIRST attempt's prompt; the repair text is not recoverable from the
    record.

    Returns ``{}`` on any failure (unknown scenario, prompt/state drift), because a missing prompt panel is a far
    better outcome than a crashed export."""
    try:
        from ..replay import replay_episode
        from ..scenarios import SCENARIOS
        from ..schema import Instance
        scenario_cls = SCENARIOS[episode["scenario"]]
        captured: dict[int, list[dict]] = {}

        def on_turn(state, request, turn):
            if getattr(request, "view", None):
                captured[int(turn["idx"])] = [dict(m) for m in request.view]

        replay_episode(scenario_cls(), Instance.from_json(instance), episode, on_turn=on_turn)
        return captured
    except Exception:
        return {}


# -------------------------------------------------------------------------------- the payload --
def episode_payload(episode: dict, instance: dict | None = None, annotation: dict | None = None, *,
                    manifest: dict | None = None, geometry: GameGeometry | None = None,
                    reconstruct: bool = True, paths: dict | None = None) -> dict:
    """The complete render payload for one episode.

    Parameters
    ----------
    episode : dict
        A stored ``Episode.to_json()`` record.
    instance : dict, optional
        The ``Instance`` record the episode was played on. Without it there is no game geometry, so the frontier
        and side panels are omitted and the page renders the transcript alone.
    annotation : dict, optional
        The post-hoc annotation record (``{episode_id, summary, turns:[{turn_idx, oracle:{...}}]}``), which is
        where a re-scored oracle such as ``bestresponse`` lives for runs annotated after the fact.
    manifest : dict, optional
        The run's ``manifest.json``, read for the recorded invocation (seat kinds, policies, oracle list).
    geometry : GameGeometry, optional
        A prebuilt geometry to reuse — pass the SAME object for both episodes of a comparison so the two
        trajectories are drawn against one identical frontier (and the ``|D| x n`` tables are built once).
    reconstruct : bool
        When an episode carries no stored per-turn views, re-derive them by replay (see
        :func:`reconstruct_views`) and mark them ``reconstructed``. ``False`` reports them as ``absent``.
    paths : dict, optional
        Absolute source paths to link from the page (``episode``, ``instance``, ``annotation``, ``run``).
    """
    geo = geometry if geometry is not None else GameGeometry.from_instance(instance or {})
    kinds = seat_kinds(episode, manifest)
    oracles = _oracle_records(episode, annotation)
    turns = episode.get("turns") or []
    stored_views = sum(1 for t in turns if t.get("view"))
    rebuilt = reconstruct_views(episode, instance) if (reconstruct and not stored_views and instance) else {}

    seat_party = {s.get("name"): i for i, s in enumerate(episode.get("seats") or [])}
    rows, trajectory, slots_seen = [], [], set()
    for t in turns:
        slot = (t.get("round"), t.get("phase"), t.get("seat"))
        is_retry = slot in slots_seen
        slots_seen.add(slot)
        idx = int(t.get("idx", len(rows)))
        parsed = t.get("parsed_action") if isinstance(t.get("parsed_action"), dict) else {}
        named = parsed.get("deal_named") or parsed.get("deal")
        deal_index = geo.deal_index(named) if geo is not None else None
        view, source = t.get("view"), "stored"
        if not view:
            view = rebuilt.get(idx)
            source = ((RETRY_SOURCE if is_retry else "reconstructed") if idx in rebuilt else "absent")
        turn_oracles = {name: _oracle_payload(name, rec, geo) for name, rec in (oracles.get(idx) or {}).items()}
        row = {
            "idx": idx, "round": t.get("round"), "phase": t.get("phase"), "seat": t.get("seat"),
            "party": seat_party.get(t.get("seat")),
            "kind": kinds["kinds"].get(t.get("seat"), "llm"),
            "action": {
                "atype": parsed.get("atype") or parsed.get("action") or ("none" if parsed else "unparsed"),
                "label": _action_label({"action": parsed.get("atype"), "offer_id": parsed.get("offer")}),
                "deal_named": named if isinstance(named, dict) else None,
                "deal_index": deal_index,
                "offer": parsed.get("offer") or parsed.get("offer_id"),
                "message": parsed.get("message"),
                "syntax_error": parsed.get("syntax_error"),
            },
            "parse_ok": bool(t.get("parse_ok")),
            "content": t.get("content"),
            "reasoning": parsed.get("thinking") or t.get("reasoning"),
            "reasoning_provenance": t.get("reasoning_provenance") or "none",
            "n_tokens_out": t.get("n_tokens_out"), "n_tokens_in": t.get("n_tokens_in"),
            "cap": t.get("cap"), "stop_reason": t.get("stop_reason"),
            "view": view, "view_source": source,
            "oracles": turn_oracles,
        }
        if deal_index is not None and geo is not None:
            row["deal"] = geo.at(deal_index).to_json()
            row["deal_welfare"] = geo.welfare_of(deal_index)
            trajectory.append({"turn_idx": idx, "ordinal": len(trajectory) + 1, "seat": t.get("seat"),
                               "kind": row["kind"], "index": deal_index, "atype": row["action"]["atype"]})
        rows.append(row)

    outcome = dict(episode.get("outcome") or {})
    agreed = geo.deal_index(outcome.get("deal_named") or outcome.get("deal")) if geo is not None else None
    if agreed is None and "nsw" in outcome:
        # No deal closed, so no surplus was realized: Nash welfare is 0, exactly as the stored usw/esw/nsw are.
        # Set it explicitly rather than leaving it absent, or a comparison against an episode that DID close would
        # render "no deal" as a missing measurement instead of the zero it is.
        outcome["nsw_geomean"] = 0.0
    if agreed is not None:
        outcome["deal_index"] = agreed
        outcome["deal_geometry"] = geo.at(agreed).to_json()
        # The stored ``nsw`` is the RAW surplus product, which explodes with the party count (a 6-party deal runs
        # to 1e11) and is unreadable beside USW/ESW. Carry the geometric mean, which lives on the same scale as
        # the other welfare scalars, so the page can report Nash welfare in a form a reader can compare.
        outcome["nsw_geomean"] = geo.welfare_of(agreed)["nsw_geomean"]

    oracle_names = sorted({name for per_turn in oracles.values() for name in per_turn})
    payload = {
        "kind": "episode",
        "episode": {k: episode.get(k) for k in
                    ("episode_id", "scenario", "arm", "model", "level", "instance_id", "seed", "cell", "cell_cfg",
                     "status", "rounds_used", "tokens_in", "tokens_out", "cost_usd", "gen_config", "error",
                     "schema_version")},
        "seats": [{"name": s.get("name"), "role": s.get("role"), "variant": s.get("variant"),
                   "party": i, "kind": kinds["kinds"].get(s.get("name"), "llm")}
                  for i, s in enumerate(episode.get("seats") or [])],
        "seat_kind_source": {"source": kinds["source"], "detail": kinds["detail"]},
        "turns": rows,
        "trajectory": trajectory,
        "outcome": outcome,
        "oracle_names": oracle_names,
        "counterfactual_oracles": [n for n in oracle_names if n in COUNTERFACTUAL_ORACLES],
        "annotation_summary": (annotation or {}).get("summary"),
        "views": {"stored": stored_views, "reconstructed": len(rebuilt), "n_turns": len(turns),
                  "reconstructed_pre_retry": sum(1 for r in rows if r["view_source"] == RETRY_SOURCE)},
        "game": geo.to_json() if geo is not None else None,
        "manifest": {k: (manifest or {}).get(k) for k in
                     ("run_name", "invocation", "table", "arms", "policies", "models", "oracles", "scaffold",
                      "info", "provenance")} if manifest else None,
        "paths": paths or {},
    }
    return payload


# ------------------------------------------------------------------------------ run-dir loading --
class RunDir:
    """A run directory's three record stores, indexed for lookup: ``episodes/``, ``instances/``, ``annotations/``,
    plus ``manifest.json``. Geometry is built lazily and CACHED per instance, so a run whose 120 episodes share 6
    instances builds 6 utility matrices rather than 120."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.episodes_dir = self.root / "episodes" if (self.root / "episodes").is_dir() else self.root
        self.instances, self.instance_paths = _index_records(self.root / "instances", "instance_id",
                                                            require="payload")
        self.annotations, self.annotation_paths = _index_records(self.root / "annotations", "episode_id")
        manifest = self.root / "manifest.json"
        self.manifest = json.loads(manifest.read_text()) if manifest.is_file() else None
        self._geometry: dict[str, GameGeometry | None] = {}

    def episode_files(self) -> list[Path]:
        """Every episode JSON under the run, in sorted path order."""
        return sorted(p for p in self.episodes_dir.glob("**/*.json") if p.name != "manifest.json")

    def geometry(self, instance_id: str) -> GameGeometry | None:
        """The cached :class:`GameGeometry` for an instance id (``None`` if the instance is missing or not a
        scorable game)."""
        if instance_id not in self._geometry:
            self._geometry[instance_id] = GameGeometry.from_instance(self.instances.get(instance_id) or {})
        return self._geometry[instance_id]

    def payload(self, episode_path: str | Path, *, reconstruct: bool = True) -> dict:
        """The render payload for one episode file in this run, with its instance, annotation, manifest, and
        cached geometry wired in."""
        episode_path = Path(episode_path)
        episode = json.loads(episode_path.read_text())
        instance_id = episode.get("instance_id")
        instance = self.instances.get(instance_id)
        annotation = self.annotations.get(episode.get("episode_id"))
        paths = {"run": str(self.root), "episode": str(episode_path.resolve())}
        for key, table in (("instance", self.instance_paths.get(instance_id)),
                           ("annotation", self.annotation_paths.get(episode.get("episode_id")))):
            if table is not None:
                paths[key] = str(table)
        return episode_payload(episode, instance, annotation, manifest=self.manifest,
                               geometry=self.geometry(instance_id), reconstruct=reconstruct, paths=paths)


def _index_records(path: Path, key: str, require: str | None = None) -> tuple[dict[str, dict], dict[str, Path]]:
    """Index the JSON records under ``path`` by their ``key`` field, returning ``(records, source_paths)``.

    One loader for both stores because their only differences are the id field and, for instances, that a file may
    hold either one record or a saved POOL (a JSON list). ``require`` names a field a record must also carry, which
    is what keeps a stray non-instance JSON in an ``instances/`` directory out of the index. Unparseable files are
    skipped rather than fatal — a run still being written should visualize."""
    records: dict[str, dict] = {}
    sources: dict[str, Path] = {}
    if not path.exists():
        return records, sources
    for f in ([path] if path.is_file() else sorted(path.glob("**/*.json"))):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for d in (data if isinstance(data, list) else [data]):
            if isinstance(d, dict) and d.get(key) and (require is None or require in d):
                records[d[key]] = d
                sources[d[key]] = f.resolve()
    return records, sources

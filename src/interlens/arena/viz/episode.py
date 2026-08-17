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
# [rational_agents: viz-sidebar] 2026-08-03

"""One stored episode, turned into the single JSON payload the interactive page renders.

This is the data layer of the episode visualizer: it reads a run's three record stores — the ``Episode`` JSON, the
``Instance`` it was played on, and (optionally) the post-hoc annotation record — and merges them into one
self-describing dict. Everything the page shows is computed here; the browser only draws it.

What the merge adds beyond the raw records:

- **numbers on every turn** — the action's deal placed in the instance's geometry (per-party surplus vs each
  threshold, welfare scalars, distance below the frontier), plus per-oracle chosen/best/regret values.
- **the post-hoc oracle counterfactual** — for every oracle that scored the turn, the action it ranks highest
  instead, resolved to a deal and its numbers, so the page can show "the model did X (value v) where the oracle
  would have done Y (value v*), regret v* - v" side by side. Runs without a ``bestresponse`` oracle are reported
  as such rather than silently rendering an empty column.
- **seat identity** — which seats were played by an LLM and which by a computable policy, so a mixed table reads
  correctly and a seat-swap comparison knows its focal seat. Read from the run manifest's recorded invocation
  when available, else inferred from generation accounting (a policy seat emits zero output tokens).
- **prompt provenance** — the exact rendered view per turn, marked ``stored`` when the episode recorded it,
  ``reconstructed`` when it was re-derived by deterministic replay through the scenario state machine (current
  prompt code, so it can differ from what the model actually saw), or ``absent``.
- **the public ledger** — which turns were actually PUBLISHED to the other seats, the offer id each proposal was
  registered under, and the deal standing on the table as of each turn (see :func:`public_ledger`). This is what
  the page's conversation view and per-agent issue view read, and it is deliberately reconstructed here rather
  than in the browser so the page can render it server-side.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..actions import action_from_json
from ..engine import EMPTY_TURN_PLACEHOLDER, gen_failures
from . import references
from .ballots import DERIVATION_SIDECAR, final_ballots, vote_derivation
from .census import turn_census
from .geometry import GameGeometry
from .hazards import generation_budget, vintage_provenance

# Decision references whose records name a counterfactual action or deal rather than only a scalar value, in
# presentation order, and the older spellings that mean the same thing. Both come from
# :mod:`~interlens.arena.viz.references`, which owns the 2x2 these live on (private vs omniscient information,
# self-interest vs table-fairness objective) and the unit each one's ``value`` is priced in.
COUNTERFACTUAL_ORACLES = references.REFERENCE_ORDER
COUNTERFACTUAL_ALIASES = references.ALIASES

#: How much of a silent turn's generated-but-unpublished text travels to the page. Enough to read what the seat
#: set out to do (a scratchpad states its intent in the first paragraph or two) and small enough that a dozen of
#: them on one page cost nothing; the untruncated text is in the episode record every page links to.
RAW_EXCERPT_CHARS = 2048

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
            canonical = COUNTERFACTUAL_ALIASES.get(str(name), str(name))
            out.setdefault(int(idx), {})[canonical] = rec

    def put_counterfactuals(idx, row):
        """Add direct decision references from one turn-like record.

        ``row`` may be a current :class:`TurnAnnotation` JSON object or a legacy oracle record. Direct references
        win over an oracle of the same name because they were computed specifically for the three-way decision
        comparison rather than inferred from a generic scored verdict.
        """
        for name, rec in ((row or {}).get("counterfactuals") or {}).items():
            if isinstance(rec, dict):
                put(idx, name, dict(rec, _direct_counterfactual=True))

    for rec in episode.get("round_checkpoints") or []:
        idx = rec.get("turn_idx")
        if idx is None or idx < 0:
            idx = by_round_seat.get((rec.get("round"), rec.get("seat")))
        put_counterfactuals(idx, rec)
        if rec.get("oracle") is None:            # a forked provisional probe, not an inline oracle verdict
            continue
        put(idx, rec.get("oracle"), rec)
    for turn in turns:
        put_counterfactuals(turn.get("idx"), turn)
    for row in (annotation or {}).get("turns") or []:
        for name, rec in (row.get("oracle") or {}).items():
            put(row.get("turn_idx"), name, rec)
        put_counterfactuals(row.get("turn_idx"), row)
    return out


def _action_kind(action: Any) -> str:
    """A stored action's kind, lowercased (``propose`` / ``accept`` / ``reject`` / ``walk`` / ``vote``), or ``""``.

    Prefers the typed parse (``arena.actions.action_from_json``) and falls back to whichever of the three stored
    spellings the record carries, so the SAME answer serves the page's label and the page's branching — a cell that
    renders "REJECT P1" and a cell that asks "was this an accept?" must not disagree about one action."""
    if not isinstance(action, dict):
        return ""
    try:
        typed = action_from_json(action)
    except Exception:
        typed = None
    if typed is not None:
        return typed.kind.lower()
    return str(action.get("action") or action.get("atype") or action.get("type") or "").lower()


def _action_label(action: Any) -> str:
    """A compact human label for a stored action dict (``PROPOSE`` / ``ACCEPT P3`` / ``WALK`` / ``VOTE``)."""
    if not isinstance(action, dict):
        return "—"
    kind = _action_kind(action).upper()
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
    and falls back to the deal carried by the best scored action.

    ``best_atype`` is the KIND of that recommended action (``accept`` / ``reject`` / ``propose`` / ``walk``), so a
    page can branch on the recommendation — "explain a rejection, but never an accept" — by reading the stored
    action rather than by pattern-matching the display label ``best_label`` was formatted into."""
    if rec.get("_direct_counterfactual"):
        action = rec.get("action")
        label = _action_label(action) if isinstance(action, dict) else str(action or "—").upper()
        kind = _action_kind(action) if isinstance(action, dict) else str(action or "").lower()
        deal = rec.get("deal")
        direct_index = rec.get("deal_index")
        if not isinstance(direct_index, int):
            direct_index = geo.deal_index(deal) if (geo is not None and deal is not None) else None
        value = rec.get("value")
        # The reference registry decides the role, the axis, and — the part a page must not improvise — the unit
        # the stored ``value`` is priced in. An unknown direct reference falls back to the omniscient
        # self-interest reading, which is what every pre-registry record was.
        described = references.describe(name) or references.describe("oracle_omniscient")
        optimum = rec.get("table_optimum")
        shortfall = (round(float(optimum) - float(value), 6)
                     if isinstance(optimum, (int, float)) and isinstance(value, (int, float)) else None)
        return {
            "oracle": name,
            "chosen_value": rec.get("chosen_value"),
            "best_value": value,
            "divergence": rec.get("divergence"),
            "flags": list(rec.get("flags") or []),
            "best_label": label,
            "best_atype": kind,
            "best_deal_index": direct_index,
            "action_values": list(rec.get("action_values") or []),
            "extra": dict(rec.get("extra") or {}),
            "counterfactual": True,
            "counterfactual_role": described["role"],
            # ``information`` stays the record's own tag when it carries one (it is more specific than the axis
            # name: "own_private_sheet+public_actions_only"); the axis is separately available as
            # ``information_axis`` so a page can group by it without parsing a provenance string.
            "information": rec.get("information") or described["information"],
            "information_axis": described["information"],
            "objective": described["objective"],
            "reference_label": described["label"],
            "reference_short": described["short"],
            "value_label": described["value_label"],
            "unit": described["unit"],
            "value_basis": described["value_basis"],
            "comparable_across_information": described["comparable_across_information"],
            "gap_label": described["gap_label"],
            # A table objective's own ceiling and the acting seat's surplus at the same deal, present only on a
            # fairness record. ``shortfall`` is the ONLY regret a fairness row supports and it is in table
            # units — never in the seat's points, which is what ``own_surplus`` alone reports.
            "table_optimum": optimum,
            "own_surplus": rec.get("own_surplus"),
            "shortfall": shortfall,
        }
    verdict = rec.get("verdict") or {}
    extra = verdict.get("extra") or {}
    best = _best_action(verdict)
    deal = extra.get("best_response_deal")
    if deal is None and isinstance(best, dict):
        deal = best.get("deal")
    index_of = lambda d: (geo.deal_index(d) if (geo is not None and d is not None) else None)
    # A generic scored oracle (``threshold``, ``acceptance``, ``belief``) is not a decision reference and gets no
    # axis or unit strings — the page keeps rendering it through its older, name-agnostic path rather than
    # claiming an objective for it.
    described = references.describe(name)
    return {
        "oracle": name,
        "chosen_value": rec.get("chosen_value"),
        "best_value": rec.get("best_value"),
        "divergence": rec.get("divergence"),
        "flags": list(rec.get("flags") or verdict.get("flags") or []),
        "best_label": _action_label(best),
        "best_atype": _action_kind(best),
        "best_deal_index": index_of(deal),
        "action_values": _verdict_actions(verdict),
        "extra": {k: v for k, v in extra.items() if k != "surplus_loss"},
        "counterfactual": name in COUNTERFACTUAL_ORACLES,
        "counterfactual_role": described.get("role", name),
        "information": rec.get("information") or described.get("information"),
        "information_axis": described.get("information"),
        "objective": described.get("objective"),
        "reference_label": described.get("label"),
        "reference_short": described.get("short"),
        "value_label": described.get("value_label"),
        "unit": described.get("unit"),
        "value_basis": described.get("value_basis"),
        "comparable_across_information": described.get("comparable_across_information"),
        "gap_label": described.get("gap_label"),
        "table_optimum": None,
        "own_surplus": None,
        "shortfall": None,
    }


# --------------------------------------------------------------------------------- public ledger --
#: Offer ids are minted ``{prefix}{n}`` in registration order (``arena.actions.OfferRegistry``). The scorable
#: negotiation registers with ``P``; a run whose seats referenced some other prefix overrides this from the ids
#: the turns actually carry, so nothing here depends on guessing right.
OFFER_PREFIX = "P"


def public_ledger(rows: list[dict]) -> dict:
    """Reconstruct what the seats publicly saw, from the per-turn records alone.

    Three things the page needs and no stored record carries directly:

    - **published** — a turn that was a first attempt at a slot the seat later retried never reached the other
      seats: the engine's retry path returns the repair directive *before* publishing, so only the LAST turn in a
      ``(round, phase, seat)`` slot is public. A conversation view that showed the malformed attempt would be
      showing text no other party ever read.
    - **offer_id** — the id a proposal was registered under. ``OfferRegistry`` mints ids sequentially over
      published proposals that resolved to a legal deal, so replaying that counter over the turns reproduces the
      exact ids the seats quoted back (``ACCEPT P2``), which the stored record keeps only on the accepting side.
    - **standing_deal_index** — the deal on the table as of each turn: the offer this turn's action referenced if
      it referenced one, else the most recently registered offer, else ``None``. This is the deal the per-agent
      issue view puts its marker on.

    Returns ``{"offers": {offer_id: {...}}, "prefix": str}`` and annotates ``rows`` in place."""
    prefix = OFFER_PREFIX
    for row in rows:
        ref = (row.get("action") or {}).get("offer")
        if isinstance(ref, str) and ref[:1].isalpha() and ref[1:].isdigit():
            prefix = ref[0]
            break

    last_in_slot: dict[tuple, int] = {}
    for row in rows:
        last_in_slot[(row.get("round"), row.get("phase"), row.get("seat"))] = row["idx"]

    offers: dict[str, dict] = {}
    counter, standing = 0, None
    for row in rows:
        action = row.get("action") or {}
        published = last_in_slot.get((row.get("round"), row.get("phase"), row.get("seat"))) == row["idx"]
        offer_id = None
        if published and action.get("atype") == "propose" and action.get("deal_index") is not None:
            counter += 1
            offer_id = f"{prefix}{counter}"
            offers[offer_id] = {"offer_id": offer_id, "deal_index": action["deal_index"], "seat": row.get("seat"),
                                "party": row.get("party"), "turn_idx": row["idx"], "round": row.get("round")}
            standing = action["deal_index"]
        elif isinstance(action.get("offer"), str):
            offer_id = action["offer"]
            if offer_id in offers:
                standing = offers[offer_id]["deal_index"]
        row["published"] = published
        row["offer_id"] = offer_id
        row["standing_deal_index"] = standing
    return {"offers": offers, "prefix": prefix}


#: The action types that can close a negotiation: an acceptance, or the final ballot of a vote.
CLOSING_ACTIONS = ("accept", "vote")


def closing_turn_index(rows: list[dict], deal_index: int | None) -> int | None:
    """The index of the turn that CLOSED the deal, or ``None`` when nothing closed.

    The chart's AGREED square is the one mark that stands for an event without naming its turn, so a reader
    clicking it has nowhere to land unless this is derived. Preference order, most specific first: the last
    published closing action (accept, or a vote ballot) taken while the agreed deal was the one standing; then the
    last published closing action at all (protocols where the standing deal is not recoverable from the ledger);
    then the last turn, since an episode that closed a deal ended by doing so. Requires ``rows`` to have been
    through :func:`public_ledger`, which is what annotates ``published`` and ``standing_deal_index``."""
    if deal_index is None or not rows:
        return None
    published = [r for r in rows if r.get("published")]
    closing = [r for r in published if ((r.get("action") or {}).get("atype") in CLOSING_ACTIONS)]
    for row in reversed(closing):
        if row.get("standing_deal_index") == deal_index:
            return int(row["idx"])
    return int((closing or published or rows)[-1]["idx"])


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


def _turn_payload(t: dict, idx: int, *, is_retry: bool, geo: GameGeometry | None, kinds: dict,
                  oracles: dict, seat_party: dict, rebuilt: dict, fabricated: dict) -> dict:
    """One turn's render row — the per-turn unit :func:`episode_payload` builds its ``turns`` list from.

    Split out so a LIVE page can build the row for a single arriving turn with exactly the code a full payload
    rebuild uses (``arena.live.payload.turn_delta``): a streamed row is then byte-identical to the one a reload
    produces, and the two can never drift.

    Everything the row needs that is not on the turn itself is passed in, since all of it is episode-scoped and
    computed once: ``geo`` (the game geometry, ``None`` without an instance), ``kinds`` (:func:`seat_kinds`),
    ``oracles`` (turn idx -> {oracle name: record}), ``seat_party`` (seat name -> party index), ``rebuilt``
    (replay-reconstructed views by turn idx) and ``fabricated`` (the ``gen_failures`` rows by turn idx).
    ``is_retry`` marks a turn whose (round, phase, seat) slot was already seen — a superseded first attempt,
    which changes only how a missing view is labelled."""
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
        # WHO held the seat for this turn (``TurnRecord.occupant``), and a human occupant's private note. ``None``
        # on every batch-run episode, where the seat's occupant never changes and ``kind`` already says what it
        # was; carried per turn because live play can hand a seat to a different player mid-episode, so only the
        # turn knows. The transcript badges a turn whose occupant is not the seat's default.
        "occupant": t.get("occupant"),
        "human_note": t.get("human_note"),
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
        # WHICH of the two sources above the text came from, which `reasoning_provenance` cannot say: an
        # ``elicited`` rationale is prose the scaffold ASKED the seat to write in its response body, and is a
        # different kind of evidence from a ``provider`` reasoning stream the model produced before answering.
        # A page that labelled a scaffold-elicited rationale as a chain of thought would overclaim.
        "reasoning_source": ("elicited" if parsed.get("thinking")
                             else ("provider" if t.get("reasoning") else "none")),
        "n_tokens_out": t.get("n_tokens_out"), "n_tokens_in": t.get("n_tokens_in"),
        "cap": t.get("cap"), "stop_reason": t.get("stop_reason"),
        "view": view, "view_source": source,
        "oracles": turn_oracles,
        "gen_failed": idx in fabricated,
        "gen_failure": (fabricated.get(idx) or {}).get("reason"),
        "gen_failed_detected_by": (fabricated.get(idx) or {}).get("detected_by"),
        # A turn whose VISIBLE text is the engine's placeholder, whatever produced it. Strictly wider than
        # ``gen_failed``: generation can succeed and still yield nothing publishable, which is what a
        # thinking model does when it spends its whole cap inside an unterminated ``<think>``. Marked on the
        # turn so the transcript can style it as the non-event it is instead of a party choosing to pass.
        "silent": (t.get("content") or "") == EMPTY_TURN_PLACEHOLDER,
    }
    if row["silent"] and t.get("raw"):
        # The text the model DID generate before the placeholder replaced it — normally an unterminated
        # scratchpad, and the only evidence of what the turn was trying to do. Carried for silent turns only:
        # it runs to several kilobytes and on a healthy local turn it merely repeats ``content``.
        #
        # And capped. A turn that burned a raised 32k cap inside one ``<think>`` block can carry a hundred
        # kilobytes, and a page with a dozen of those is a page nobody opens twice. The HEAD is what a reader
        # wants (what the seat set out to do), and the full text is in the episode record the page links to,
        # so ``raw_chars`` keeps the true length honest rather than letting the excerpt pass for the whole.
        raw = str(t["raw"])
        row["raw"] = raw[:RAW_EXCERPT_CHARS]
        row["raw_chars"] = len(raw)
        row["raw_truncated"] = len(raw) > RAW_EXCERPT_CHARS
    if deal_index is not None and geo is not None:
        row["deal"] = geo.at(deal_index).to_json()
        row["deal_welfare"] = geo.welfare_of(deal_index)
    return row


# -------------------------------------------------------------------------------- the payload --
def episode_payload(episode: dict, instance: dict | None = None, annotation: dict | None = None, *,
                    manifest: dict | None = None, geometry: GameGeometry | None = None,
                    reconstruct: bool = True, paths: dict | None = None,
                    annotations_source: str | None = None, vintage: dict | None = None,
                    derivation: dict | None = None) -> dict:
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
    annotations_source : str, optional
        The name of the per-run annotation subdirectory the ``annotation`` record was read from (e.g.
        ``"annotations"`` or ``"annotations_v1"``). Carried through to the page as provenance so an auditor can
        see WHICH annotation vintage the post-hoc oracle values (above all the ``bestresponse`` counterfactual)
        were read from — the v0 pass versus a re-annotated set such as the oracle seat-binding fix. ``None`` when
        the counterfactual oracles came only from the episode's own inline records, not an annotation store.
    vintage : dict, optional
        The run's parsed ``VINTAGE_PROVENANCE.md`` hazard record (see
        :func:`~interlens.arena.viz.hazards.vintage_provenance`), which marks a run whose agents carry a known
        defect. Passed in rather than read here because it is a property of the run directory and one run's file
        serves all of its episodes. ``None`` means no hazard file, which is the healthy case.
    derivation : dict, optional
        The run's optional ``vote_derivation.json`` sidecar (see
        :func:`~interlens.arena.viz.ballots.vote_derivation`), which lets the final-vote tally show what each
        computable seat's own policy re-derives beside what the record holds. ``None`` renders the recorded
        ballots alone.
    """
    geo = geometry if geometry is not None else GameGeometry.from_instance(instance or {})
    kinds = seat_kinds(episode, manifest)
    oracles = _oracle_records(episode, annotation)
    turns = episode.get("turns") or []
    stored_views = sum(1 for t in turns if t.get("view"))
    rebuilt = reconstruct_views(episode, instance) if (reconstruct and not stored_views and instance) else {}

    # Turns whose text NO MODEL PRODUCED — the engine fabricated them after generation failed. Read through
    # ``arena.engine.gen_failures`` rather than re-derived here, so the page and every audit share one detector
    # (it reads the v1.2 ``gen_failed`` stamp and falls back to the legacy value signature on older episodes).
    # Surfacing these is not cosmetic: the placeholder parses into a well-formed no-op, so an episode that is
    # entirely fabricated otherwise renders as a clean transcript of a party that chose to say nothing.
    fabricated = {row["idx"]: row for row in gen_failures(episode)}

    seat_party = {s.get("name"): i for i, s in enumerate(episode.get("seats") or [])}
    rows, trajectory, slots_seen = [], [], set()
    for t in turns:
        slot = (t.get("round"), t.get("phase"), t.get("seat"))
        is_retry = slot in slots_seen
        slots_seen.add(slot)
        idx = int(t.get("idx", len(rows)))
        row = _turn_payload(t, idx, is_retry=is_retry, geo=geo, kinds=kinds, oracles=oracles,
                            seat_party=seat_party, rebuilt=rebuilt, fabricated=fabricated)
        if row["action"]["deal_index"] is not None and geo is not None:
            trajectory.append({"turn_idx": idx, "ordinal": len(trajectory) + 1, "seat": t.get("seat"),
                               "kind": row["kind"], "index": row["action"]["deal_index"],
                               "atype": row["action"]["atype"]})
        rows.append(row)

    ledger = public_ledger(rows)
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
        # The turn a reader lands on when they click the AGREED square (see closing_turn_index).
        outcome["closing_turn_idx"] = closing_turn_index(rows, agreed)

    oracle_names = sorted({name for per_turn in oracles.values() for name in per_turn})
    counterfactual_names = [name for name in COUNTERFACTUAL_ORACLES if name in oracle_names]
    payload = {
        "kind": "episode",
        "episode": {k: episode.get(k) for k in
                    ("episode_id", "scenario", "arm", "model", "level", "instance_id", "seed", "cell", "cell_cfg",
                     "status", "rounds_used", "tokens_in", "tokens_out", "cost_usd", "gen_config", "error",
                     "schema_version", "difficulty", "tags", "score_differential")},
        "seats": [{"name": s.get("name"), "role": s.get("role"), "variant": s.get("variant"),
                   "party": i, "kind": kinds["kinds"].get(s.get("name"), "llm")}
                  for i, s in enumerate(episode.get("seats") or [])],
        "seat_kind_source": {"source": kinds["source"], "detail": kinds["detail"]},
        "turns": rows,
        "trajectory": trajectory,
        # the public offer ledger the conversation and issue views read (see public_ledger)
        "offers": ledger["offers"],
        "outcome": outcome,
        "oracle_names": oracle_names,
        # Information-feasible rational and omniscient references lead; the legacy best-response comparator
        # follows. This ordering drives the detailed-selector default but never drops generic scored oracles.
        "counterfactual_oracles": counterfactual_names,
        "annotation_summary": (annotation or {}).get("summary"),
        "annotations_source": annotations_source,
        "views": {"stored": stored_views, "reconstructed": len(rebuilt), "n_turns": len(turns),
                  "reconstructed_pre_retry": sum(1 for r in rows if r["view_source"] == RETRY_SOURCE)},
        # How much of this episode is not model behaviour at all. ``fraction`` of 0.0 is the only healthy value.
        "generation": {"n_turns": len(turns), "fabricated": len(fabricated),
                       "fraction": round(len(fabricated) / len(turns), 4) if turns else 0.0,
                       "detected_by": sorted({r["detected_by"] for r in fabricated.values()}) or None},
        # How much of this episode carried a move at all — the questions the fabrication screen does not ask.
        "census": turn_census(rows),
        "game": geo.to_json() if geo is not None else None,
        "manifest": {k: (manifest or {}).get(k) for k in
                     ("run_name", "invocation", "table", "arms", "policies", "models", "oracles", "scaffold",
                      "info", "provenance", "difficulty", "tags", "score_differential",
                      "api_request_config", "turn_max_tokens")} if manifest else None,
        # The run-level hazards: a known defect in the agents that played it, and the generation budget its
        # seats actually ran at. Both decide whether these numbers may be compared with another run's.
        "vintage": vintage,
        "paths": paths or {},
        # The 2x2 the decision references live on, shipped once so the browser groups them from data and takes
        # every unit string from one owner.
        "reference_axes": references.axes_payload(),
    }
    payload["budget"] = generation_budget(payload)
    payload["ballots"] = final_ballots(payload, derivation)
    return payload


# ------------------------------------------------------------------------------ run-dir loading --
class RunDir:
    """A run directory's three record stores, indexed for lookup: ``episodes/``, ``instances/``, and the annotation
    subdirectory named by ``annotations_dirname`` (``annotations/`` by default), plus ``manifest.json``. Geometry
    is built lazily and CACHED per instance, so a run whose 120 episodes share 6 instances builds 6 utility
    matrices rather than 120."""

    def __init__(self, root: str | Path, *, annotations_dirname: str = "annotations"):
        """``annotations_dirname`` selects which per-run subdirectory the post-hoc oracle annotations are read
        from — mirrors ``analysis.campaign.load_campaign_rows``'s knob. The default ``"annotations"`` is the
        original scoring pass and preserves the previous reads exactly. Point it at a re-annotated set (e.g.
        ``"annotations_v1"``, written by the oracle seat-binding fix) to render the corrected ``bestresponse``
        counterfactual instead of the contaminated v0 one; the chosen name is carried through to every page as
        provenance. A directory that does not exist just yields no annotations (the page then reports the missing
        counterfactual), so an absent re-annotation is graceful rather than fatal."""
        self.root = Path(root)
        self.annotations_dirname = annotations_dirname
        self.episodes_dir = self.root / "episodes" if (self.root / "episodes").is_dir() else self.root
        self.instances, self.instance_paths = _index_records(self.root / "instances", "instance_id",
                                                            require="payload")
        self.annotations, self.annotation_paths = _index_records(self.root / annotations_dirname, "episode_id")
        manifest = self.root / "manifest.json"
        self.manifest = json.loads(manifest.read_text()) if manifest.is_file() else None
        # Two optional run-level sidecars, read once here because every episode of the run shares them: the
        # vintage hazard file that says this run must not be pooled with a repaired one, and the gate's
        # re-derivation of each computable seat's ballot. Both are ``None`` when absent.
        self.vintage = vintage_provenance(self.root)
        self.derivation = vote_derivation(self.root)
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
        if self.vintage:
            paths["vintage"] = self.vintage["path"]
        if self.derivation is not None:
            paths["vote_derivation"] = str((self.root / DERIVATION_SIDECAR).resolve())
        return episode_payload(episode, instance, annotation, manifest=self.manifest,
                               geometry=self.geometry(instance_id), reconstruct=reconstruct, paths=paths,
                               annotations_source=(self.annotations_dirname if annotation is not None else None),
                               vintage=self.vintage, derivation=self.derivation)


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

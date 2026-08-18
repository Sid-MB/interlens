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

# [implement f: fixing rational] 2026-08-18
"""The **talking rational agent**: the composed Bayesian negotiator with a truthful templated voice.

``BayesianRationalPolicy`` is mute — its beliefs are signal-starved under private information because the only
evidence it ever emits or consumes is offer movement. This module gives the SAME decision rule a message
channel, in a ladder of strictly increasing revelation, plus the inbound half (parsing counterparties'
statements into belief-grid conditioning). The decision rule is UNCHANGED by construction: the speaking
variants only add messages, and the listening variant changes only the belief posterior the existing rule is
applied to.

The ladder (``TalkingBayesianPolicy.VARIANTS``):

- ``commit`` (T1) — once, on its first turn: its concession schedule ("I accept any package worth at least
  ``bar(r)`` to me; the bar falls to my floor by the deadline"), computed from the live optimal-stopping
  reservation curve under current beliefs.
- ``narrate`` (T2) — each turn with a standing offer: whether that offer clears its CURRENT reservation bar and
  by how much, in its own points and on its own min-max-normalized 0-1 scale.
- ``hint`` (T3) — narrate + once, on its first turn: its ordinal top option on each issue (tops only — no
  scores, no threshold).
- ``listen`` (T4) — commit + narrate + hint + parse other seats' ``talking_rational`` statements (verbatim from
  other talking seats; from LLM text via a strict JSON convention it requests in its first-turn message) into
  soft, trust-discounted belief-grid conditioning.

``BabbleBayesianPolicy`` is the control: fluent, on-topic, length-matched, state-INDEPENDENT boilerplate every
turn over the same mute decision rule — it separates "any speech helps" from "informative speech helps".

Honesty is a hard constraint, enforced by construction and gated offline: every emitted statement is a pure
function of the policy's live state (reservation curve, standing offer, own sheet), rendered by the same
functions an offline gate re-runs on the recorded view (see the rational_agents experiment's
``gate_talking_messages.py``). There is no bluffing arm here.

Message grammar: prose for the LLM audience plus one fenced ```json`` block per statement carrying
``{"talking_rational": {payload}}``. The scenario republishes a seat's ``message`` as plain text, so the block
is legible (and machine-parseable) in every other seat's view. :func:`statements_in` is the total parser —
anything malformed is dropped and counted, never raised.
"""
from __future__ import annotations

import json
import re

import numpy as np

from .acceptance import AcceptanceOracle
from .beliefs import BeliefState
from .bestresponse import passage_probability
from .oracle_context import issue_sizes
from .policy_participant import PolicyParticipant
from .strategies import BayesianRationalPolicy, NegotiationState, fit_belief

#: The fenced-JSON key every talking-rational statement is published under. One key for the whole grammar so a
#: transcript census (and the LLM convention request) has a single unmistakable marker.
MESSAGE_KEY = "talking_rational"

#: The statement kinds the grammar defines. ``commit``/``hint`` are first-turn statements, ``narrate`` recurs.
STATEMENT_KINDS = ("commit", "narrate", "hint")


# --------------------------------------------------------------------------------------------------------- #
# The total parser: text -> statement payloads. Shared by the listening seat and the offline gates.
# --------------------------------------------------------------------------------------------------------- #
def _balanced_objects(text: str) -> list[str]:
    """Brace-balanced ``{...}`` substrings that mention :data:`MESSAGE_KEY` — finds the statement objects
    whether they sit inside a ```` ```json ```` fence or bare in prose. Brace counting is blind to braces
    inside string literals, but the grammar's own strings carry none and a broken candidate simply fails
    ``json.loads`` and is dropped, so the scanner stays total."""
    out = []
    for m in re.finditer(re.escape(f'"{MESSAGE_KEY}"'), text or ""):
        start = (text or "").rfind("{", 0, m.start())
        if start < 0:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[start:i + 1])
                    break
    return out


def _resolve_seat(block: dict, personas) -> int | None:
    """The speaker's seat index: an explicit integer ``seat``, or a ``name`` resolved against ``personas``
    (the convention LLM seats are asked to use, since a model knows its name but not its index)."""
    if isinstance(block.get("seat"), int) or (isinstance(block.get("seat"), str)
                                              and str(block["seat"]).isdigit()):
        return int(block["seat"])
    name = str(block.get("name", "")).strip().lower()
    for i, persona in enumerate(personas or ()):
        if name == str(persona).strip().lower():
            return i
    return None


def _resolve_deal(block: dict, space) -> tuple | None:
    """A statement's referenced package as option indices: an index list, or a named ``{issue: option}`` object
    decoded through ``space.parse`` (the one tolerant name decoder). ``None`` when absent/undecodable."""
    deal = block.get("deal")
    if isinstance(deal, (list, tuple)):
        try:
            return tuple(int(x) for x in deal)
        except (TypeError, ValueError):
            return None
    if isinstance(deal, dict) and space is not None:
        try:
            return space.parse(deal)
        except (ValueError, AttributeError):
            return None
    return None


def _resolve_tops(block: dict, space) -> dict[int, int] | None:
    """A hint's declared per-issue top options as ``{issue_index: option_index}``. Accepts integer indices or
    issue/option NAMES (matched case/whitespace-insensitively against ``space``). Any unknown issue or option
    drops the WHOLE hint — a half-decoded preference claim is worse than none."""
    tops = block.get("tops")
    if not isinstance(tops, dict) or space is None:
        return None
    by_name = {i.name.strip().lower(): (j, {o.strip().lower(): k for k, o in enumerate(i.options)})
               for j, i in enumerate(space.issues)}
    out: dict[int, int] = {}
    for issue, option in tops.items():
        key = str(issue).strip().lower()
        if key.isdigit() and int(key) < len(space.issues):
            j = int(key)
            opts = {o.strip().lower(): k for k, o in enumerate(space.issues[j].options)}
        elif key in by_name:
            j, opts = by_name[key]
        else:
            return None
        opt_key = str(option).strip().lower()
        if opt_key.isdigit() and int(opt_key) < len(space.issues[j].options):
            out[j] = int(opt_key)
        elif opt_key in opts:
            out[j] = opts[opt_key]
        else:
            return None
    return out or None


def statements_in(text: str, *, space=None, personas=()) -> tuple[list[dict], int, int]:
    """Every well-formed talking-rational statement in ``text``, plus the census the honesty audit needs.

    Returns ``(statements, n_candidates, n_dropped)``. Each statement is a normalized dict with ``kind``
    (:data:`STATEMENT_KINDS`), ``seat`` (int), and kind-specific fields — ``narrate``: ``above`` (bool) plus
    optionally ``deal`` (index tuple) and ``offer_id``; ``hint``: ``tops`` ``{issue_index: option_index}``;
    ``commit``: ``floor_norm`` (float in [0, 1]) if the block carried one. The parser is TOTAL: an unparseable
    or schema-violating candidate is dropped and counted in ``n_dropped``, never raised, because a listening
    seat must survive arbitrary LLM text.
    """
    statements: list[dict] = []
    candidates = _balanced_objects(text or "")
    dropped = 0
    for raw in candidates:
        try:
            block = json.loads(raw).get(MESSAGE_KEY)
        except (ValueError, AttributeError):
            dropped += 1
            continue
        if not isinstance(block, dict):
            dropped += 1
            continue
        kind = block.get("kind")
        seat = _resolve_seat(block, personas)
        if kind not in STATEMENT_KINDS or seat is None:
            dropped += 1
            continue
        stmt: dict = {"kind": kind, "seat": seat}
        if kind == "narrate":
            if not isinstance(block.get("above"), bool):
                dropped += 1
                continue
            stmt["above"] = block["above"]
            deal = _resolve_deal(block, space)
            if deal is not None:
                stmt["deal"] = deal
            if isinstance(block.get("offer_id"), str):
                stmt["offer_id"] = block["offer_id"]
        elif kind == "hint":
            tops = _resolve_tops(block, space)
            if tops is None:
                dropped += 1
                continue
            stmt["tops"] = tops
        elif kind == "commit":
            floor = block.get("floor_norm")
            if isinstance(floor, (int, float)) and 0.0 <= float(floor) <= 1.0:
                stmt["floor_norm"] = float(floor)
            else:
                dropped += 1
                continue
        statements.append(stmt)
    return statements, len(candidates), dropped


# --------------------------------------------------------------------------------------------------------- #
# Trust-discounted belief conditioning. Module functions over BeliefState: each folds ONE public claim into
# one opponent's posterior, softly, so a false or strategic claim cannot collapse the grid. They write the
# same damped log-posterior ``observe_response`` does and belong on BeliefState eventually; they live here
# for now because beliefs.py is mid-edit by a parallel lane and these are this module's only clients.
# --------------------------------------------------------------------------------------------------------- #
def condition_on_narration(bst: BeliefState, deal, above: bool, *, reliability: float = 0.85,
                           strength: float = 0.6) -> None:
    """Fold "this package is above/below my bar" into the posterior — exactly the accept/reject evidence
    ``observe_response`` implements, with the claim's truth value playing the vote."""
    bst.observe_response(tuple(int(x) for x in deal), bool(above), reliability=float(reliability),
                         strength=float(strength))


def condition_on_hint(bst: BeliefState, tops: dict, *, reliability: float = 0.85,
                      strength: float = 0.6) -> None:
    """Fold declared per-issue top options into the posterior: types whose evaluator peaks at the declared
    option on that issue match the claim (likelihood ``reliability``), the rest ``1 - reliability``, tempered
    by ``strength`` and the state's own damping ``lam``."""
    loglik = np.zeros(len(bst.types))
    for issue, option in tops.items():
        predicted = bst._S[int(issue)].argmax(axis=1) == int(option)
        loglik += np.log(np.where(predicted, float(reliability), 1.0 - float(reliability)))
    bst._logpost = bst._logpost + bst.lam * float(strength) * loglik
    bst._renormalize()


def condition_on_commit(bst: BeliefState, floor_norm: float, *, scale: float = 0.12,
                        strength: float = 0.6) -> None:
    """Fold a declared normalized walk-away floor into the posterior over the grid's reservation levels: a
    Gaussian log-likelihood ``-(tau - floor)^2 / (2 scale^2)`` per type, tempered by ``strength`` and ``lam``.
    The declarer's floor is on its own min-max scale and a grid type's ``tau`` on the type's additive [0, 1]
    scale — close but not identical coordinates, which is one reason this update is soft."""
    loglik = -((bst.type_thresholds() - float(floor_norm)) ** 2) / (2.0 * float(scale) ** 2)
    bst._logpost = bst._logpost + bst.lam * float(strength) * loglik
    bst._renormalize()


# --------------------------------------------------------------------------------------------------------- #
# The talking policy.
# --------------------------------------------------------------------------------------------------------- #
class TalkingBayesianPolicy(BayesianRationalPolicy):
    """``BayesianRationalPolicy`` with a truthful templated message channel and (optionally) inbound listening.

    The decision rule is untouched: ``act``/``vote`` are inherited verbatim. Speaking variants add messages
    only; the listening variant overrides ``_accept_prob_table`` to condition the SAME belief grid on parsed
    counterparty statements before the inherited rule reads it. Actions are therefore byte-identical to the
    base policy given the same beliefs — the experiment's gate G1.

    Parameters
    ----------
    commit : bool
        Emit the concession-schedule commitment on the first turn (T1 content): the optimal-stopping
        reservation bar per round under current beliefs, in own points and normalized units, falling to the
        walk-away floor. Labeled as the current plan — the live bar each turn remains authoritative.
    narrate : bool
        Emit, on every turn with a standing offer, whether that offer clears the current bar and by how much
        (T2 content).
    hint : bool
        Emit the per-issue ordinal top options on the first turn (T3 increment). No scores, no threshold.
    listen : bool
        Parse other seats' statements (delivered by :class:`TalkingParticipant` on
        ``state.statements``) into trust-discounted belief conditioning, and request the machine-readable
        convention from LLM seats in the first-turn message (T4 increment).
    narrate_reliability, narrate_strength : float
        Trust discount for inbound narrations (see :func:`condition_on_narration`). ``reliability`` is the
        probability a claim is truthful/myopically consistent; ``strength`` tempers it against self-authored
        evidence.
    hint_reliability, hint_strength : float
        Trust discount for inbound ordinal hints (:func:`condition_on_hint`).
    commit_tau_scale, commit_strength : float
        Softness of the inbound declared-floor conditioning (:func:`condition_on_commit`): ``scale`` is the
        Gaussian width on the [0, 1] threshold scale, ``strength`` the tempering.
    discount, walk_if_hopeless, name
        As in :class:`BayesianRationalPolicy`.
    """

    #: The preregistered variant ladder, name -> constructor flags. ``hint`` and ``listen`` are cumulative in
    #: revelation per the proposal (T3 = narrate + hint; T4 = commit + narrate + hint + inbound).
    VARIANTS = {
        "commit": dict(commit=True),
        "narrate": dict(narrate=True),
        "hint": dict(narrate=True, hint=True),
        "listen": dict(commit=True, narrate=True, hint=True, listen=True),
    }

    def __init__(self, *, commit: bool = False, narrate: bool = False, hint: bool = False,
                 listen: bool = False, narrate_reliability: float = 0.85, narrate_strength: float = 0.6,
                 hint_reliability: float = 0.85, hint_strength: float = 0.6,
                 commit_tau_scale: float = 0.12, commit_strength: float = 0.6,
                 discount: float | None = None, walk_if_hopeless: bool = True,
                 name: str = "talking-bayes-rational", **kwargs):
        super().__init__(discount=discount, walk_if_hopeless=walk_if_hopeless, name=name, **kwargs)
        self.commit = bool(commit)
        self.narrate = bool(narrate)
        self.hint = bool(hint)
        self.listen = bool(listen)
        self.narrate_reliability = float(narrate_reliability)
        self.narrate_strength = float(narrate_strength)
        self.hint_reliability = float(hint_reliability)
        self.hint_strength = float(hint_strength)
        self.commit_tau_scale = float(commit_tau_scale)
        self.commit_strength = float(commit_strength)

    # -- state readouts the messages are derived from (each a pure function of ``state``) ------------------
    def _norm(self, state, points: float) -> float:
        """A sheet-point value on this seat's min-max 0-1 scale (the scale ``u_norm`` uses)."""
        _deals, u, _ = self._own.get(state)
        span = float(u.max() - u.min())
        return float((points - float(u.min())) / span) if span > 1e-12 else 0.0

    def reservation_schedule(self, state: NegotiationState) -> list[tuple[int, float]]:
        """``[(round, bar_points), ...]`` for every round 1..deadline+1: the own-sheet score a package must
        reach for this seat to stop, under CURRENT beliefs — the same acceptance-oracle reservation ``act``
        prices the standing offer against, plus the walk-away floor at the forced final (where the terminal
        vote accepts anything individually rational)."""
        disc = self.discount if self.discount is not None else float(state.discount)
        tables = self._tables(state)
        ap = self._accept_prob_table(state, tables)
        pass_vec = passage_probability(ap, state.seat, min_accept=state.min_accept,
                                       veto_seats=state.veto_seats)
        acceptor = AcceptanceOracle(state.seat, discount=disc, accept_prob_vec=pass_vec)
        curve = acceptor.reservation_curve(tables, max(int(state.deadline), 1))
        thr = float(getattr(state.sheet, "threshold", 0.0))
        schedule = []
        for r in range(1, int(state.deadline) + 2):
            r_left = max(int(state.deadline) - r + 1, 0)
            schedule.append((r, thr + float(curve[min(r_left, len(curve) - 1)])))
        return schedule

    def current_bar(self, state: NegotiationState) -> float:
        """This turn's acceptance bar in own sheet points: the walk-away floor on a terminal vote (no
        continuation exists), else the optimal-stopping reservation at the rounds actually left — the exact
        ``r_left`` clamp ``act`` uses."""
        thr = float(getattr(state.sheet, "threshold", 0.0))
        if state.must_vote:
            return thr
        schedule = dict(self.reservation_schedule(state))
        r = min(max(int(state.round), 1), int(state.deadline) + 1)
        return schedule[r]

    def issue_tops(self, state: NegotiationState) -> dict:
        """``{issue_name: option_name}`` — this seat's true ordinal top per issue, ties broken by first index
        (deterministic). Read straight off the sheet's per-issue value rows."""
        return {issue.name: issue.options[int(np.argmax([float(v) for v in row]))]
                for issue, row in zip(state.space.issues, state.sheet.values)}

    # -- message rendering (prose + fenced payload; deterministic, gate-re-derivable) -----------------------
    @staticmethod
    def _fenced(payload: dict) -> str:
        return "```json\n" + json.dumps({MESSAGE_KEY: payload}, sort_keys=True) + "\n```"

    def commit_message(self, state: NegotiationState) -> str:
        """The first-turn concession-schedule commitment (T1)."""
        schedule = self.reservation_schedule(state)
        thr = float(getattr(state.sheet, "threshold", 0.0))
        payload = {"kind": "commit", "seat": int(state.seat), "round": int(state.round),
                   "floor_points": round(thr, 4), "floor_norm": round(self._norm(state, thr), 4),
                   "schedule_points": [[r, round(bar, 4)] for r, bar in schedule],
                   "schedule_norm": [[r, round(self._norm(state, bar), 4)] for r, bar in schedule]}
        steps = "; ".join(f"round {r}: {bar:.1f}" for r, bar in schedule)
        return (f"So everyone can plan around me, here is my acceptance schedule as I currently compute it "
                f"(it may tighten or loosen as I learn, and what I narrate each turn is authoritative): I "
                f"will accept any package worth at least the bar for the round we are in, on my private "
                f"sheet — {steps}. By the final vote my bar is my walk-away floor of {thr:.1f} points: any "
                f"package at or above it beats no deal for me and I will vote yes on it.\n" +
                self._fenced(payload))

    def narrate_message(self, state: NegotiationState) -> str | None:
        """This turn's standing-offer narration (T2), or ``None`` when there is nothing to narrate."""
        deal = state.standing_deal
        if deal is None or state.standing is None:
            return None
        bar = self.current_bar(state)
        value = float(state.sheet.utility(deal))
        margin = value - bar
        payload = {"kind": "narrate", "seat": int(state.seat), "round": int(state.round),
                   "offer_id": str(state.standing), "deal": [int(x) for x in deal],
                   "above": bool(margin >= 0.0), "margin_points": round(margin, 4),
                   "margin_norm": round(margin / max(1e-12, self._span(state)), 4)}
        side = "clears" if margin >= 0.0 else "misses"
        return (f"On my own numbers, the standing offer {state.standing} {side} my current bar by "
                f"{abs(margin):.1f} points ({abs(payload['margin_norm']):.3f} on my 0-1 scale).\n" +
                self._fenced(payload))

    def hint_message(self, state: NegotiationState) -> str:
        """The first-turn ordinal-tops hint (T3 increment)."""
        tops = self.issue_tops(state)
        payload = {"kind": "hint", "seat": int(state.seat), "round": int(state.round), "tops": tops}
        listing = "; ".join(f"on {issue}, I prefer {option}" for issue, option in tops.items())
        return (f"Direction only, no numbers: {listing}. Those are my true first choices per issue; my "
                f"rankings below the top are not stated.\n" + self._fenced(payload))

    def convention_message(self, state: NegotiationState) -> str:
        """The first-turn request (T4 increment) that language-model seats state their own constraints in the
        machine-readable convention this policy can actually consume. Claims are trust-discounted, never
        taken as fact."""
        return (
            "If you want me to factor your constraints into my planning exactly, state them anywhere in your "
            "message in this exact machine-readable form (I treat them as claims, not facts): "
            '```json\n{"' + MESSAGE_KEY + '": {"kind": "narrate", "name": "<your name>", '
            '"offer_id": "<offer id>", "above": true}}\n``` '
            "with \"above\" meaning the named offer clears your own private bar (false if it does not), and "
            'for your per-issue first choices: ```json\n{"' + MESSAGE_KEY + '": {"kind": "hint", '
            '"name": "<your name>", "tops": {"<issue>": "<your best option>"}}}\n```')

    def _span(self, state) -> float:
        _deals, u, _ = self._own.get(state)
        return float(u.max() - u.min())

    def declaration(self, state: NegotiationState) -> str | None:
        """The one-time first-turn message: commitment schedule, ordinal tops, and/or the LLM convention
        request, per this variant's flags. ``PolicyParticipant`` publishes it exactly like LLM chat."""
        parts = []
        if self.commit:
            parts.append(self.commit_message(state))
        if self.hint:
            parts.append(self.hint_message(state))
        if self.listen:
            parts.append(self.convention_message(state))
        return "\n\n".join(parts) or None

    def commentary(self, state: NegotiationState) -> str | None:
        """The every-turn message (narration), or ``None``. :class:`TalkingParticipant` appends it to the
        turn's public message on every turn, first and later alike."""
        return self.narrate_message(state) if self.narrate else None

    # -- listening: condition the belief grid on parsed statements ------------------------------------------
    def conditioned_belief_states(self, state: NegotiationState) -> dict:
        """Per-opponent posteriors after folding in the parsed statements riding on ``state.statements``
        (attached by :class:`TalkingParticipant`), in transcript order, each softly and trust-discounted.
        Offers condition exactly as in the base policy (same ``fit_belief``); statements about a seat's own
        valuation condition that seat's grid."""
        belief = fit_belief(state)
        counts = issue_sizes(state.space, [state.sheet])
        states = dict(belief.states)
        for opp in state.opponents:
            states.setdefault(int(opp), BeliefState(counts))
        for stmt in getattr(state, "statements", ()) or ():
            target = states.get(int(stmt["seat"]))
            if target is None or int(stmt["seat"]) == int(state.seat):
                continue
            if stmt["kind"] == "narrate":
                deal = stmt.get("deal")
                if deal is None and stmt.get("offer_id") is not None:
                    deal = (state.offers or {}).get(stmt["offer_id"])
                if deal is None:
                    continue
                condition_on_narration(target, deal, stmt["above"],
                                       reliability=self.narrate_reliability,
                                       strength=self.narrate_strength)
            elif stmt["kind"] == "hint":
                condition_on_hint(target, stmt["tops"], reliability=self.hint_reliability,
                                  strength=self.hint_strength)
            elif stmt["kind"] == "commit" and "floor_norm" in stmt:
                condition_on_commit(target, stmt["floor_norm"], scale=self.commit_tau_scale,
                                    strength=self.commit_strength)
        return states

    def _accept_prob_table(self, state, tables):
        """The base table under full information or when not listening / nothing was said; otherwise the same
        posterior acceptance table computed from the statement-conditioned belief states. The DECISION RULE
        consuming this table is inherited unchanged — that is gate G1's re-derivable claim."""
        if state.tables is not None or not self.listen or not getattr(state, "statements", ()):
            return super()._accept_prob_table(state, tables)
        ap = np.ones((tables.n_deals, tables.n_agents))
        for opp, bst in self.conditioned_belief_states(state).items():
            if int(opp) != int(state.seat):
                ap[:, int(opp)] = bst.accept_prob_matrix(tables.deals_arr)
        return ap


class BabbleBayesianPolicy(BayesianRationalPolicy):
    """The babble control: the mute decision rule plus fluent, on-topic, state-INDEPENDENT boilerplate every
    turn. Sentences are length-matched to the talking variants' narrations and rotate deterministically by
    round, so the channel is equally busy but carries zero information about this seat's state."""

    #: Deterministic rotation, indexed by ``(round - 1) % len``. Deliberately generic: nothing here is
    #: derivable from (or contradicts) any seat's private state, which is what makes it a control.
    BABBLE = (
        "I think we should all keep looking for common ground here — there is usually a package that works "
        "better for everyone than it first appears.",
        "Let us keep the conversation constructive and focus on the issues where our interests overlap "
        "rather than the ones where they collide.",
        "Progress in talks like these usually comes from small mutual adjustments, so I encourage everyone "
        "to stay flexible round by round.",
        "It is worth remembering that a deal all of us can live with beats a stalemate for every party at "
        "this table.",
        "I appreciate the proposals made so far and think continued good-faith engagement will get us to "
        "an agreement.",
        "Every negotiation has give and take; let us make sure we are all still listening to each other as "
        "the deadline approaches.",
    )

    def __init__(self, *, discount: float | None = None, walk_if_hopeless: bool = True,
                 name: str = "babble-bayes-rational", **kwargs):
        super().__init__(discount=discount, walk_if_hopeless=walk_if_hopeless, name=name, **kwargs)

    def commentary(self, state: NegotiationState) -> str | None:
        """One boilerplate sentence per turn, a pure function of the round number."""
        return self.BABBLE[(max(int(state.round), 1) - 1) % len(self.BABBLE)]


# --------------------------------------------------------------------------------------------------------- #
# The participant: publishes per-turn commentary and delivers parsed inbound statements to the policy.
# --------------------------------------------------------------------------------------------------------- #
class TalkingParticipant(PolicyParticipant):
    """A :class:`PolicyParticipant` for talking policies: it merges the one-time ``declaration`` with the
    bound policy's per-turn ``commentary`` into the turn's public message, and (for listening policies)
    parses every ``talking_rational`` statement in the view into ``state.statements`` before the policy runs.

    Parameters (beyond :class:`PolicyParticipant`)
    ----------
    personas : tuple[str, ...]
        Seat-ordered public names, used to resolve ``name``-keyed statements from LLM seats to seat indices.
        Empty disables name resolution (index-keyed statements still parse).
    """

    def __init__(self, *args, personas: tuple = (), **kwargs):
        super().__init__(*args, **kwargs)
        self.personas = tuple(personas or ())
        #: Census of the last parse: candidates seen / dropped, for the message audit. Overwritten per turn.
        self.last_parse_census: dict = {}

    def _declaration(self, state, view: list[dict]) -> str | None:
        """First-turn declaration (inherited rule) plus this turn's commentary, joined. Both derive purely
        from ``state``/``view``, so a retried turn re-sends the identical message."""
        parts = []
        first = super()._declaration(state, view)
        if first:
            parts.append(first)
        commentary = getattr(self.policy, "commentary", None)
        if commentary is not None:
            line = commentary(state)
            if line:
                parts.append(line)
        return "\n\n".join(parts) or None

    def _state_from_view(self, view: list[dict]) -> NegotiationState:
        """The ordinary reconstruction plus the inbound channel: every parsed statement from OTHER seats, in
        view order, de-duplicated (the public log repeats across view segments), attached as
        ``state.statements``. Statements about this seat's own valuation are excluded — a seat never updates
        on its own speech."""
        state = super()._state_from_view(view)
        statements: list[dict] = []
        seen: set = set()
        n_candidates = n_dropped = 0
        for seg in (view or []):
            found, candidates, dropped = statements_in(seg.get("content", "") or "",
                                                       space=self.space, personas=self.personas)
            n_candidates += candidates
            n_dropped += dropped
            for stmt in found:
                if int(stmt["seat"]) == int(self.seat):
                    continue
                key = json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in stmt.items()},
                                 sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                statements.append(stmt)
        state.statements = tuple(statements)
        self.last_parse_census = {"n_candidates": n_candidates, "n_dropped": n_dropped,
                                  "n_statements": len(statements)}
        return state

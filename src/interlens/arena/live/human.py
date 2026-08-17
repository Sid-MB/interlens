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
# [implement: live-play/lane0] 2026-08-16
# [implement: live-play/laneA] 2026-08-16
"""``HumanParticipant``: a seat played by a person in a browser.

The person is a participant like any other. ``Participant.generate`` is synchronous and the engine already runs
it in ``asyncio.to_thread`` (``arena/engine.py``), so a seat that blocks for two minutes while somebody decides
what to offer blocks a worker thread and nothing else — no async plumbing, no engine change.

The split of responsibility is deliberate and is the thing to preserve:

- the PARTICIPANT parses the state out of its own view, publishes an ``awaiting_human`` event describing what
  may legally be done, and blocks on a queue;
- the SERVER validates the submitted form and assembles the message, because validation needs the deal space and
  the offer registry and belongs on the side that can answer a POST with a 400;
- the message the server enqueues goes through ``arena.actions.action_message`` — the SAME renderer LLM seats'
  output is parsed back out of — so a human turn is byte-identical in form to a model turn. Nothing downstream
  (the scenario parser, the oracles, the visualizer, an exported dataset row) can tell them apart except by the
  ``occupant`` stamp, which is exactly the property that makes a mixed human/model game measurable.

Never enqueue an unvalidated submission: the engine reads empty content as a well-formed no-op turn (it
substitutes ``EMPTY_TURN_PLACEHOLDER``), so a mistyped form would silently become the player passing.

Owned by lane A.
"""
from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from ...message import Message
from ...participant.participant import Participant
from ..actions import Accept, Pass, Propose, Reject, Walk, action_message
from ..negotiation.strategies import NegotiationState, parse_negotiation_state
from . import events

logger = logging.getLogger(__name__)

#: Phase names a human seat can be asked under, derived from the scenario's own ``negotiation_state`` block
#: rather than from ``SeatRequest.phase`` (which the participant never sees). They are spelled exactly as
#: ``ScorableNegotiation`` spells them, because the server's legality rules must agree with the scenario's
#: ``_PHASE_ALLOWED`` table turn for turn — a form that offers a move the scenario will refuse is a bug that
#: only shows up as a wasted turn.
TURN = "turn"
FINAL_PROPOSAL = "final_proposal"
FINAL_VOTE = "final_vote"


class SessionStopped(RuntimeError):
    """Raised inside a blocked :meth:`HumanParticipant.generate` when the session is stopped.

    Deliberately an exception rather than a fabricated pass: a stopped session's episode must end as an error,
    because "the player was still deciding when the server shut down" and "the player chose to do nothing" are
    different facts and only one of them is behaviour."""


class _Stop:
    """The sentinel :meth:`HumanParticipant.unblock` feeds the inbox. Carries the reason so the raised
    :class:`SessionStopped` can say why the seat was released."""

    def __init__(self, reason: str):
        self.reason = reason


@dataclass
class PendingRequest:
    """One open ask of a human seat — what the browser renders a form from, and what the server validates a
    submission against.

    Held by the participant while it blocks and mirrored into the ``awaiting_human`` event. Carrying the parsed
    state (rather than re-parsing the prompt on submit) is what guarantees the form's legality rules and the
    server's validation are computed from the same state the seat was conditioned on.

    Parameters
    ----------
    seat : str
        The seat display name being asked to move.
    seat_idx : int
        Its index into the game's seat-indexed sheets/tables.
    turn_idx : int
        The index the resulting turn will take.
    round : int
        The negotiation round this move belongs to.
    phase : str
        The scenario phase (proposal, voting, ...) — decides which actions are legal.
    state : Any
        The ``NegotiationState`` reconstructed from the seat's view, including the live offer registry.
    view : list[dict]
        The exact view the seat was conditioned on, kept so the dock can show the human the prompt they are
        answering rather than a paraphrase.
    legal : dict
        ``{can_accept: [offer_ids], can_reject: [offer_ids], can_offer: bool, can_walk: bool, can_pass: bool}``
        for this moment — see :func:`legal_actions`.
    block : dict
        The raw ``negotiation_state`` JSON the state was reconstructed from. Kept alongside the typed state
        because ``state`` holds live ``ScoreSheet``/``DealSpace`` objects and the wire needs plain JSON; carrying
        the block the seat actually read (rather than re-serializing the typed state) means the browser and the
        seat are looking at the same bytes.
    """

    seat: str
    seat_idx: int
    turn_idx: int
    round: int
    phase: str
    state: Any = None
    view: list[dict] = field(default_factory=list)
    legal: dict = field(default_factory=dict)
    block: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        """The wire form carried in ``awaiting_human`` (the view is omitted — it is fetched with the snapshot)."""
        return {"seat": self.seat, "seat_idx": int(self.seat_idx), "turn_idx": int(self.turn_idx),
                "round": int(self.round), "phase": self.phase, "state": dict(self.block),
                "legal": dict(self.legal)}


def legal_actions(state: NegotiationState) -> dict:
    """What this seat may legally submit right now, as ``{can_accept, can_reject, can_offer, can_walk,
    can_pass}`` — the form's rules and the server's validation, computed once from one state.

    It mirrors ``ScorableNegotiation._PHASE_ALLOWED`` exactly, because the scenario is the authority and a form
    that offers a disallowed move burns a real turn on a legality error:

    - an ordinary **turn** allows everything: propose, accept/reject any live offer, walk, or stand pat;
    - the forced-final **proposal** turn allows propose / accept / walk but NOT reject (the scenario reads a
      reject here as an economic-legality violation), and not a pass either — this turn tables the last binding
      package or there is nothing to vote on;
    - the forced-final **vote** allows accept / reject of THE offer under vote only (``state.standing``, which
      the scenario pins to its ``final_offer``) or a walk.

    ``can_accept``/``can_reject`` are lists of offer ids in registration order, so the dock renders the ballot in
    the order the offers were tabled.
    """
    live = list(state.offers)
    if state.must_vote:
        under_vote = [state.standing] if state.standing else []
        return {"can_accept": under_vote, "can_reject": under_vote, "can_offer": False,
                "can_walk": True, "can_pass": False}
    if state.final_proposal:
        return {"can_accept": live, "can_reject": [], "can_offer": True,
                "can_walk": True, "can_pass": False}
    return {"can_accept": live, "can_reject": live, "can_offer": True, "can_walk": True, "can_pass": True}


def phase_of(state: NegotiationState) -> str:
    """The scenario phase this state describes: :data:`FINAL_VOTE` on the forced-final ballot,
    :data:`FINAL_PROPOSAL` on the turn that tables it, else an ordinary :data:`TURN`. Read off the same two
    fields the policies read (``must_vote`` and ``round > deadline``) so a human seat and a policy seat agree
    about what turn they are playing."""
    if state.must_vote:
        return FINAL_VOTE
    return FINAL_PROPOSAL if state.final_proposal else TURN


def sheet_json(sheet: Any) -> dict:
    """A seat's private score sheet as the dock renders it: ``{agent, values, threshold}``. Sent to exactly one
    browser — the person playing this seat — which is the whole point of a private sheet."""
    return {"agent": getattr(sheet, "agent", None),
            "values": [list(row) for row in getattr(sheet, "values", ())],
            "threshold": float(getattr(sheet, "threshold", 0.0))}


class HumanParticipant(Participant):
    """A negotiation seat whose moves come from a browser.

    Parameters
    ----------
    name : str
        Identifier within the conversation, and the ``human:<name>`` occupant label's detail.
    seat : int
        This seat's index into the game's seat-indexed sheets/tables.
    sheet : object
        This seat's PRIVATE score sheet (``.utility``/``.surplus``/``.threshold``) — shown in the player's dock,
        and shown to nobody else. A human plays under the same information a model seat has.
    space : DealSpace
        The shared deal space: the issue/option name table the offer builder is generated from, and the decoder
        (``DealSpace.parse``) a submitted deal is validated with.
    deadline : int
        Total rounds ``T``, so the dock can say which round of how many is being played.
    publisher : callable
        ``publisher(event_type, data) -> None`` — how the participant announces that it is waiting. Injected
        rather than reaching for the session, so the participant is testable with a list.append.
    """

    self_role = "assistant"
    others_role = "user"

    def __init__(self, name: str, seat: int, sheet: Any, space: Any, deadline: int,
                 publisher: Callable[[str, dict], None]):
        self.name = name
        self.seat = int(seat)
        self.sheet = sheet
        self.space = space
        self.deadline = int(deadline)
        self.publisher = publisher
        self.system_prompt = None
        self.private_context = ()
        # The handoff between the engine's worker thread (blocked in ``generate``) and the HTTP thread (calling
        # ``submit``). A plain queue.Queue, not an asyncio primitive: the two sides are OS threads, and the
        # engine's ``asyncio.to_thread`` wrapper means the event loop is never the thing waiting.
        self._inbox: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._pending: PendingRequest | None = None

    # ---------------------------------------------------------------------------------------------------- #
    @property
    def occupant(self) -> str:
        """This seat's occupant label, ``human:<name>`` — stamped on every message the person plays so the
        transcript records WHO took the turn, not just which seat it was."""
        return f"human:{self.name}"

    def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
                 return_logprobs: bool = False, turn: int | None = None,
                 max_new_tokens: int | None = None, seat: str | None = None) -> Message:
        """Ask the person for this turn and block until they answer.

        Parses the ``negotiation_state`` block out of ``view``, builds a :class:`PendingRequest`, publishes
        ``awaiting_human``, then blocks on the inbox with NO timeout — a human thinking is not an error, and a
        deadline that fired mid-decision would fabricate a turn nobody played. Returns the ``Message`` the server
        assembled, whose metadata carries ``action``, ``occupant`` (``human:<name>``) and ``human_note``.

        Raises on any interp request, exactly as ``PolicyParticipant`` does: there is no model here to steer,
        capture, patch or read logprobs from, and silently ignoring the request would corrupt an experiment.

        ``turn_idx`` on the published request is :data:`events.UNKNOWN_TURN_IDX`: the participant does not know
        the episode's turn count
        (the engine passes ``turn`` only alongside a capture request), and the SESSION does — it stamps the real
        index on the event before broadcasting, the same way it supplies ``turn_idx`` for ``turn_started``,
        which the router cannot know either.
        """
        if steering is not None or capture is not None or patch is not None or return_logprobs:
            # Not a live-play stub: the permanent contract every model-less participant holds
            # (``PolicyParticipant``/``ScriptedParticipant`` refuse identically). A capture or a steer that was
            # silently dropped would corrupt an experiment far more quietly than one that failed.
            raise NotImplementedError(
                f"HumanParticipant {self.name!r} has no model: steering/capture/patch/logprobs are unavailable")
        request = self._ask(view, seat)
        with self._lock:
            self._pending = request
        try:
            self.publish(request)
            answer = self._inbox.get()          # no timeout: a person thinking is not a failure mode
        finally:
            with self._lock:
                self._pending = None
        if isinstance(answer, _Stop):
            raise SessionStopped(f"seat {request.seat!r} released without a move: {answer.reason}")
        return answer

    def _ask(self, view: list[dict], seat: str | None) -> PendingRequest:
        """Build the :class:`PendingRequest` for this turn out of the seat's own view.

        The ``negotiation_state`` block is required, not best-effort. Without it there is no offer registry, so
        the form could not tell the player which offers they may accept and the server could not check an accept
        against a live id — every accept would be guesswork. Raising here names the actual misconfiguration (a
        scenario run with ``state_block`` disabled) instead of producing a dock that silently cannot vote."""
        block = None
        for segment in reversed(view or []):
            block = parse_negotiation_state(segment.get("content", ""))
            if block is not None:
                break
        if block is None:
            raise ValueError(
                f"seat {seat or self.name!r} was asked to move but its view carries no negotiation_state block; "
                "a human seat needs the scenario's authoritative offer registry to be told what it may accept "
                "(run the scenario with state_block enabled)")
        block.setdefault("seat", self.seat)
        block.setdefault("deadline", self.deadline)
        state = NegotiationState.from_block(block, sheet=self.sheet, space=self.space, seat=self.seat)
        return PendingRequest(seat=seat or self.name, seat_idx=state.seat,
                              turn_idx=events.UNKNOWN_TURN_IDX, round=state.round,
                              phase=phase_of(state), state=state, view=[dict(s) for s in (view or [])],
                              legal=legal_actions(state), block=block)

    def publish(self, request: PendingRequest) -> None:
        """Announce that this seat is waiting, through the injected publisher.

        A publisher that raises must not take the game down with it — the person can still be asked in another
        browser tab, and a broadcast failure is a UI problem, not a negotiation one — so the exception is logged
        and swallowed, matching how the engine treats its wave observer."""
        kind, data = events.awaiting_human(
            seat=request.seat, seat_idx=request.seat_idx, turn_idx=request.turn_idx, round_=request.round,
            phase=request.phase, state=request.block, sheet=sheet_json(self.sheet), legal=request.legal,
            deadline=self.deadline)
        try:
            self.publisher(kind, data)
        except Exception:
            logger.exception("live-play: awaiting_human publisher raised for seat %s", request.seat)

    def submit(self, message: Message) -> None:
        """Hand the server-assembled message to the blocked :meth:`generate`. Called from the HTTP thread.

        Refuses when the seat is not waiting: a message queued against a closed prompt would sit in the inbox
        and play itself on some LATER turn, under a state the player never saw."""
        with self._lock:
            if self._pending is None:
                raise ValueError(f"seat {self.name!r} is not waiting for input")
        self._inbox.put(message)

    def unblock(self, reason: str = "stopped") -> None:
        """Release a blocked :meth:`generate` without a move — the stop path. Feeds a sentinel that makes
        ``generate`` raise, so a stopped session's episode ends as an error rather than as a fabricated pass."""
        self._inbox.put(_Stop(reason))

    @property
    def pending(self) -> PendingRequest | None:
        """The open ask, or ``None`` when this seat is not waiting. Read by the server to decide whether a
        submission is expected at all, and to refuse a swap while a prompt is open."""
        with self._lock:
            return self._pending


def build_human_message(form: dict, *, name: str, space: Any, pending: PendingRequest) -> Message:
    """Turn a validated browser form into the message a human seat plays — the assembly half of the split above.

    ``form`` is the POST body (``{action, deal, offer_id, message, note}``); ``space`` decodes a named deal;
    ``pending`` supplies the legality rules the submission is checked against. Builds the typed ``Action``,
    renders it with ``arena.actions.action_message`` so the envelope matches an LLM seat's exactly, and stamps
    ``occupant``/``human_note`` metadata for the turn record.

    Raises ``ValueError`` with a player-readable message for anything illegal — an unknown option name, an accept
    referencing a dead offer, an action the phase does not allow, an empty submission. The caller answers that
    with a 400 and an ``input_rejected`` event; nothing is enqueued.
    """
    kind = str(form.get("action") or "").strip().lower()
    if not kind:
        raise ValueError("Choose an action before submitting (propose, accept, reject, walk or pass).")
    legal = pending.legal or {}
    public = (form.get("message") or "").strip() or None
    note = (form.get("note") or "").strip() or None

    if kind == Propose.kind:
        if not legal.get("can_offer"):
            raise ValueError(f"You cannot table a new package on a {pending.phase.replace('_', ' ')} turn.")
        action: Any = Propose(deal=_decode_deal(form.get("deal"), space))
    elif kind in (Accept.kind, Reject.kind):
        allowed = legal.get("can_accept" if kind == Accept.kind else "can_reject") or []
        offer_id = str(form.get("offer_id") or form.get("id") or form.get("offer") or "").strip()
        if not offer_id:
            raise ValueError(f"Say which offer you want to {kind} (e.g. \"P1\").")
        if offer_id not in allowed:
            raise ValueError(f'Offer "{offer_id}" is not one you can {kind} right now'
                             + (f" (you may {kind}: {', '.join(allowed)})." if allowed
                                else f"; there is no offer you can {kind} on this turn."))
        action = Accept(offer_id=offer_id) if kind == Accept.kind else Reject(offer_id=offer_id)
    elif kind == Walk.kind:
        if not legal.get("can_walk"):
            raise ValueError("Walking away is not available on this turn.")
        action = Walk()
    elif kind in (Pass.kind, "pass", "talk"):
        # "talk" is the dock's name for a turn that speaks without moving. It is the SAME wire form as a pass
        # ({"action": "none"} plus a message) — the scenario has no third category — so it must not become a
        # separate action kind here, or a talk-only turn would parse differently from a policy seat's Pass.
        if not legal.get("can_pass"):
            raise ValueError(f"You must take a formal action on a {pending.phase.replace('_', ' ')} turn.")
        if kind == "talk" and not public:
            raise ValueError("Say something, or choose a formal action.")
        action = Pass()
    else:
        raise ValueError(f'Unknown action "{kind}". Use propose, accept, reject, walk or pass.')

    # The SAME renderer LLM seats' output is parsed back out of, so the envelope is indistinguishable on the
    # wire; ``space`` renders a proposed deal by issue/option NAME, which is what the transcript shows.
    content = action_message(action, space, message=public)
    metadata = {"action": action.to_json(), "occupant": f"human:{name}", "human_note": note}
    if public:
        metadata["message"] = public                 # mirrors PolicyParticipant's metadata exactly
    return Message(author=name, content=content, metadata=metadata)


def _decode_deal(deal_obj: Any, space: Any) -> tuple:
    """Decode a submitted deal to an option-index tuple, raising a player-readable ``ValueError`` if it is not a
    complete valid package.

    Two shapes are accepted, matching what the browser can send: the ``{issue_name: option_label}`` object the
    offer builder produces (decoded by ``DealSpace.parse``, whose own error names the offending issue and lists
    its valid labels — far more useful to a player than "invalid deal"), and a bare list of option indices for a
    client that already resolved them."""
    if isinstance(deal_obj, dict):
        if not deal_obj:
            raise ValueError("Set every issue before proposing a package.")
        return space.parse(deal_obj)
    if isinstance(deal_obj, (list, tuple)):
        shape = space.shape
        if len(deal_obj) != len(shape):
            raise ValueError(f"A package must set all {len(shape)} issues; this one sets {len(deal_obj)}.")
        try:
            deal = tuple(int(x) for x in deal_obj)
        except (TypeError, ValueError):
            raise ValueError("Option indices must be whole numbers.") from None
        for j, (option, count) in enumerate(zip(deal, shape)):
            if not 0 <= option < count:
                raise ValueError(f"Issue {space.issues[j].name!r} has no option {option}.")
        return deal
    raise ValueError("Set every issue before proposing a package.")

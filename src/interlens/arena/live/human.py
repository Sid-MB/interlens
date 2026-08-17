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

from dataclasses import dataclass, field
from typing import Any, Callable

from ...message import Message
from ...participant.participant import Participant


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
        ``{can_accept: [offer_ids], can_offer: bool, can_walk: bool, can_pass: bool}`` for this moment.
    """

    seat: str
    seat_idx: int
    turn_idx: int
    round: int
    phase: str
    state: Any = None
    view: list[dict] = field(default_factory=list)
    legal: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        """The wire form carried in ``awaiting_human`` (the view is omitted — it is fetched with the snapshot)."""
        raise NotImplementedError("live-play lane A")


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
        raise NotImplementedError("live-play lane A")

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
        """
        raise NotImplementedError("live-play lane A")

    def submit(self, message: Message) -> None:
        """Hand the server-assembled message to the blocked :meth:`generate`. Called from the HTTP thread."""
        raise NotImplementedError("live-play lane A")

    def unblock(self, reason: str = "stopped") -> None:
        """Release a blocked :meth:`generate` without a move — the stop path. Feeds a sentinel that makes
        ``generate`` raise, so a stopped session's episode ends as an error rather than as a fabricated pass."""
        raise NotImplementedError("live-play lane A")

    @property
    def pending(self) -> PendingRequest | None:
        """The open ask, or ``None`` when this seat is not waiting. Read by the server to decide whether a
        submission is expected at all, and to refuse a swap while a prompt is open."""
        raise NotImplementedError("live-play lane A")


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
    raise NotImplementedError("live-play lane A")

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
"""The live-play wire protocol: every server-sent event a session can emit, in one place.

This module is the SINGLE SOURCE OF TRUTH for what goes over the wire. The server never builds an event dict by
hand and the browser never reads a literal event name — both go through the constants and builders here — so the
protocol cannot drift between the two halves of a feature written by different people at the same time.

Transport is plain SSE over ``GET /api/session/{sid}/events``. A frame is::

    id: <seq>
    event: <type>
    data: <one-line JSON>

    (blank line)

``seq`` is a monotonic per-session sequence number over ALL events the session emitted, and the session keeps the
emitted frames in a log, so a browser that reconnects sends ``Last-Event-ID: <seq>`` and is replayed everything
after it. That, not a heartbeat, is what makes a reload mid-episode lossless. ``data`` is always ONE line
(``json.dumps`` with no newlines) because a bare newline inside ``data`` would be read as a field break by the
EventSource parser and split one event into two.

Builders return ``(event_type, data_dict)`` rather than a formatted frame: the session stamps the sequence number
when it appends to its log (that is where the ordering is decided), and :func:`format_sse` does the formatting.
"""
from __future__ import annotations

import json

# --- event types -------------------------------------------------------------------------------------- #
# The stream opens with this: which session the client is attached to and where it is in the sequence, so a page
# that rendered a server-side snapshot can tell whether it missed anything.
HELLO = "hello"
# The lobby configuration — before a game starts, and again whenever it is edited. The lobby page's whole state.
LOBBY_STATE = "lobby_state"
# An episode began. Carries only the id: the client answers by GETting /state for the full payload, so the
# large first render travels over a normal HTTP response instead of one enormous SSE frame.
EPISODE_STARTED = "episode_started"
# A seat is about to be asked for a turn. Emitted by the router BEFORE generation, so the UI can show "Blake is
# thinking" during an API call that may take half a minute. It is a hint, not a record: nothing is on disk yet.
TURN_STARTED = "turn_started"
# A turn is committed AND persisted. This is the record-bearing event, emitted from the engine's post-save
# observer, and it carries the payload turn dict (identical to a full-payload rebuild) plus its chat bubble.
TURN_APPENDED = "turn_appended"
# A human seat is blocked waiting for input: everything the input form needs to render, including the legal
# moves, so the browser never has to decide legality for itself.
AWAITING_HUMAN = "awaiting_human"
# A human submission was refused (illegal move, unparseable deal, empty text). The turn did NOT happen and the
# seat is still blocked; the form stays open with this reason attached.
INPUT_REJECTED = "input_rejected"
# A seat changed hands mid-game.
SEAT_SWAPPED = "seat_swapped"
# Spend so far against the session's cap. Emitted per committed turn so a live game's cost is never a surprise.
USAGE = "usage"
# The episode ended, for any reason (played out, stopped, budget exhausted, error).
EPISODE_DONE = "episode_done"
# Something went wrong. ``fatal`` distinguishes "this action failed" from "this session is over".
ERROR = "error"

# Every type, for validation and for tests that assert the builders cover the protocol.
EVENT_TYPES = (HELLO, LOBBY_STATE, EPISODE_STARTED, TURN_STARTED, TURN_APPENDED, AWAITING_HUMAN, INPUT_REJECTED,
               SEAT_SWAPPED, USAGE, EPISODE_DONE, ERROR)

# How often the server writes a bare SSE comment when nothing is happening. Comments are ignored by EventSource
# but keep the connection (and any proxy in between) from being reaped as idle during a long model call.
KEEPALIVE_SECONDS = 15
KEEPALIVE_FRAME = b": ping\n\n"

# The ``legal`` block of an ``awaiting_human`` event: every key the human dock may render a control from, with
# the value meaning "this move is not available". Frozen here because it is a contract between three lanes — the
# participant computes it, the server validates against it, the browser draws buttons from it — and a key that
# exists in only two of the three is a control that either never appears or 400s when pressed.
#
# ``can_accept`` and ``can_reject`` are LISTS of live offer ids, not booleans, because both moves name the offer
# they act on (``Accept(offer_id)`` / ``Reject(offer_id)``), and the dock renders one button per live offer.
# They are also genuinely independent: ``ScorableNegotiation._PHASE_ALLOWED`` permits accept but NOT reject on
# the forced-final proposal turn, so a dock that derived one from the other would offer a move the scenario
# scores as a legality error and burn a real turn on it.
LEGAL_ACTION_DEFAULTS = {"can_accept": [], "can_reject": [], "can_offer": False, "can_walk": False,
                         "can_pass": False}

# The response headers an SSE endpoint must send. ``X-Accel-Buffering`` is the nginx directive that turns off
# response buffering — without it a proxy happily holds the stream until it has a bufferful, which for an event
# stream means the page shows nothing for a minute and then everything at once.
SSE_HEADERS = (
    ("Content-Type", "text/event-stream; charset=utf-8"),
    ("Cache-Control", "no-cache, no-store"),
    ("Connection", "keep-alive"),
    ("X-Accel-Buffering", "no"),
)


def format_sse(seq: int, event: str, data: dict) -> bytes:
    """Format one event as an SSE frame, ready to write to the socket.

    ``seq`` becomes the frame's ``id:`` (the value a reconnecting client echoes in ``Last-Event-ID``), ``event``
    its type — one of the constants above — and ``data`` its JSON body, dumped with ``ensure_ascii=False``
    because the transcript is UTF-8 prose that would otherwise triple in size as escapes. The body is one line by
    construction: ``json.dumps`` escapes every newline inside a string, and a literal newline in ``data`` would
    be read as a field break and split one event into two. ``default=str`` keeps a stray non-JSON value (a Path
    on a provenance field) from taking the stream down mid-game.

    Returns bytes because this is written straight to a socket, not to a text stream.
    """
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"id: {int(seq)}\nevent: {event}\ndata: {body}\n\n".encode("utf-8")


# --- builders ------------------------------------------------------------------------------------------ #
# Each returns (event_type, data). Keep the argument names identical to the JSON keys: the browser reads these
# names, so a rename here is a protocol change and should look like one.

def hello(sid: str, seq: int, phase: str, occupants: dict) -> tuple[str, dict]:
    """Stream opened. ``sid`` is the session, ``seq`` the last sequence number the session has emitted (0 before
    anything), ``phase`` where the session is (``"lobby"`` | ``"running"`` | ``"awaiting_human"`` | ``"done"``),
    and ``occupants`` the current seat -> occupant-label map so a fresh page can badge seats immediately."""
    return HELLO, {"sid": sid, "seq": int(seq), "phase": phase, "occupants": dict(occupants)}


def lobby_state(bank: str, framing: str, instance_id: str, seats: list[dict],
                budget_usd: float) -> tuple[str, dict]:
    """The lobby's full configuration: the chosen instance bank, framing and instance, the per-seat configs
    (``SeatConfig.to_json()`` dicts, in seat order) and the session's spend cap in dollars."""
    return LOBBY_STATE, {"bank": bank, "framing": framing, "instance_id": instance_id,
                         "seats": list(seats), "budget_usd": float(budget_usd)}


def episode_started(episode_id: str) -> tuple[str, dict]:
    """An episode began. The client fetches ``/api/session/{sid}/state`` for the initial payload rather than
    receiving it here — the first payload carries the whole game geometry and is far too large for one frame."""
    return EPISODE_STARTED, {"episode_id": episode_id}


def turn_started(turn_idx: int, round_: int, phase: str, seat: str, seat_idx: int,
                 occupant: str | None) -> tuple[str, dict]:
    """A seat is being asked to move. ``turn_idx`` is the index the turn WILL take, ``round_``/``phase`` locate
    it in the scenario, and ``occupant`` is who is answering (``None`` when the seat's occupant is unlabelled).
    Trailing underscore on ``round_`` only because ``round`` is a builtin; the JSON key is ``round``."""
    return TURN_STARTED, {"turn_idx": int(turn_idx), "round": int(round_), "phase": phase,
                          "seat": seat, "seat_idx": int(seat_idx), "occupant": occupant}


def turn_appended(turn: dict, bubble_html: str, rounds_used: int,
                  outcome_partial: dict | None = None) -> tuple[str, dict]:
    """A committed, persisted turn. ``turn`` is the payload turn dict — byte-identical to what a full
    ``episode_payload`` rebuild would produce for it, oracle annotations and occupant included — which is what
    lets the client push it straight onto ``PAYLOAD.turns``. ``bubble_html`` is that turn's chat bubble,
    server-rendered by the same function the static page uses. ``outcome_partial`` is the episode's outcome so
    far when the scenario has one (a closed deal mid-episode), else ``None``."""
    return TURN_APPENDED, {"turn": turn, "bubble_html": bubble_html, "rounds_used": int(rounds_used),
                           "outcome_partial": outcome_partial}


def awaiting_human(seat: str, seat_idx: int, turn_idx: int, round_: int, phase: str, state: dict,
                   sheet: dict, legal: dict, deadline: int) -> tuple[str, dict]:
    """A human seat is blocked on input — everything the control dock renders from.

    ``state`` is the machine-readable ``negotiation_state`` block parsed out of the seat's own view (the offer
    registry, the standing offer, the round), so the UI reads the same state the seat was conditioned on rather
    than scraping the prompt. ``sheet`` is that seat's PRIVATE score sheet (``{values, threshold}``) — it is
    private to this seat and to this browser, which is the point of playing it. ``legal`` is the verdict on what
    may be submitted now (:data:`LEGAL_ACTION_DEFAULTS` names the keys): the server validates anyway, but the
    form should not offer a move that will be refused. ``deadline`` is the game's total round count ``T``, for
    the "round r of T" the human is deciding under.

    ``legal`` is NORMALIZED here — every key in :data:`LEGAL_ACTION_DEFAULTS` is present in the emitted event,
    missing ones taking their "not available" default. So the browser can read ``legal.can_reject`` directly
    instead of guarding for undefined, and a capability a caller forgot to compute fails CLOSED (the control is
    not offered) rather than rendering a button that 400s. Extra keys are passed through untouched, so a later
    move type does not need this builder changed to reach the page."""
    return AWAITING_HUMAN, {"seat": seat, "seat_idx": int(seat_idx), "turn_idx": int(turn_idx),
                            "round": int(round_), "phase": phase, "state": state, "sheet": sheet,
                            "legal": {**LEGAL_ACTION_DEFAULTS, **(legal or {})}, "deadline": int(deadline)}


def input_rejected(seat: str, reason: str) -> tuple[str, dict]:
    """A human submission was refused before it reached the engine. ``reason`` is shown verbatim to the player,
    so it must say what was wrong in their terms. Nothing was enqueued: the seat is still waiting."""
    return INPUT_REJECTED, {"seat": seat, "reason": reason}


def seat_swapped(seat: str, seat_idx: int, from_: str | None, to: str, at_turn: int) -> tuple[str, dict]:
    """A seat changed occupant between turns. ``from_``/``to`` are occupant labels (``None`` from-side if the
    outgoing occupant was unlabelled) and ``at_turn`` is the turn index the new occupant starts at. JSON keys
    are ``from``/``to``; the parameter carries an underscore only because ``from`` is a keyword."""
    return SEAT_SWAPPED, {"seat": seat, "seat_idx": int(seat_idx), "from": from_, "to": to,
                          "at_turn": int(at_turn)}


def usage(tokens_in: int, tokens_out: int, cost_usd: float, cap_usd: float | None,
          exhausted: bool) -> tuple[str, dict]:
    """Spend so far against the cap. ``cap_usd`` is ``None`` for a session with no metered seat; ``exhausted``
    means the meter has stopped the run, which the client should read as the episode being over."""
    return USAGE, {"tokens_in": int(tokens_in), "tokens_out": int(tokens_out), "cost_usd": float(cost_usd),
                   "cap_usd": None if cap_usd is None else float(cap_usd), "exhausted": bool(exhausted)}


def episode_done(status: str, outcome: dict, final: dict | None = None) -> tuple[str, dict]:
    """The episode ended. ``status`` is the episode's own (``"done"`` / ``"error"``) or a live-play reason
    (``"stopped"``, ``"budget_stopped"``); ``outcome`` is the scenario's outcome record; ``final`` is an optional
    closing payload slice (scores, the agreed deal) for the summary strip without a second fetch."""
    return EPISODE_DONE, {"status": status, "outcome": dict(outcome or {}), "final": final}


def error(message: str, fatal: bool = False) -> tuple[str, dict]:
    """Something failed. ``fatal=True`` means the session cannot continue and the page should stop waiting for
    turns; ``False`` means one action failed and the game is still live."""
    return ERROR, {"message": message, "fatal": bool(fatal)}

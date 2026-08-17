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
"""``LiveSession``: one live game — the engine thread, the event log, and everything the browser can do to it.

A session owns a running episode and the fanout to however many browsers are watching it. Its threading model is
small on purpose, because a live server with an LLM in it has enough moving parts already:

- ONE engine thread per session runs ``asyncio.run(EpisodePool(...).run_episode(...))`` with ``max_concurrent=1``.
  The negotiation scenario issues exactly one request per wave, so turns are strictly sequential — which is what
  makes a turn-by-turn UI honest rather than a reordering of a concurrent batch.
- HTTP threads (one per request, from ``ThreadingHTTPServer``) mutate the session: submit a human move, swap a
  seat, stop. Every mutation takes ONE ``threading.RLock``.
- Streaming is a plain fanout: :meth:`broadcast` appends the event to a sequence-numbered log and
  ``put_nowait``s it on each subscriber's queue. It never blocks and never waits on a socket, because it is
  called from the engine thread — a slow reader must be able to fall behind or be dropped, never to stall a game.

No asyncio primitives are shared across threads. The engine thread has its own event loop and the only things
crossing the boundary are ``queue.Queue`` handoffs, which are thread-safe by construction. Cross-loop asyncio
objects are the classic way this goes wrong and are simply not used.

The event log is what makes reload lossless: a reconnecting browser replays from ``Last-Event-ID`` and a fresh
one renders :meth:`snapshot` server-side, then subscribes from the snapshot's sequence number.

Owned by lane B.
"""
from __future__ import annotations

from typing import Any

from .provider import PreparedGame, ScenarioProvider, SeatConfig

# Session phases, in the order a session moves through them. ``awaiting_human`` is a sub-state of ``running``
# reported separately because it is the one phase where the UI must show a form instead of a spinner.
PHASES = ("lobby", "starting", "running", "awaiting_human", "done")


class LiveSession:
    """One live episode plus its subscribers.

    Parameters
    ----------
    sid : str
        Session id, used in every route and echoed in ``hello``.
    provider : ScenarioProvider
        Where games and model seats come from.
    game : PreparedGame
        The assembled game this session plays (from ``provider.prepare``).
    seats : list[SeatConfig]
        Who plays each seat at the start, in seat order.
    run_dir : str | Path
        Where the episode JSON is written. The live page links to it, and it is the durable artifact: the stream
        is a view of the file, never a replacement for it.
    budget_usd : float | None
        Hard spend cap for this session, enforced by a ``UsageMeter``. Required whenever any seat is a metered
        model — a live game with a human in it can idle for a long time with an API seat configured, and an
        uncapped session is how a lobby click turns into a bill.
    """

    def __init__(self, sid: str, provider: ScenarioProvider, game: PreparedGame, seats: list[SeatConfig],
                 run_dir: Any, budget_usd: float | None = None):
        raise NotImplementedError("live-play lane B")

    # --- lifecycle ------------------------------------------------------------------------------------- #
    def start(self) -> str:
        """Build the table, spawn the engine thread, and return the episode id.

        Constructs each seat from its :class:`SeatConfig` (model seats through ``provider.build_model_seat``,
        computable seats through ``arena.table.policy_seat``, human seats as ``HumanParticipant``), wraps them in
        a :class:`~interlens.arena.live.router.LiveSeatRouter`, and runs the episode with ``on_wave`` bound to
        :meth:`_on_wave`. Fails fast — BEFORE the thread starts — if a configured API seat has no credentials or
        a metered seat has no budget cap, so a misconfiguration surfaces in the lobby instead of as a dead game.
        """
        raise NotImplementedError("live-play lane B")

    def stop(self) -> None:
        """End the session: unblock any waiting human seat, ask the engine thread to wind down, and broadcast
        ``episode_done{status:"stopped"}``. Idempotent — a double-click on Stop must not raise."""
        raise NotImplementedError("live-play lane B")

    # --- browser actions ------------------------------------------------------------------------------- #
    def submit_human(self, seat: str, form: dict) -> None:
        """Validate a human submission and hand it to the blocked seat.

        Raises ``ValueError`` (message shown to the player) if the seat is not waiting, or the move is illegal /
        unparseable / empty. Nothing is enqueued on a rejection: the seat stays blocked and the caller answers
        400 and broadcasts ``input_rejected``. This is the guard that keeps a typo from becoming a silent pass —
        the engine would read empty content as a well-formed no-op turn.
        """
        raise NotImplementedError("live-play lane B")

    def swap_seat(self, seat_idx: int, config: SeatConfig) -> None:
        """Replace a seat's occupant, effective on its next turn.

        Builds the new participant from ``config``, installs it via the router, and broadcasts ``seat_swapped``.
        Refused (``ValueError``) while that seat's human prompt is open: the person is mid-decision and the turn
        is already theirs. v1 applies swaps between turns only.
        """
        raise NotImplementedError("live-play lane B")

    # --- streaming ------------------------------------------------------------------------------------- #
    def broadcast(self, event: str, data: dict) -> int:
        """Append one event to the session log under the next sequence number and push it to every subscriber.

        Returns the sequence number assigned. Never blocks: it is called from the engine thread between turns, so
        a subscriber whose queue is full is dropped rather than allowed to stall the game.
        """
        raise NotImplementedError("live-play lane B")

    def subscribe(self, last_event_id: int | None = None) -> Any:
        """Attach a client. Returns a ``queue.Queue`` of ``(seq, event, data)`` tuples, pre-loaded with every
        logged event after ``last_event_id`` — the replay that makes a reconnect lossless."""
        raise NotImplementedError("live-play lane B")

    def unsubscribe(self, q: Any) -> None:
        """Detach a client's queue (its SSE connection closed)."""
        raise NotImplementedError("live-play lane B")

    def snapshot(self) -> dict:
        """The session's complete current state, for a page load or a reload mid-episode.

        ``{seq, payload, phase, awaiting, occupants, lobby}`` — where ``payload`` is a full
        ``viz.episode_payload`` over the live episode's ``to_json()`` and ``seq`` is the sequence number that
        payload is current as of, so the client subscribes with ``Last-Event-ID: seq`` and misses nothing. Using
        the visualizer's own payload builder (rather than a live-specific one) is what guarantees a reloaded page
        and a streamed one are showing the same thing.
        """
        raise NotImplementedError("live-play lane B")

    def _on_wave(self, episode: Any) -> None:
        """The engine's post-save observer: broadcast every turn committed since the last call, plus ``usage``.

        Runs on the engine thread AFTER the episode was persisted, which is the ordering guarantee that the
        stream never shows a turn that is not yet on disk.
        """
        raise NotImplementedError("live-play lane B")


class SessionManager:
    """The server's session registry. v1 holds ONE active session at a time.

    One at a time is a real constraint, not a shortcut: a live game is meant to be watched and played by the
    person who started it, budgets are per-session, and a second concurrent game would double an API bill with no
    way to tell whose it was. The manager keeps the lobby configuration between games so starting a second game
    with the same lineup is one click.
    """

    def __init__(self, provider: ScenarioProvider, run_dir: Any):
        raise NotImplementedError("live-play lane B")

    @property
    def active(self) -> LiveSession | None:
        """The running session, or ``None`` when the server is sitting in the lobby."""
        raise NotImplementedError("live-play lane B")

    def get(self, sid: str) -> LiveSession:
        """The session with this id. Raises ``KeyError`` when it is unknown or has been replaced."""
        raise NotImplementedError("live-play lane B")

    def start(self, lobby: dict) -> LiveSession:
        """Prepare a game from the lobby configuration and start a session on it. Raises ``ValueError`` if a
        session is already running (stop it first) or the configuration is invalid."""
        raise NotImplementedError("live-play lane B")

    def reset(self) -> None:
        """Stop any active session and return the server to the lobby."""
        raise NotImplementedError("live-play lane B")

    def lobby_state(self) -> dict:
        """The current lobby configuration plus the provider's listings — what the lobby page renders from."""
        raise NotImplementedError("live-play lane B")

    def update_lobby(self, patch: dict) -> dict:
        """Merge a partial lobby edit (one changed seat, a new bank) and return the updated state. Validates
        against the provider's listings so an unknown model or policy is refused at edit time, not at start."""
        raise NotImplementedError("live-play lane B")

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
# [implement: live-play/laneB] 2026-08-16
# [implement: live-play/lobby-defaults] 2026-08-19
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

import asyncio
import logging
import queue
import random
import threading
import uuid
from pathlib import Path
from typing import Any

from ...usage import CostBudget, UsageMeter
from ..engine import EpisodePool
from ..schema import PERSONAS, EpisodeStore
from ..table import POLICY_FACTORIES, policy_seat
from ..viz.episode import episode_payload, seat_kinds
from ..viz.geometry import GameGeometry
from . import events
from .human import HumanParticipant, build_human_message
from .payload import bubble_html, turn_delta
from .provider import SEAT_KINDS, PreparedGame, ScenarioProvider, SeatConfig
from .router import LiveSeatRouter

logger = logging.getLogger(__name__)

# Session phases, in the order a session moves through them. ``awaiting_human`` is a sub-state of ``running``
# reported separately because it is the one phase where the UI must show a form instead of a spinner.
PHASES = ("lobby", "starting", "running", "awaiting_human", "done")

# The lobby's default spend cap, in dollars. Small deliberately: a live game with a person in it can sit idle for
# an hour with an API seat configured, so the default has to be a number nobody minds losing rather than a number
# big enough for a long session. Raise it in the lobby for a game that needs it.
DEFAULT_BUDGET_USD = 2.0

# How many undelivered events a subscriber may fall behind by before it is dropped. Generous — a whole game is a
# few hundred events — because the only thing a smaller number would buy is disconnecting a reader whose browser
# stalled for a second, and a reconnect replays the log anyway.
SUBSCRIBER_QUEUE_MAX = 4096

# The heading the seat-instruction override is appended to a participant's ``private_context`` under. One
# constant, because the lobby's label, the human dock's display and the text the seat actually reads must be the
# same string — an override the operator cannot recognize in the transcript is worse than none.
INSTRUCTION_HEADER = "Additional private instructions for this seat (live-play override):"


def apply_private_instructions(participant: Any, instructions: str) -> Any:
    """Append ``instructions`` to ``participant``'s ``private_context`` as one labelled segment, and return it.

    The whole override mechanism: a live operator gives one seat a persona or a hidden agenda without editing a
    scaffold, and the text folds into that seat's view exactly where its own private material already goes. A
    no-op for empty instructions or for a participant with no ``private_context`` (a policy seat reads no prose).

    Shared with :meth:`ScenarioProvider.build_model_seat` implementations so a model seat's override and a
    scripted seat's are the same segment in the same place rather than two spellings of the same idea.
    """
    if not instructions or not str(instructions).strip():
        return participant
    if not hasattr(participant, "private_context"):
        return participant
    existing = tuple(participant.private_context or ())
    participant.private_context = existing + (f"{INSTRUCTION_HEADER} {instructions}",)
    return participant


#: How many times a shuffle re-draws before accepting an arrangement identical to the one it started from. A
#: uniform permutation returns the lineup unchanged often enough to look broken (always, for a lineup of one
#: distinct seat; half the time for two), and a button that appears to do nothing is worse than a slightly
#: non-uniform draw. Bounded rather than looping: a lineup whose seats are all identical has NO different
#: arrangement, and the honest answer there is to return it unchanged and say so.
SHUFFLE_REDRAWS = 8


def shuffled_seats(seats: list[SeatConfig], rng: random.Random) -> tuple[list[SeatConfig], list[int]]:
    """Permute WHO plays which seat, leaving the seats themselves alone.

    Returns the new lineup and the permutation that produced it as source indices: ``order[i]`` is the index the
    seat now at position ``i`` came from, so ``new[i] is seats[order[i]]`` and ``order`` is what gets recorded.
    Seat NAMES and parties do not move — Avery is still party 0 with party 0's score sheet — only the occupant
    configurations do, which is the thing worth randomizing when seat position carries a protocol advantage (the
    proposer order rotates from the proposer base, so "the model always opens" is a property of the lineup, not
    of the model).

    Uniform over permutations, re-drawn while the resulting ARRANGEMENT is the one it started from (see
    :data:`SHUFFLE_REDRAWS`) — so it is uniform over the arrangements that visibly differ, and returns the input
    unchanged, with the identity order, when no different arrangement exists.

    Parameters
    ----------
    seats : list[SeatConfig]
        The current lineup, in seat order.
    rng : random.Random
        The source of randomness, passed in rather than reached for so a caller can make a shuffle reproducible
        (and so the test can pin an exact permutation instead of asserting that something moved).
    """
    order = list(range(len(seats)))
    before = [s.to_json() for s in seats]
    for _ in range(SHUFFLE_REDRAWS):
        rng.shuffle(order)
        if [before[i] for i in order] != before:
            break
    else:
        order = list(range(len(seats)))           # every draw looked the same: say so rather than pretend
    return [seats[i] for i in order], order


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
        self.sid = sid
        self.provider = provider
        self.game = game
        # Resolved on the way in, so a session constructed directly (a test, a client that posted a bare model
        # seat) seats the same occupant the lobby would have shown: the provider's default model at its default
        # thinking mode. Cheap and idempotent — an already-chosen field is returned untouched.
        offered = provider.list_models() if any(s.kind == "llm" for s in seats) else ()
        self.seats = [s.resolved(offered) for s in seats]
        self.run_dir = Path(run_dir)
        self.budget_usd = None if budget_usd is None else float(budget_usd)
        # The cap binds in two places, and it needs both. The METER is the pool's launch gate and the ledger every
        # metered participant charges; the per-episode ``CostBudget`` is what actually stops a game that is
        # already running, by making the scenario finalize early (``state["budget_exhausted"]``). A meter alone
        # would let one live episode run past the cap forever, since there is no second episode for it to gate.
        self.meter = UsageMeter(self.budget_usd)
        self.phase = "lobby"

        self._lock = threading.RLock()
        self._log: list[tuple[int, str, dict]] = []
        self._seq = 0
        self._subscribers: list[queue.Queue] = []

        self._thread: threading.Thread | None = None
        self._router: LiveSeatRouter | None = None
        self._humans: dict[str, HumanParticipant] = {}
        self._stopping = False
        self._awaiting: dict | None = None

        # Payload state. ``_rows`` is the accumulated render rows the stream has emitted (the delta side of the
        # one payload code path); ``_episode_json`` is the last persisted episode, replaced wholesale on each
        # wave. Both start from a seat-only placeholder so ``/state`` is renderable from the instant the session
        # starts — a human seat can be asked to move before any turn exists, and its dock needs the game.
        self._geometry = GameGeometry.from_instance(game.instance_json or {})
        self._manifest = dict(game.manifest or {})
        self._episode_json: dict = {"episode_id": None, "scenario": None, "arm": game.arm, "status": "starting",
                                    "seats": [{"name": n, "role": "assistant"} for n in game.seat_names],
                                    "turns": [], "round_checkpoints": [], "outcome": {}}
        self._seat_party = {n: i for i, n in enumerate(game.seat_names)}
        self._kinds = seat_kinds(self._episode_json, self._manifest or None)
        self._rows: list[dict] = []
        self._n_emitted = 0
        self._episode_id: str | None = None
        self._done_broadcast = False

    # --- lifecycle ------------------------------------------------------------------------------------- #
    @property
    def seq(self) -> int:
        """The sequence number of the last event this session emitted (0 before any). What a fresh stream
        reports in ``hello`` so a page rendered from a snapshot can tell whether it missed anything."""
        with self._lock:
            return self._seq

    @property
    def occupants(self) -> dict:
        """The current seat -> occupant-label map, or ``{}`` before the table is built."""
        with self._lock:
            return self._router.occupants() if self._router is not None else {}

    @property
    def episode_id(self) -> str | None:
        """The running episode's id, or ``None`` until the first wave lands.

        The engine mints the id inside ``run_episode``, so it does not exist at the moment the thread is spawned;
        the id reaches the browser in the ``episode_started`` event instead, and a client that started the session
        finds it in the ``/state`` snapshot. Nothing needs it earlier — the routes are keyed by session id."""
        return self._episode_id

    def start(self) -> str:
        """Build the table, spawn the engine thread, and return the episode id.

        Constructs each seat from its :class:`SeatConfig` (model seats through ``provider.build_model_seat``,
        computable seats through ``arena.table.policy_seat``, human seats as ``HumanParticipant``), wraps them in
        a :class:`~interlens.arena.live.router.LiveSeatRouter`, and runs the episode with ``on_wave`` bound to
        :meth:`_on_wave`. Fails fast — BEFORE the thread starts — if a configured API seat has no credentials or
        a metered seat has no budget cap, so a misconfiguration surfaces in the lobby instead of as a dead game.

        Returns the episode id, which is ``""`` until the engine mints one (see :attr:`episode_id`).
        """
        with self._lock:
            if self._thread is not None:
                raise ValueError("this session has already been started")
            self._check_seats_are_startable()
            participants, labels = {}, {}
            for idx, config in enumerate(self.seats):
                seat = self.game.seat_names[idx]
                participants[seat] = self._build_participant(idx, config)
                labels[seat] = config.occupant_label()
            self._router = LiveSeatRouter(participants, labels=labels, on_turn_start=self._on_turn_start,
                                          name=f"live:{self.sid}")
            self.phase = "starting"
            self._thread = threading.Thread(target=self._run, name=f"live-engine-{self.sid}", daemon=True)
            self._thread.start()
        return self._episode_id or ""

    def _check_seats_are_startable(self) -> None:
        """Refuse a lineup that cannot play, with the reason the lobby should show.

        Two checks, both of which are otherwise discovered as a dead game: an ``llm`` seat on a model the provider
        reports as unavailable (no API key, no weights), and a metered seat with no spend cap."""
        if not any(config.kind == "llm" for config in self.seats):
            return                                       # nothing to charge and nothing to authenticate
        models = {m.model_id: m for m in self.provider.list_models()}
        for idx, config in enumerate(self.seats):
            if config.kind != "llm":
                continue
            info = models.get(config.model_id)
            if info is None:
                raise ValueError(f"seat {idx} ({self.game.seat_names[idx]}): unknown model {config.model_id!r}")
            if not info.available:
                raise ValueError(f"seat {idx} ({self.game.seat_names[idx]}): {info.label} is unavailable — "
                                 f"{info.unavailable_reason or 'no reason given'}")
            if info.metered and not self.budget_usd:
                raise ValueError(f"seat {idx} ({self.game.seat_names[idx]}): {info.label} costs money, so this "
                                 "session needs a budget cap before it can start")

    def _build_participant(self, idx: int, config: SeatConfig) -> Any:
        """One seat's participant, from its configuration. The lobby's only route into a live table.

        ``llm`` goes through the provider (which owns credentials, thinking modes and metering); ``rational`` and
        ``oracle`` are the same ``policy_seat`` call differing only in ``full_info`` — a private-information
        belief model versus the exact game tables; ``human`` blocks on the browser; ``scripted`` replays
        ``config.instructions`` as its fixed line, which is what makes an all-offline smoke game possible.
        """
        game = self.game.game
        if config.kind == "llm":
            return self.provider.build_model_seat(config.model_id, thinking=config.thinking, meter=self.meter,
                                                  extra_instructions=config.instructions)
        if config.kind in ("rational", "oracle"):
            if config.policy and config.policy not in POLICY_FACTORIES:
                raise ValueError(f"unknown policy {config.policy!r}; choose one of {sorted(POLICY_FACTORIES)}")
            return policy_seat(config.policy or "bayes-rational", idx, game, deadline=self.game.deadline,
                               full_info=(config.kind == "oracle"))
        if config.kind == "human":
            # The name MUST be ``occupant_detail()``. A HumanParticipant stamps ``human:<its own name>`` on the
            # turns it plays and the router deliberately does not overwrite a self-stamp, so any other spelling
            # here would make one seat report two occupants and its timeline unreadable.
            participant = HumanParticipant(name=config.occupant_detail(), seat=idx,
                                           sheet=game.sheets[idx], space=game.space,
                                           deadline=self.game.deadline, publisher=self.broadcast)
            self._humans[self.game.seat_names[idx]] = participant
            return apply_private_instructions(participant, config.instructions)
        if config.kind == "scripted":
            # Imported here, not at module scope: ``participant.participants.__init__`` eagerly imports the
            # local-model participant, so a top-level import would drag torch into a CPU-only lobby and make it
            # take ten seconds to open on a machine with no GPU to use anyway. A scripted seat is the rare path
            # (smoke tests and demos), so it is the right one to pay the import on.
            from ...participant.participants.scripted_participant import ScriptedParticipant
            return ScriptedParticipant(config.display_name or f"scripted{idx}", config.instructions or "")
        raise ValueError(f"unknown seat kind {config.kind!r}")

    def _run(self) -> None:
        """The engine thread. Owns its own event loop and never touches the HTTP side except through
        :meth:`broadcast`, which is thread-safe by construction."""
        try:
            pool = EpisodePool(store=EpisodeStore(self.run_dir), meter=self.meter, max_concurrent=1)
            asyncio.run(pool.run_episode(
                self.game.scenario, self.game.instance, self.game.arm, self._router,
                seed=int((self.game.cfg or {}).get("seed", 0)), cfg=dict(self.game.cfg or {}),
                budget=CostBudget(self.budget_usd) if self.budget_usd else None,
                on_wave=self._on_wave))
        except BaseException as exc:                     # noqa: BLE001 - the thread's last line of defence
            logger.exception("live session %s: the engine thread died", self.sid)
            self.broadcast(*events.error(f"{type(exc).__name__}: {exc}", fatal=True))
        finally:
            # ``run_episode`` returns None without ever firing the observer when the meter was already exhausted
            # at launch, and a crash skips the finalize call — either way a browser that only ever hears about
            # waves would sit on a spinner forever, so the session closes itself out here if nothing else did.
            self._finish(self._final_status("done"))

    def stop(self) -> None:
        """End the session: unblock any waiting human seat, ask the engine thread to wind down, and broadcast
        ``episode_done{status:"stopped"}``. Idempotent — a double-click on Stop must not raise.

        A blocked human seat is released immediately (its ``generate`` raises, and the engine finalizes the
        episode as an error, which is the honest record: a stopped game did not play itself out). A seat that is
        mid-generation cannot be interrupted — an API call in flight is in flight — so a stopped session ends
        when that turn returns, and ``episode_done`` is broadcast then rather than optimistically now."""
        with self._lock:
            self._stopping = True
            humans = list(self._humans.values())
        for participant in humans:
            try:
                participant.unblock("stopped")
            except Exception:                            # noqa: BLE001 - stopping must not raise
                logger.exception("live session %s: unblocking a human seat failed", self.sid)
        if self._thread is None or not self._thread.is_alive():
            self._finish("stopped")

    def _finish(self, status: str) -> None:
        """Broadcast ``episode_done`` exactly once, whatever route the episode ended by."""
        with self._lock:
            if self._done_broadcast:
                return
            self._done_broadcast = True
            self.phase = "done"
            outcome = dict(self._episode_json.get("outcome") or {})
            self.broadcast(*events.episode_done(status, outcome, self._final_slice()))

    def _final_slice(self) -> dict:
        """The closing numbers the summary strip needs without a second fetch."""
        ep = self._episode_json
        return {"episode_id": ep.get("episode_id"), "status": ep.get("status"),
                "rounds_used": ep.get("rounds_used"), "tokens_in": ep.get("tokens_in"),
                "tokens_out": ep.get("tokens_out"), "cost_usd": ep.get("cost_usd"),
                "error": ep.get("error"), "n_turns": len(self._rows)}

    # --- browser actions ------------------------------------------------------------------------------- #
    def submit_human(self, seat: str, form: dict) -> None:
        """Validate a human submission and hand it to the blocked seat.

        Raises ``ValueError`` (message shown to the player) if the seat is not waiting, or the move is illegal /
        unparseable / empty. Nothing is enqueued on a rejection: the seat stays blocked and the caller answers
        400 and broadcasts ``input_rejected``. This is the guard that keeps a typo from becoming a silent pass —
        the engine would read empty content as a well-formed no-op turn.
        """
        with self._lock:
            participant = self._humans.get(seat)
            if participant is None:
                raise ValueError(f"seat {seat!r} is not played by a person")
            pending = participant.pending
            if pending is None:
                raise ValueError(f"seat {seat!r} is not waiting for a move right now")
            message = build_human_message(form, name=participant.name, space=self.game.game.space,
                                          pending=pending)
            participant.submit(message)

    def swap_seat(self, seat_idx: int, config: SeatConfig) -> None:
        """Replace a seat's occupant, effective on its next turn.

        Builds the new participant from ``config``, installs it via the router, and broadcasts ``seat_swapped``.
        Refused (``ValueError``) while that seat's human prompt is open: the person is mid-decision and the turn
        is already theirs. v1 applies swaps between turns only.
        """
        with self._lock:
            if self._router is None:
                raise ValueError("this session has not started yet")
            if not 0 <= seat_idx < len(self.game.seat_names):
                raise ValueError(f"no seat {seat_idx} (this game seats {len(self.game.seat_names)})")
            seat = self.game.seat_names[seat_idx]
            outgoing = self._humans.get(seat)
            if outgoing is not None and outgoing.pending is not None:
                raise ValueError(f"{seat} is mid-decision — a seat cannot change hands while its player is "
                                 "answering. Swap it once the turn is played.")
            self._humans.pop(seat, None)
            config = config.resolved(self.provider.list_models() if config.kind == "llm" else ())
            participant = self._build_participant(seat_idx, config)
            label = config.occupant_label()
            previous = self._router.swap(seat, participant, label)
            self.seats[seat_idx] = config
            self.broadcast(*events.seat_swapped(seat, seat_idx, previous, label, at_turn=len(self._rows)))

    # --- streaming ------------------------------------------------------------------------------------- #
    def broadcast(self, event: str, data: dict) -> int:
        """Append one event to the session log under the next sequence number and push it to every subscriber.

        Returns the sequence number assigned. Never blocks: it is called from the engine thread between turns, so
        a subscriber whose queue is full is dropped rather than allowed to stall the game.

        This is also where the session's own phase is kept: the events that move it (a seat blocking on a person,
        a turn landing, the episode ending) are exactly the events that go over the wire, so reading the phase off
        the stream keeps ``/state`` and the stream from ever disagreeing about where the session is.
        """
        with self._lock:
            self._seq += 1
            seq = self._seq
            self._note_phase(event, data)
            self._log.append((seq, event, data))
            for q in list(self._subscribers):
                try:
                    q.put_nowait((seq, event, data))
                except queue.Full:
                    logger.warning("live session %s: dropping a subscriber that fell %d events behind",
                                   self.sid, q.qsize())
                    self._subscribers.remove(q)
        return seq

    def _note_phase(self, event: str, data: dict) -> None:
        """Move the session phase in response to an outgoing event. Called under the lock."""
        if event == events.AWAITING_HUMAN:
            # The participant cannot know the episode's turn index (the engine passes one only alongside a
            # capture request), so it publishes -1 and the session — which counts the rows it has streamed —
            # stamps the real one here, exactly as it does for ``turn_started``.
            if int(data.get("turn_idx", -1)) < 0:
                data["turn_idx"] = len(self._rows)
            self.phase, self._awaiting = "awaiting_human", dict(data)
        elif event in (events.TURN_STARTED, events.TURN_APPENDED, events.EPISODE_STARTED):
            self._awaiting = None
            if self.phase != "done":
                self.phase = "running"
        elif event == events.EPISODE_DONE:
            self.phase, self._awaiting = "done", None

    def subscribe(self, last_event_id: int | None = None) -> Any:
        """Attach a client. Returns a ``queue.Queue`` of ``(seq, event, data)`` tuples, pre-loaded with every
        logged event after ``last_event_id`` — the replay that makes a reconnect lossless."""
        q: queue.Queue = queue.Queue(maxsize=SUBSCRIBER_QUEUE_MAX)
        with self._lock:
            since = -1 if last_event_id is None else int(last_event_id)
            for seq, event, data in self._log:
                if seq > since:
                    q.put_nowait((seq, event, data))
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: Any) -> None:
        """Detach a client's queue (its SSE connection closed)."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def snapshot(self) -> dict:
        """The session's complete current state, for a page load or a reload mid-episode.

        ``{seq, payload, phase, awaiting, occupants, lobby}`` — where ``payload`` is a full
        ``viz.episode_payload`` over the live episode's ``to_json()`` and ``seq`` is the sequence number that
        payload is current as of, so the client subscribes with ``Last-Event-ID: seq`` and misses nothing. Using
        the visualizer's own payload builder (rather than a live-specific one) is what guarantees a reloaded page
        and a streamed one are showing the same thing.
        """
        with self._lock:
            payload = episode_payload(self._episode_json, self.game.instance_json or None,
                                      manifest=self._manifest or None, geometry=self._geometry,
                                      reconstruct=False, paths={"run": str(self.run_dir)})
            return {"sid": self.sid, "seq": self._seq, "payload": payload, "phase": self.phase,
                    "awaiting": dict(self._awaiting) if self._awaiting else None,
                    "occupants": self.occupants,
                    "lobby": self.lobby()}

    def lobby(self) -> dict:
        """This session's own configuration, in the shape the ``lobby_state`` event carries.

        Carries the provider's ``models`` and ``policies`` listings as well as the current lineup, because the
        live page's swap dock reuses the lobby's seat editor and must be able to offer the same choices without a
        second round trip to ``/api/lobby``."""
        return {"sid": self.sid, "seats": [s.to_json() for s in self.seats], "budget_usd": self.budget_usd,
                "seat_names": list(self.game.seat_names), "arm": self.game.arm,
                "instance_id": (self.game.instance_json or {}).get("instance_id") or "",
                "deadline": self.game.deadline,
                "models": [m.to_json() for m in self.provider.list_models()],
                "policies": sorted(POLICY_FACTORIES), "seat_kinds": list(SEAT_KINDS)}

    def _on_turn_start(self, seat: str, occupant: str | None) -> None:
        """The router's pre-generation hook: announce who is about to move.

        A hint, not a record — nothing is on disk yet — which is exactly why it is worth sending: it is the only
        moment at which "Blake is thinking" is both true and useful, and it covers the half-minute an API seat
        spends generating.

        The round and phase are read off the last COMMITTED turn: the router's hook is handed the seat and its
        occupant and nothing else (it fires from inside ``generate``, where the ``SeatRequest`` is no longer in
        hand), and a wave's turns share a round, so the last committed turn is right except across a round
        boundary, where it is one behind for one turn. The authoritative round arrives with ``turn_appended``."""
        idx = len(self._rows)
        turn = (self._episode_json.get("turns") or [{}])[-1] if self._episode_json.get("turns") else {}
        self.broadcast(*events.turn_started(idx, int(turn.get("round") or 0) or 1, turn.get("phase") or "",
                                            seat, self._seat_party.get(seat, 0), occupant))

    def _on_wave(self, episode: Any) -> None:
        """The engine's post-save observer: broadcast every turn committed since the last call, plus ``usage``.

        Runs on the engine thread AFTER the episode was persisted, which is the ordering guarantee that the
        stream never shows a turn that is not yet on disk.
        """
        try:
            with self._lock:
                self._episode_json = episode.to_json()
                if self._episode_id is None:
                    self._episode_id = episode.episode_id
                    self.broadcast(*events.episode_started(episode.episode_id))
                # Seat kinds are re-derived per wave rather than pinned at start: without a run manifest the
                # visualizer INFERS them from output-token accounting, so they are only as good as the turns
                # played so far, and a row must carry the same answer a rebuild over the same prefix would give.
                self._kinds = seat_kinds(self._episode_json, self._manifest or None)
                turns = self._episode_json.get("turns") or []
                oracles = None                       # re-derived per turn: a turn's records are written with it
                for turn in turns[self._n_emitted:]:
                    row = turn_delta(self._episode_json, turn, self._rows, geometry=self._geometry,
                                     kinds=self._kinds, oracles=oracles, seat_party=self._seat_party)
                    self.broadcast(*events.turn_appended(
                        row, bubble_html(self._bubble_payload(), row),
                        int(self._episode_json.get("rounds_used") or 0),
                        dict(self._episode_json.get("outcome") or {}) or None))
                self._n_emitted = len(turns)
                self.broadcast(*events.usage(
                    int(self._episode_json.get("tokens_in") or 0),
                    int(self._episode_json.get("tokens_out") or 0),
                    float(self._episode_json.get("cost_usd") or 0.0), self.budget_usd, self._over_budget()))
                status = self._episode_json.get("status")
            if status in ("done", "error"):
                self._finish(self._final_status(status))
        except Exception:                                # noqa: BLE001 - an observer must never kill a game
            logger.exception("live session %s: broadcasting a wave failed", self.sid)

    def _bubble_payload(self) -> dict:
        """What a bubble renders against: the seat table and the transcript so far.

        The turns are not decoration. ``_chat_bubble`` derives each seat's DEFAULT occupant from them
        (``viz.page.occupant_defaults``) and badges only a turn that departs from it, so a bubble rendered
        against a payload with no turns would silently drop the "now oracle:…" badge on every turn after a swap —
        the one case the badge exists for. The rows are the session's accumulated ones and the row being
        rendered is already among them, which is exactly the prefix a reload would rebuild from."""
        kinds = self._kinds["kinds"]
        return {"seats": [{"name": s.get("name"), "party": i, "kind": kinds.get(s.get("name"), "llm")}
                          for i, s in enumerate(self._episode_json.get("seats") or [])],
                "turns": self._rows}

    def _over_budget(self) -> bool:
        """Whether this session's spend has reached its cap — the meter's own gate, or the episode's recorded
        cost against the per-episode ``CostBudget`` that actually stops the game."""
        if not self.budget_usd:
            return False
        return self.meter.exhausted or float(self._episode_json.get("cost_usd") or 0.0) >= self.budget_usd

    def _final_status(self, episode_status: str) -> str:
        """What the ``episode_done`` event calls the ending: the live-play reason when there is one (the player
        stopped it, the cap stopped it), otherwise the episode's own status."""
        if self._stopping:
            return "stopped"
        if self._over_budget():
            return "budget_stopped"
        return episode_status


class SessionManager:
    """The server's session registry. v1 holds ONE active session at a time.

    One at a time is a real constraint, not a shortcut: a live game is meant to be watched and played by the
    person who started it, budgets are per-session, and a second concurrent game would double an API bill with no
    way to tell whose it was. The manager keeps the lobby configuration between games so starting a second game
    with the same lineup is one click.
    """

    def __init__(self, provider: ScenarioProvider, run_dir: Any, rng: random.Random | None = None):
        self.provider = provider
        self.run_dir = Path(run_dir)
        # The lobby's own source of randomness (currently just the seat shuffle). Injectable so a caller can make
        # a sitting reproducible and a test can pin the permutation rather than assert that something moved.
        self._rng = rng or random.Random()
        self._lock = threading.RLock()
        self._sessions: dict[str, LiveSession] = {}
        self._active: LiveSession | None = None
        banks = provider.list_banks()
        framings = provider.list_framings()
        self._lobby: dict = {
            "bank": banks[0].bank_id if banks else None,
            "framing": (framings[0] or {}).get("framing_id") if framings else None,
            "instance_id": None,
            "budget_usd": DEFAULT_BUDGET_USD,
            "seats": [s.to_json() for s in self._default_seats(banks[0].n_parties if banks else 2)],
            "overrides": {},
            # The permutation the last shuffle applied, as source indices (see :func:`shuffled_seats`), or ``[]``
            # when the lineup has not been shuffled. Recorded rather than merely applied: seat position carries a
            # protocol advantage, so "this lineup was randomized" is a fact about the game about to be played. It
            # rides into the episode's cfg at start; the per-turn occupant stamp remains the ground truth for who
            # actually played where.
            "last_shuffle": [],
            # The last refused edit, shown in the lobby's status strip. Kept HERE rather than only raised,
            # because a page that re-renders from the state it was handed has nowhere else to read it from.
            "error": "",
        }

    @staticmethod
    def _default_seats(n_parties: int | None) -> list[SeatConfig]:
        """A starting lineup for a bank of ``n_parties`` seats: every seat a private-information rational policy.

        Computable seats, not models, because the lobby must open into a configuration that costs nothing and
        runs offline — a default that spends money on the first click is a bad default."""
        return [SeatConfig(kind="rational", policy="bayes-rational") for _ in range(int(n_parties or 2))]

    @property
    def active(self) -> LiveSession | None:
        """The running session, or ``None`` when the server is sitting in the lobby."""
        with self._lock:
            return self._active

    def get(self, sid: str) -> LiveSession:
        """The session with this id. Raises ``KeyError`` when it is unknown or has been replaced."""
        with self._lock:
            return self._sessions[sid]

    def start(self, lobby: dict | None = None) -> LiveSession:
        """Prepare a game from the lobby configuration and start a session on it. Raises ``ValueError`` if a
        session is already running (stop it first) or the configuration is invalid."""
        with self._lock:
            if lobby:
                self.update_lobby(lobby)
            if self._active is not None and self._active.phase != "done":
                raise ValueError("a session is already running — stop it before starting another")
            cfg = self._lobby
            game = self.provider.prepare(cfg["bank"], cfg["framing"], cfg["instance_id"],
                                         dict(cfg.get("overrides") or {}))
            seats = self._seats_for(game)
            self._lobby["seats"] = [s.to_json() for s in seats]
            if self._lobby.get("last_shuffle"):
                # Provenance on the episode itself: seat position carries a protocol advantage (the proposer
                # order rotates from the proposer base), so a randomized lineup is a fact about the game, not
                # about the lobby session that configured it. The per-turn occupant stamp stays authoritative
                # for who actually played where; this only says the arrangement was drawn rather than chosen.
                game.cfg["live_seat_shuffle"] = list(self._lobby["last_shuffle"])
            session = LiveSession(uuid.uuid4().hex[:12], self.provider, game, seats, self.run_dir,
                                  budget_usd=cfg.get("budget_usd"))
            session.start()
            self._sessions[session.sid] = session
            self._active = session
            return session

    def _seats_for(self, game: PreparedGame) -> list[SeatConfig]:
        """The lobby's seat configs, padded or trimmed to the prepared game's actual seat count.

        The lobby builds its cards before an instance is chosen (a bank declares ``n_parties``), so a bank of
        mixed sizes can hand back a game with more seats than were configured. Padding with the default rational
        seat is the only answer that still produces a playable table."""
        configs = [SeatConfig.from_json(s) for s in self._lobby.get("seats") or []]
        n = len(game.seat_names)
        if len(configs) < n:
            configs += self._default_seats(n - len(configs))
        return configs[:n]

    def reset(self) -> None:
        """Stop any active session and return the server to the lobby."""
        with self._lock:
            session, self._active = self._active, None
        if session is not None:
            session.stop()

    def lobby_state(self) -> dict:
        """The current lobby configuration plus the provider's listings — what the lobby page renders from.

        The complete set of keys, since three things render from this one dict (the lobby page, ``GET
        /api/lobby``, and the ``lobby_state`` event) and a key that exists in only two of them is a drift waiting
        to happen:

        - ``banks`` / ``framings`` / ``models`` — the provider's listings, as their ``to_json()`` dicts. An
          unavailable model is LISTED with its ``unavailable_reason``, never filtered out.
        - ``policies`` — the names in ``table.POLICY_FACTORIES``, for the rational/oracle picker.
        - ``seat_kinds`` — the kinds a seat may take (:data:`~interlens.arena.live.provider.SEAT_KINDS`).
        - ``seat_names`` — seat order for the chosen bank, so the cards can be labelled before a game exists.
        - ``bank`` / ``framing`` / ``instance_id`` / ``seats`` / ``budget_usd`` — the current selection.
          ``instance_id`` is ``""`` for "let the provider choose", which is also what the lobby may post back.
        - ``running`` / ``sid`` / ``phase`` / ``episode_id`` — whether a session is live and how to reach it.
          ``running`` is a plain bool so a page can branch on it; ``sid`` is what ``/play`` is keyed by.
        - ``error`` — the last refused edit's message, ``""`` when the last one was accepted.
        """
        with self._lock:
            active = self._active
            banks = {b.bank_id: b for b in self.provider.list_banks()}
            n_parties = getattr(banks.get(self._lobby["bank"]), "n_parties", None) or len(self._lobby["seats"])
            return {
                **self._lobby,
                "instance_id": self._lobby["instance_id"] or "",
                "banks": [b.to_json() for b in banks.values()],
                "framings": list(self.provider.list_framings()),
                "models": [m.to_json() for m in self.provider.list_models()],
                "policies": sorted(POLICY_FACTORIES),
                "seat_kinds": list(SEAT_KINDS),
                "seat_names": list(PERSONAS[:int(n_parties)]),
                "running": active is not None and active.phase != "done",
                "sid": None if active is None else active.sid,
                "phase": None if active is None else active.phase,
                "episode_id": None if active is None else active.episode_id,
            }

    def update_lobby(self, patch: dict) -> dict:
        """Merge a partial lobby edit (one changed seat, a new bank) and return the updated state. Validates
        against the provider's listings so an unknown model or policy is refused at edit time, not at start.

        Recognized keys: ``bank``, ``framing``, ``instance_id`` (``""`` = let the provider choose),
        ``budget_usd`` (``null`` = uncapped, which only a lineup with no metered seat may start),
        ``overrides``, ``shuffle`` (``true`` permutes the current lineup among the seats — see
        :func:`shuffled_seats` — and records the permutation in ``last_shuffle``; any later seat edit clears that
        record, since a permutation that no longer maps the lineup to a previous one describes nothing), and the
        seats. ``seats`` is the whole list; a single-card edit may instead send
        ``{"seat_idx": i, "seat": {...}}`` (``index`` is accepted as a synonym), so a lobby with six seats does
        not have to round-trip all six to change one. Both forms are supported — send whichever the page finds
        simpler.
        """
        with self._lock:
            try:
                return self._apply_lobby_patch(dict(patch or {}))
            except ValueError as exc:
                # Recorded as well as raised: the caller answers 400 with this message, but a page that
                # re-renders from the state it was handed has nowhere else to read the refusal from.
                self._lobby["error"] = str(exc)
                raise

    def _apply_lobby_patch(self, patch: dict) -> dict:
        """Apply one validated lobby patch under the lock. Raises ``ValueError`` before mutating anything the
        rejected field owns, so a refused edit never leaves the lobby half-changed."""
        if "bank" in patch:
            banks = {b.bank_id: b for b in self.provider.list_banks()}
            if patch["bank"] not in banks:
                raise ValueError(f"unknown bank {patch['bank']!r}; have {sorted(banks)}")
            if patch["bank"] != self._lobby["bank"]:
                # A different bank can seat a different number of parties, and an instance id from the old
                # bank means nothing in the new one — so both are re-defaulted rather than carried over.
                self._lobby["instance_id"] = None
                self._lobby["seats"] = [s.to_json() for s in self._default_seats(banks[patch["bank"]].n_parties)]
            self._lobby["bank"] = patch["bank"]
        if "framing" in patch:
            framings = {f.get("framing_id") for f in self.provider.list_framings()}
            if patch["framing"] not in framings:
                raise ValueError(f"unknown framing {patch['framing']!r}; have {sorted(f for f in framings)}")
            self._lobby["framing"] = patch["framing"]
        if "instance_id" in patch:
            self._lobby["instance_id"] = patch["instance_id"] or None
        if "budget_usd" in patch:
            budget = patch["budget_usd"]
            self._lobby["budget_usd"] = None if budget in (None, "") else float(budget)
        if "overrides" in patch:
            self._lobby["overrides"] = dict(patch["overrides"] or {})
        if patch.get("shuffle"):
            # Applied HERE rather than in the browser so the permutation exists on the server, where it can be
            # recorded on the game that gets played. The page posts ``{"shuffle": true}`` and re-renders from the
            # answer, so there is no second permutation implementation to keep in step.
            seats = [SeatConfig.from_json(s) for s in self._lobby["seats"]]
            shuffled, order = shuffled_seats(seats, self._rng)
            self._lobby["seats"] = [s.to_json() for s in shuffled]
            self._lobby["last_shuffle"] = order
        if "seats" in patch:
            self._lobby["seats"] = [self._validated(SeatConfig.from_json(s)).to_json() for s in patch["seats"]]
            self._lobby["last_shuffle"] = []       # hand-edited afterwards: the recorded permutation is stale
        if "seat" in patch:
            idx = int(patch.get("seat_idx", patch.get("index", 0)))
            seats = list(self._lobby["seats"])
            while len(seats) <= idx:
                seats.append(SeatConfig(kind="rational", policy="bayes-rational").to_json())
            seats[idx] = self._validated(SeatConfig.from_json(patch["seat"])).to_json()
            self._lobby["seats"] = seats
            self._lobby["last_shuffle"] = []
        self._lobby["error"] = ""
        return self.lobby_state()

    def _validated(self, config: SeatConfig) -> SeatConfig:
        """One seat config checked against what this provider can actually seat, and RETURNED with its unset
        model-seat choices resolved (:meth:`SeatConfig.resolved`) — a bare ``{"kind": "llm"}`` from any client
        becomes the provider's default model at that model's default thinking mode, exactly as the lobby page
        renders it. Existence only — availability (a missing API key) is re-checked at start, since a key can
        appear between editing and playing."""
        if config.kind not in SEAT_KINDS:
            raise ValueError(f"unknown seat kind {config.kind!r}; choose one of {list(SEAT_KINDS)}")
        if config.kind == "llm":
            offered = self.provider.list_models()
            config = config.resolved(offered)
            models = {m.model_id: m for m in offered}
            if config.model_id not in models:
                raise ValueError(f"unknown model {config.model_id!r}; have {sorted(models)}")
            info = models[config.model_id]
            if config.thinking not in info.thinking_modes:
                raise ValueError(f"{info.label} does not support thinking={config.thinking!r}; "
                                 f"it offers {list(info.thinking_modes)}")
        if config.kind in ("rational", "oracle") and config.policy and config.policy not in POLICY_FACTORIES:
            raise ValueError(f"unknown policy {config.policy!r}; choose one of {sorted(POLICY_FACTORIES)}")
        return config

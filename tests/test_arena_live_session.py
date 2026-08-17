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
# [implement: live-play/laneB] 2026-08-16
"""``LiveSession`` and ``SessionManager``: lobby to table, and the stream a live game emits.

Every test here plays a REAL episode through the real engine — a two-issue, three-seat scorable negotiation with
computable seats — and touches no network at all. That combination is the point: the things worth pinning about a
live session (that a lobby configuration becomes the participants it names, that a budget cap binds, that the
delta stream and a page reload agree) are all properties of the whole path, and a mocked engine would pin none of
them. The games are tiny, so the whole file runs in about a second.

The zero-drift gate is :func:`test_the_streamed_rows_are_exactly_what_a_reload_rebuilds`: the rows the session
accumulated one turn at a time, against the rows a full ``episode_payload`` rebuild produces for the same
episode. It is asserted as an identity rather than a spot-check, so it keeps holding as the payload evolves.
"""
from __future__ import annotations

import functools
import json
import queue
import threading
import time

import pytest

from interlens.arena.live import events
from interlens.arena.live.human import HumanParticipant
from interlens.arena.live.payload import bubble_html, turn_delta
from interlens.arena.live.provider import BankInfo, ModelInfo, PreparedGame, SeatConfig
from interlens.arena.live.session import (DEFAULT_BUDGET_USD, INSTRUCTION_HEADER, LiveSession, SessionManager,
                                          apply_private_instructions)
from interlens.arena.negotiation.games import build_preset_instance
from interlens.arena.negotiation.policy_participant import PolicyParticipant
from interlens.arena.negotiation.sheets import GameSpec
from interlens.arena.schema import PERSONAS
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.viz import page as viz_page
from interlens.arena.viz.episode import episode_payload
from interlens.message import Message
from interlens.participant.participants.scripted_participant import ScriptedParticipant

# The arm the scorable negotiation actually offers. ``PreparedGame.arm`` defaults to ``"live"``, which no
# scenario knows — a provider names a real arm, and this stub does the same thing the launcher will.
ARM = "moves_chat"

# How long a test waits for a two-issue game of computable seats to play out. It takes milliseconds; the timeout
# exists only so a genuinely stuck engine thread fails the test instead of hanging the suite.
TIMEOUT = 20.0


def lane_a_ready() -> bool:
    """Whether lane A's ``SeatConfig.occupant_label`` has landed. A session cannot build a table without it (the
    router stamps the label on every turn), so the tests that start one are skipped until it does rather than
    failing with a lane-attribution error that says nothing about this lane's code."""
    try:
        SeatConfig(kind="rational", policy="bayes-rational").occupant_label()
        return True
    except NotImplementedError:
        return False


needs_lane_a = pytest.mark.skipif(not lane_a_ready(),
                                  reason="lane A's SeatConfig.occupant_label has not landed yet")


@functools.lru_cache(maxsize=None)
def generated_game(n_parties: int):
    """One generated instance per seat count, built once for the whole suite.

    ``build_preset_instance`` is solver-verified — it enumerates the deal space and checks the analysis — which
    costs a second or two, and every test in this file wants the same tiny game. The instance is read-only from
    here on (the scenario builds its state from a copy), so sharing it is safe and turns a minute of setup into
    one build."""
    instance, protocol_cfg = build_preset_instance("scorable", n_parties=n_parties, n_issues=2, n_options=2,
                                                  seed=3)
    return instance, protocol_cfg, GameSpec.from_json(instance.payload)


class StubModelSeat(ScriptedParticipant):
    """A stand-in for an API seat: talks every turn, takes no formal action, and reports token usage.

    The usage is what makes it a MODEL seat rather than a computable one as far as everything downstream is
    concerned — the visualizer infers seat kinds from output-token accounting — so a table built from this stub
    exercises the same mixed-kind path a real lineup does, for free and offline."""

    def generate(self, view, **kwargs) -> Message:
        message = super().generate(view, **kwargs)
        message.metadata.update({"n_tokens": 12, "n_tokens_in": 40, "cost_usd": 0.01})
        return message


class StubProvider:
    """A :class:`~interlens.arena.live.provider.ScenarioProvider` over one tiny generated negotiation.

    Everything a provider must supply, and nothing an experiment would recognize: one bank holding one instance,
    one framing that frames nothing, and three models — an available free one, an available metered one and an
    unavailable one — because the interesting provider behaviour on the session side is entirely about how those
    three are treated at start.
    """

    def __init__(self, n_parties: int = 3):
        self.instance, self.protocol_cfg, self.spec = generated_game(n_parties)
        self.n_parties = n_parties
        self.model_seats: list[dict] = []            # every build_model_seat call, for the assembly assertions

    def list_banks(self) -> list[BankInfo]:
        return [BankInfo("stub", "Stub bank", (self.instance.instance_id,), self.n_parties, "one tiny game")]

    def list_framings(self) -> list[dict]:
        return [{"framing_id": "plain", "label": "Plain", "description": "no re-skin"}]

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo("stub-free", "Stub (free)", "stub", ("off",), metered=False),
            ModelInfo("stub-paid", "Stub (paid)", "stub", ("off", "on"), metered=True),
            ModelInfo("stub-gone", "Stub (no key)", "stub", ("off",), available=False,
                      unavailable_reason="STUB_API_KEY is not set"),
        ]

    def prepare(self, bank: str, framing: str, instance_id: str | None, overrides: dict | None = None):
        if bank != "stub":
            raise ValueError(f"unknown bank {bank!r}")
        if framing != "plain":
            raise ValueError(f"unknown framing {framing!r}")
        return PreparedGame(instance=self.instance, scenario=ScorableNegotiation(), game=self.spec,
                            cfg=dict(self.protocol_cfg), arm=ARM, deadline=self.spec.rounds,
                            seat_names=tuple(PERSONAS[:self.n_parties]),
                            instance_json=self.instance.to_json())

    def build_model_seat(self, model_id: str, *, thinking: str = "off", meter=None, extra_instructions: str = ""):
        self.model_seats.append({"model_id": model_id, "thinking": thinking, "meter": meter,
                                 "extra_instructions": extra_instructions})
        seat = StubModelSeat(f"api:{model_id}", ['```json\n{"action": "none", "message": "still thinking."}\n```'])
        return apply_private_instructions(seat, extra_instructions)


def make_manager(tmp_path, n_parties: int = 3) -> SessionManager:
    """A manager over a fresh stub provider, writing episodes under ``tmp_path``."""
    return SessionManager(StubProvider(n_parties), tmp_path)


def start(manager: SessionManager, seats: list[SeatConfig], budget_usd: float | None = None) -> LiveSession:
    """Configure a lineup in the lobby and start it — the two calls every session test opens with."""
    manager.update_lobby({"seats": [s.to_json() for s in seats], "budget_usd": budget_usd})
    return manager.start()


def wait_for(predicate, timeout: float = TIMEOUT, what: str = "condition") -> None:
    """Block until ``predicate()`` or fail the test. Polled rather than event-driven because what is being waited
    for is a whole engine thread reaching a state, not one signal."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    pytest.fail(f"timed out after {timeout}s waiting for {what}")


def play_out(session: LiveSession) -> None:
    """Wait for a session's episode to finish."""
    wait_for(lambda: session.phase == "done", what="the episode to finish")


def kinds(*names: str) -> list[SeatConfig]:
    """A lineup of computable seats, one per name (``"rational"`` / ``"oracle"``)."""
    return [SeatConfig(kind=name, policy="bayes-rational") for name in names]


# --------------------------------------------------------------------------------------- the lobby --
def test_the_lobby_opens_on_a_configuration_that_costs_nothing(tmp_path):
    """Every seat a computable policy and a default cap: the first click must be free and offline, or the lobby
    is a way to spend money by accident."""
    state = make_manager(tmp_path).lobby_state()
    assert state["bank"] == "stub" and state["framing"] == "plain"
    assert [s["kind"] for s in state["seats"]] == ["rational"] * 3
    assert state["budget_usd"] == DEFAULT_BUDGET_USD
    assert state["running"] is False


def test_the_lobby_carries_the_providers_listings_and_the_policy_zoo(tmp_path):
    """The lobby page renders entirely from this, so an unavailable model has to be LISTED with its reason —
    silently omitting it looks like the model does not exist."""
    state = make_manager(tmp_path).lobby_state()
    assert [b["bank_id"] for b in state["banks"]] == ["stub"]
    assert [f["framing_id"] for f in state["framings"]] == ["plain"]
    gone = next(m for m in state["models"] if m["model_id"] == "stub-gone")
    assert gone["available"] is False and "STUB_API_KEY" in gone["unavailable_reason"]
    assert "bayes-rational" in state["policies"] and "human" in state["seat_kinds"]


def test_the_lobby_state_carries_every_key_its_three_readers_need(tmp_path):
    """Three things render from this one dict — the lobby page, ``GET /api/lobby`` and the ``lobby_state``
    event — so a key present for only two of them is a drift waiting to happen. Pinned as a set, not spot
    checks, because the failure mode is a key quietly disappearing rather than one holding a wrong value."""
    state = make_manager(tmp_path).lobby_state()
    assert {"banks", "framings", "models", "policies", "seat_kinds", "seat_names", "bank", "framing",
            "instance_id", "seats", "budget_usd", "running", "sid", "phase", "episode_id",
            "error"} <= set(state)
    assert state["seat_names"] == list(PERSONAS[:3])
    assert state["instance_id"] == "", '"" is how the lobby says "let the provider choose"'
    assert state["running"] is False and state["sid"] is None and state["error"] == ""


@needs_lane_a
def test_the_lobby_names_the_running_session_so_the_page_can_link_to_it(tmp_path):
    """Every per-session route is keyed by ``sid``, and the lobby is where a page that did not start the game
    finds it."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    running = manager.lobby_state()
    assert running["running"] is True and running["sid"] == session.sid
    play_out(session)
    assert manager.lobby_state()["running"] is False, "a finished session is not in the way of the next one"


def test_a_refused_edit_is_recorded_as_well_as_raised(tmp_path):
    """The caller answers 400 with the message, but a page that re-renders from the state it was handed has
    nowhere else to read the refusal from — so it rides along until the next edit is accepted."""
    manager = make_manager(tmp_path)
    with pytest.raises(ValueError):
        manager.update_lobby({"framing": "nope"})
    assert "unknown framing" in manager.lobby_state()["error"]
    assert manager.update_lobby({"budget_usd": 4.0})["error"] == ""


def test_a_single_seat_edit_takes_either_spelling_of_its_index(tmp_path):
    """``seat_idx`` is what the play page's swap dock calls it and ``index`` what the lobby calls it; both name
    the same seat, so both are read rather than making one page rename a field to match the other."""
    manager = make_manager(tmp_path)
    by_idx = manager.update_lobby({"seat_idx": 1, "seat": {"kind": "oracle", "policy": "bayes-rational"}})
    assert by_idx["seats"][1]["kind"] == "oracle"
    by_index = manager.update_lobby({"index": 2, "seat": {"kind": "oracle", "policy": "bayes-rational"}})
    assert by_index["seats"][2]["kind"] == "oracle"


def test_one_seat_can_be_edited_without_resending_the_lineup(tmp_path):
    """The seat cards send one card. A lobby with six seats should not have to round-trip all six to change one."""
    manager = make_manager(tmp_path)
    state = manager.update_lobby({"index": 1, "seat": {"kind": "oracle", "policy": "bayes-rational"}})
    assert [s["kind"] for s in state["seats"]] == ["rational", "oracle", "rational"]


@pytest.mark.parametrize("patch, message", [
    ({"bank": "nope"}, "unknown bank"),
    ({"framing": "nope"}, "unknown framing"),
    ({"seats": [{"kind": "telepath"}]}, "unknown seat kind"),
    ({"seats": [{"kind": "llm", "model_id": "gpt-nonexistent"}]}, "unknown model"),
    ({"seats": [{"kind": "llm", "model_id": "stub-free", "thinking": "on"}]}, "does not support thinking"),
    ({"seats": [{"kind": "rational", "policy": "vibes"}]}, "unknown policy"),
])
def test_an_impossible_configuration_is_refused_at_edit_time(tmp_path, patch, message):
    """Refused where the person can still see the form, not as a dead game two clicks later. The thinking-mode
    check is the one that earns its keep: a model that rejects a mode 400s mid-game and wastes the session."""
    with pytest.raises(ValueError, match=message):
        make_manager(tmp_path).update_lobby(patch)


def test_a_short_lineup_is_padded_to_the_games_actual_seat_count(tmp_path):
    """A bank may seat more parties than the lobby had cards for. Padding with the default computable seat is the
    only answer that still produces a playable table."""
    manager = make_manager(tmp_path)
    manager.update_lobby({"seats": [{"kind": "oracle", "policy": "bayes-rational"}]})
    seats = manager._seats_for(manager.provider.prepare("stub", "plain", None))
    assert [s.kind for s in seats] == ["oracle", "rational", "rational"]


# ----------------------------------------------------------------------------- lobby -> a real table --
@needs_lane_a
def test_each_seat_kind_becomes_the_participant_it_names(tmp_path):
    """The one translation the whole feature rests on: a lobby row becomes a participant of the right type, and
    ``rational`` versus ``oracle`` differ by exactly what the seat is allowed to know."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="rational", policy="bayes-rational"),
                              SeatConfig(kind="oracle", policy="bayes-rational"),
                              SeatConfig(kind="scripted", instructions="I am scripted.")], budget_usd=1.0)
    seats = session._router.seats
    assert isinstance(seats["Avery"], PolicyParticipant) and seats["Avery"].tables is None
    assert isinstance(seats["Blake"], PolicyParticipant) and seats["Blake"].tables is not None
    assert isinstance(seats["Casey"], ScriptedParticipant)
    play_out(session)


@needs_lane_a
def test_a_model_seat_is_built_by_the_provider_with_the_sessions_meter(tmp_path):
    """interlens never learns how to build a model seat. It hands the provider the thinking mode, the session's
    meter (so the cap actually binds) and the seat's private instructions, and takes back a participant."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="llm", model_id="stub-paid", thinking="on", instructions="Be terse."),
                              *kinds("rational", "rational")], budget_usd=1.0)
    (call,) = manager.provider.model_seats
    assert call["model_id"] == "stub-paid" and call["thinking"] == "on"
    assert call["meter"] is session.meter
    assert call["extra_instructions"] == "Be terse."
    play_out(session)


@needs_lane_a
def test_private_instructions_land_in_the_seats_own_private_context(tmp_path):
    """One labelled segment, folded in where the seat's own private material already goes — so the operator can
    recognize their override in the transcript and no scaffold had to be edited to add it."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="llm", model_id="stub-free", instructions="Hold out for the split."),
                              *kinds("rational", "rational")], budget_usd=None)
    context = session._router.seats["Avery"].private_context
    assert context and context[-1] == f"{INSTRUCTION_HEADER} Hold out for the split."
    play_out(session)


def test_an_override_is_appended_to_what_the_seat_already_reads():
    """Appended, never substituted: a scaffold's own private material is the seat's information, and an override
    that replaced it would silently change the game rather than add to it."""
    seat = ScriptedParticipant("x", ["hi"], private_context=("your sheet is private",))
    assert apply_private_instructions(seat, "Be terse.").private_context == (
        "your sheet is private", f"{INSTRUCTION_HEADER} Be terse.")


def test_an_empty_override_adds_no_segment():
    """A seat nobody typed instructions for must read exactly what it would have read without live play."""
    seat = ScriptedParticipant("x", ["hi"])
    assert apply_private_instructions(seat, "").private_context == ()
    assert apply_private_instructions(seat, "   ").private_context == ()


@needs_lane_a
def test_the_budget_cap_becomes_the_sessions_meter(tmp_path):
    """The cap the lobby typed is the ledger every metered participant charges, and the number the ``usage``
    event reports against."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"), budget_usd=3.5)
    assert session.meter.budget == 3.5
    play_out(session)
    usage = [data for _, kind, data in session._log if kind == events.USAGE]
    assert usage and all(u["cap_usd"] == 3.5 for u in usage)


def test_a_metered_seat_cannot_start_without_a_cap(tmp_path):
    """An uncapped session with an API seat is how one lobby click turns into a bill — and a live game with a
    person in it can idle for an hour with that seat configured."""
    manager = make_manager(tmp_path)
    manager.update_lobby({"seats": [{"kind": "llm", "model_id": "stub-paid"}, {"kind": "rational"},
                                    {"kind": "rational"}], "budget_usd": None})
    with pytest.raises(ValueError, match="needs a budget cap"):
        manager.start()


def test_an_unavailable_model_cannot_start(tmp_path):
    """Checked at START, not at boot: a key can appear between configuring the lobby and playing, and the reason
    the provider gave is what the operator needs to see."""
    manager = make_manager(tmp_path)
    manager.update_lobby({"seats": [{"kind": "llm", "model_id": "stub-gone"}, {"kind": "rational"},
                                    {"kind": "rational"}], "budget_usd": 1.0})
    with pytest.raises(ValueError, match="STUB_API_KEY is not set"):
        manager.start()


@needs_lane_a
def test_a_second_session_is_refused_while_one_is_running(tmp_path):
    """v1 holds one game at a time: budgets are per session, and a second concurrent game would double an API
    bill with no way to tell whose it was."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    # A finished session is not in the way; a running one is.
    manager._active.phase = "running"
    with pytest.raises(ValueError, match="already running"):
        manager.start()


# ------------------------------------------------------------------------------------ the event log --
@needs_lane_a
def test_the_log_is_a_monotonic_sequence_in_protocol_order(tmp_path):
    """The stream's shape: the episode is announced before any turn is committed, every turn lands, and the
    episode closes exactly once.

    ``turn_started`` for the opening turn precedes ``episode_started``, and that is not a defect to fix: the
    router announces a seat while its generation is in flight, and the engine does not mint an episode id until
    it persists the first wave. Announcing the seat late (or the episode with a fabricated id) would be the
    worse trade — the id reaches the browser before any turn is COMMITTED, which is what the client needs it
    for, since it answers ``episode_started`` by fetching the snapshot."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    seqs = [seq for seq, _, _ in session._log]
    assert seqs == sorted(seqs) == list(range(1, len(seqs) + 1))
    order = [kind for _, kind, _ in session._log]
    assert order.index(events.EPISODE_STARTED) < order.index(events.TURN_APPENDED)
    assert order[-1] == events.EPISODE_DONE
    assert order.count(events.EPISODE_STARTED) == 1
    assert order.count(events.EPISODE_DONE) == 1
    assert order.count(events.TURN_APPENDED) == len(session._rows) >= 3
    # Every turn was announced before it was committed, and by the seat that played it.
    started = [d["seat"] for _, k, d in session._log if k == events.TURN_STARTED]
    assert started == [r["seat"] for r in session._rows]


@needs_lane_a
def test_a_subscriber_replays_from_where_it_left_off(tmp_path):
    """The reconnect guarantee, at the session level: subscribing with a sequence number delivers everything
    after it and nothing before, which is what makes a reload mid-episode lossless."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    q = session.subscribe(2)
    replayed = [q.get_nowait()[0] for _ in range(q.qsize())]
    assert replayed == list(range(3, session.seq + 1))
    assert session.subscribe(session.seq).qsize() == 0
    session.unsubscribe(q)


@needs_lane_a
def test_a_stalled_subscriber_is_dropped_rather_than_stalling_the_game(tmp_path):
    """``broadcast`` runs on the engine thread, so a reader whose queue filled up must be droppable. A game that
    could be stalled by a browser that stopped reading is not a live game."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    full: queue.Queue = queue.Queue(maxsize=1)
    full.put_nowait("occupied")
    session._subscribers.append(full)
    session.broadcast(*events.error("just a notice"))
    assert full not in session._subscribers


# ------------------------------------------------------------------------------- the zero-drift gate --
@needs_lane_a
def test_the_streamed_rows_are_exactly_what_a_reload_rebuilds(tmp_path):
    """THE gate. The rows the session accumulated one turn at a time must equal, key for key, the rows a full
    ``episode_payload`` rebuild produces — which is what lets a live page push a streamed turn straight onto
    ``PAYLOAD.turns`` instead of re-fetching, and what makes a reload land on the same game it was watching."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "oracle", "rational"))
    play_out(session)
    rebuilt = session.snapshot()["payload"]["turns"]
    assert len(rebuilt) == len(session._rows) >= 3
    for i, row in enumerate(session._rows):
        assert row == rebuilt[i], f"streamed turn {i} differs from the row a reload rebuilds"


@needs_lane_a
def test_every_streamed_turn_carried_the_row_the_snapshot_holds(tmp_path):
    """And the rows actually went over the wire: the ``turn_appended`` events carry the same dicts, so a client
    that merged the stream holds what a reloading one fetches."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    snapshot = session.snapshot()
    streamed = [d["turn"] for _, k, d in session._log if k == events.TURN_APPENDED]
    assert streamed == snapshot["payload"]["turns"]
    # and every bubble that was streamed is character for character the one the reloaded page renders in that
    # slot — the same guarantee as the rows, for the half of the transcript that is server-rendered HTML
    transcript = viz_page._chat_bubbles(snapshot["payload"])
    bubbles = [d["bubble_html"] for _, k, d in session._log if k == events.TURN_APPENDED]
    assert bubbles and all(b in transcript for b in bubbles)


@needs_lane_a
def test_the_snapshot_is_renderable_before_a_single_turn_exists(tmp_path):
    """A human seat can be asked to move before any turn is played, and its dock needs the game — so ``/state``
    has to render from the moment the session starts, not from the first wave."""
    manager = make_manager(tmp_path)
    session = LiveSession("s0", manager.provider, manager.provider.prepare("stub", "plain", None),
                          kinds("rational", "rational", "rational"), tmp_path)
    snapshot = session.snapshot()
    assert snapshot["phase"] == "lobby" and snapshot["payload"]["turns"] == []
    assert [s["name"] for s in snapshot["payload"]["seats"]] == list(PERSONAS[:3])
    assert snapshot["payload"]["game"] is not None          # the geometry the dock builds its offer form from


# ---------------------------------------------------------------------------- the per-turn delta unit --
def test_a_retry_retroactively_unpublishes_the_attempt_it_superseded():
    """``published`` is a property of a turn's POSITION, not of the turn — so the delta builder re-derives the
    ledger over everything accumulated, and an earlier row flips to unpublished when its retry lands. This is the
    subtlety that would otherwise make a streamed transcript show text no other seat ever read."""
    episode = {"seats": [{"name": "Avery"}], "turns": [], "round_checkpoints": []}
    first = {"idx": 0, "round": 1, "phase": "turn", "seat": "Avery", "content": "oops", "parsed_action": {},
             "n_tokens_out": 5}
    retry = {**first, "idx": 1, "content": "fixed"}
    rows: list[dict] = []
    episode["turns"] = [first]
    assert turn_delta(episode, first, rows)["published"] is True
    episode["turns"] = [first, retry]
    assert turn_delta(episode, retry, rows)["published"] is True
    assert rows[0]["published"] is False, "the superseded attempt is still marked public"


def test_a_bubble_renders_from_the_seat_table_alone():
    """A streamed bubble is rendered before its turn joins the payload, so the renderer may read only the seats."""
    turn = {"idx": 0, "round": 1, "seat": "Avery", "action": {"atype": "none", "message": "hello"}}
    html = bubble_html({"seats": [{"name": "Avery", "party": 0}]}, turn)
    assert "hello" in html and "Avery" in html and "data-turnidx='0'" in html


def test_a_streamed_bubble_badges_a_swapped_seat_the_way_a_full_render_does():
    """The occupant badge marks a DEPARTURE from the seat's first recorded occupant, so the renderer derives
    that default from the transcript — which is why the session hands it the rows it has accumulated. Rendered
    against no transcript, every post-swap badge silently disappears, and the one thing a live page adds over a
    static one (you can see the seat changed hands) is gone."""
    rows = [{"idx": 0, "round": 1, "seat": "Avery", "occupant": "policy:bayes-rational",
             "action": {"atype": "none", "message": "mine"}},
            {"idx": 1, "round": 2, "seat": "Avery", "occupant": "oracle:bayes-rational",
             "action": {"atype": "none", "message": "now mine"}}]
    payload = {"seats": [{"name": "Avery", "party": 0}], "turns": rows}
    swapped = bubble_html(payload, rows[1])
    assert "now oracle:bayes-rational" in swapped
    assert swapped in viz_page._chat_bubbles(payload), "a streamed bubble must be the one a reload rebuilds"
    assert "now oracle" not in bubble_html({"seats": payload["seats"], "turns": []}, rows[1])


# ------------------------------------------------------------------------------- a person at the table --
@needs_lane_a
def test_a_human_seat_blocks_the_game_and_plays_the_move_it_is_given(tmp_path):
    """The whole human path end to end: the seat blocks, the session announces what may legally be done, a POST
    body becomes a move, and the turn is recorded as the person's — indistinguishable in FORM from a model's,
    which is exactly what makes a mixed game measurable."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="human", display_name="sid"), *kinds("rational", "rational")])
    wait_for(lambda: session.phase == "awaiting_human", what="the human seat to be asked")

    awaiting = session._awaiting
    assert awaiting["seat"] == "Avery" and awaiting["turn_idx"] == 0
    assert awaiting["legal"]["can_offer"] is True and awaiting["sheet"]["threshold"] >= 0.0
    assert isinstance(session._router.seats["Avery"], HumanParticipant)

    deal = {issue.name: issue.options[0] for issue in manager.provider.spec.space.issues}
    session.submit_human("Avery", {"action": "propose", "deal": deal, "message": "Here is my package.",
                                   "note": "opening high"})
    play_out(session)
    assert session._rows[0]["occupant"] == "human:sid"
    assert session._rows[0]["human_note"] == "opening high"
    assert session._rows[0]["action"]["atype"] == "propose"


@needs_lane_a
@pytest.mark.parametrize("display_name, occupant", [("sid", "human:sid"), ("", "human:player")])
def test_a_human_seat_is_built_under_the_name_its_occupant_label_uses(tmp_path, display_name, occupant):
    """A ``HumanParticipant`` stamps ``human:<its own name>`` on the turns it plays and the router does not
    overwrite a self-stamp, so the session MUST construct it with ``SeatConfig.occupant_detail()``. Any other
    spelling — including a plausible ``player{idx}`` fallback — makes one seat report two different occupants
    and its timeline unreadable. Pinned for the named case AND the unnamed one, since the fallback is exactly
    where the two spellings would drift apart."""
    manager = make_manager(tmp_path)
    config = SeatConfig(kind="human", display_name=display_name)
    session = start(manager, [config, *kinds("rational", "rational")])
    wait_for(lambda: session.phase == "awaiting_human", what="the human seat to be asked")
    assert session._router.seats["Avery"].occupant == config.occupant_label() == occupant
    assert session.occupants["Avery"] == occupant
    session.stop()
    play_out(session)


@needs_lane_a
def test_an_illegal_move_is_refused_and_the_seat_stays_blocked(tmp_path):
    """Nothing is enqueued on a rejection. The engine reads empty content as a well-formed no-op turn, so a
    submission that slipped through unvalidated would silently become the player passing."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="human", display_name="sid"), *kinds("rational", "rational")])
    wait_for(lambda: session.phase == "awaiting_human", what="the human seat to be asked")

    with pytest.raises(ValueError, match="P9"):
        session.submit_human("Avery", {"action": "accept", "offer_id": "P9"})
    with pytest.raises(ValueError, match="Choose an action"):
        session.submit_human("Avery", {"action": "", "message": "hi"})
    with pytest.raises(ValueError, match="not played by a person"):
        session.submit_human("Blake", {"action": "pass"})

    assert session.phase == "awaiting_human" and session._rows == []
    session.stop()
    play_out(session)


@needs_lane_a
def test_a_seat_cannot_change_hands_while_its_player_is_deciding(tmp_path):
    """v1 applies swaps between turns only. The person is already answering and the turn is theirs — taking it
    away mid-decision would either lose their move or play it under somebody else's occupant stamp."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="human", display_name="sid"), *kinds("rational", "rational")])
    wait_for(lambda: session.phase == "awaiting_human", what="the human seat to be asked")
    with pytest.raises(ValueError, match="mid-decision"):
        session.swap_seat(0, SeatConfig(kind="rational", policy="bayes-rational"))
    session.stop()
    play_out(session)


@needs_lane_a
def test_a_seat_that_is_not_waiting_can_be_swapped_and_the_swap_is_announced(tmp_path):
    """The other half of the same rule, and the event a page badges the new occupant from."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    session.swap_seat(1, SeatConfig(kind="oracle", policy="bayes-rational", display_name="mediator"))
    seq, kind, data = session._log[-1]
    assert kind == events.SEAT_SWAPPED and data["seat"] == "Blake" and data["seat_idx"] == 1
    assert data["from"] and data["to"]
    assert session._router.seats["Blake"].tables is not None


@needs_lane_a
def test_stopping_releases_a_waiting_player_and_is_idempotent(tmp_path):
    """A double-click on Stop must not raise, and a blocked seat must be released — otherwise the engine thread
    outlives the session forever, holding a person's turn open on a game nobody is watching."""
    manager = make_manager(tmp_path)
    session = start(manager, [SeatConfig(kind="human", display_name="sid"), *kinds("rational", "rational")])
    wait_for(lambda: session.phase == "awaiting_human", what="the human seat to be asked")
    session.stop()
    session.stop()
    play_out(session)
    done = [d for _, k, d in session._log if k == events.EPISODE_DONE]
    assert len(done) == 1 and done[0]["status"] == "stopped"


@needs_lane_a
def test_the_engine_thread_never_leaves_a_session_hanging(tmp_path):
    """Whatever route the episode ends by — played out, stopped, or an exception nobody predicted — the session
    closes itself out. A browser that only ever hears about waves would otherwise sit on a spinner forever."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    session._thread.join(timeout=TIMEOUT)
    assert not session._thread.is_alive()
    assert session.phase == "done" and session.episode_id


@needs_lane_a
def test_the_episode_is_on_disk_and_the_stream_never_ran_ahead_of_it(tmp_path):
    """The stream is a view of the file, never a replacement for it: the run directory holds the episode, with
    every turn the stream reported."""
    manager = make_manager(tmp_path)
    session = start(manager, kinds("rational", "rational", "rational"))
    play_out(session)
    written = list(tmp_path.rglob(f"{session.episode_id}.json"))
    assert len(written) == 1
    stored = json.loads(written[0].read_text())
    assert len(stored["turns"]) == len(session._rows)
    # and the durable record is the one the payload builder reads: rebuilding from disk gives the same rows
    rebuilt = episode_payload(stored, manager.provider.instance.to_json(), reconstruct=False)
    assert [t["idx"] for t in rebuilt["turns"]] == [r["idx"] for r in session._rows]


@needs_lane_a
def test_two_sessions_do_not_share_a_lock_or_a_log(tmp_path):
    """Sessions are independent by construction — the manager holds one at a time, but the objects must not have
    started sharing state through a mutable default."""
    manager = make_manager(tmp_path)
    first = start(manager, kinds("rational", "rational", "rational"))
    play_out(first)
    manager._active = None
    second = manager.start()
    play_out(second)
    assert first.sid != second.sid
    assert first._log is not second._log and first._rows is not second._rows
    assert first.episode_id != second.episode_id


@needs_lane_a
def test_broadcast_is_safe_to_call_from_several_threads(tmp_path):
    """``broadcast`` is called from the engine thread while HTTP threads subscribe and unsubscribe, so the
    sequence numbering has to hold under contention: no duplicates, no gaps."""
    manager = make_manager(tmp_path)
    session = LiveSession("s1", manager.provider, manager.provider.prepare("stub", "plain", None),
                          kinds("rational", "rational", "rational"), tmp_path)
    threads = [threading.Thread(target=lambda: [session.broadcast(*events.error(f"n{i}")) for i in range(50)])
               for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [seq for seq, _, _ in session._log] == list(range(1, 201))

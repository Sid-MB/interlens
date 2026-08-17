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
# [implement: live-play/laneA] 2026-08-16
"""``LiveSeatRouter``: a seat changes hands mid-episode, and the transcript remembers who played what.

Two properties are worth the machinery and both are asserted end to end rather than on the class in isolation:

1. **A swap takes effect on the next turn and nothing restarts.** The episode keeps running; only the table
   entry changed. The swap here is fired from the engine's own post-save observer, which is exactly where the
   live server fires it from — between turns, on the engine thread.
2. **Attribution is per turn, not per seat.** ``TurnRecord.occupant`` records who took each turn, survives to
   disk, and reaches the visualizer payload the badge is drawn from. A seat table alone cannot express this:
   read after the fact it only says who holds the seat now.

The concurrency test is the one that would fail silently in production. ``generate`` runs on an engine worker
thread and ``swap`` on an HTTP thread, so the participant and its label must be read TOGETHER under the lock —
read separately, a swap landing between the two reads stamps one occupant's label on another's turn, which is
the single failure that would make the occupant record a lie rather than merely absent.
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import threading

import pytest

from interlens.arena.engine import EpisodePool
from interlens.arena.live.provider import SeatConfig
from interlens.arena.live.router import LiveSeatRouter
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.schema import PERSONAS, EpisodeStore, Instance, new_id
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.viz import episode as viz_episode
from interlens.message import Message

TARGET = {"Site": "North", "Fund": "High"}


def game(rounds: int = 2) -> GameSpec:
    space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
    sheets = (ScoreSheet("Alpha", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0),
              ScoreSheet("Beta", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=5.0))
    return GameSpec(space, sheets, rounds=rounds, info="full", chat=True, proposer=0, veto=None, min_accept=None)


def instance_of(spec: GameSpec) -> Instance:
    return Instance(new_id("live-router-test"), ScorableNegotiation.name, 0, 0,
                    payload=spec.to_json(), ceiling=1.0, floor=0.0, solution={})


class Seat:
    """A model-free seat that never closes early: it re-tables the target package every turn and only casts a
    vote when the forced final asks for one, so an episode runs long enough for a swap to be visible.

    ``stamp`` optionally has it claim its own occupant label, which is how a ``HumanParticipant`` behaves."""

    self_role, others_role = "assistant", "user"
    system_prompt, private_context = None, ()

    def __init__(self, name: str, stamp: str | None = None):
        self.name = name
        self.stamp = stamp
        self.turns = 0

    def generate(self, view, *, seat=None, **kwargs):
        self.turns += 1
        final = re.search(r"FINAL up/down vote on (P\d+)", view[-1]["content"])
        obj = ({"action": "accept", "offer_id": final.group(1)} if final
               else {"action": "propose", "deal": TARGET})
        metadata = {"played_by": self.name}
        if self.stamp is not None:
            metadata["occupant"] = self.stamp
        return Message(self.name, "```json\n" + json.dumps(obj) + "\n```", metadata)


def play(tmp_path, table, spec=None, **kwargs):
    """One real episode through the real pool. Returns ``(episode, store)``."""
    spec = spec or game()
    store = EpisodeStore(tmp_path)
    ep = asyncio.run(EpisodePool(store).run_episode(ScorableNegotiation(), instance_of(spec), "moves_chat",
                                                    table, seed=0, **kwargs))
    return ep, store


# ------------------------------------------------------------------------------------ the hot swap --
def test_a_swap_mid_episode_changes_who_plays_the_next_turn(tmp_path):
    """The point of the whole class: the engine holds the TABLE, so replacing an entry hands the seat over
    without restarting anything — and the turns before and after are attributed to different occupants."""
    table = LiveSeatRouter({PERSONAS[0]: Seat("first"), PERSONAS[1]: Seat("other")},
                           labels={PERSONAS[0]: "policy:first", PERSONAS[1]: "policy:other"})
    swapped: list = []

    def swap_after_the_first_turn(ep):
        if len(ep.turns) == 1 and not swapped:
            swapped.append(table.swap(PERSONAS[0], Seat("second"), "human:sid"))

    ep, store = play(tmp_path, table, on_wave=swap_after_the_first_turn)
    assert ep.status == "done"
    assert swapped == ["policy:first"], "swap must report the occupant it replaced"

    seat0 = [t.occupant for t in ep.turns if t.seat == PERSONAS[0]]
    assert len(seat0) >= 2, "the episode was too short to show a swap"
    assert seat0[0] == "policy:first" and set(seat0[1:]) == {"human:sid"}
    # the other seat never changed hands, and its label never moved
    assert {t.occupant for t in ep.turns if t.seat == PERSONAS[1]} == {"policy:other"}


def test_the_occupant_sequence_survives_to_disk_and_into_the_payload(tmp_path):
    """The stamp is only worth anything if it reaches the page: episode -> JSON -> render payload, unbroken."""
    spec = game()
    table = LiveSeatRouter({PERSONAS[0]: Seat("first"), PERSONAS[1]: Seat("other")},
                           labels={PERSONAS[0]: "api:claude-fable-5", PERSONAS[1]: "policy:bayes-rational"})
    done: list = []

    def swap_once(ep):
        if len(ep.turns) == 1 and not done:
            done.append(table.swap(PERSONAS[0], Seat("second"), "human:sid"))

    ep, store = play(tmp_path, table, spec=spec, on_wave=swap_once)
    stored = json.loads(store.path(ep).read_text())
    sequence = [t["occupant"] for t in stored["turns"]]
    assert sequence == [t.occupant for t in ep.turns]

    payload = viz_episode.episode_payload(stored, instance_of(spec).to_json())
    assert [t["occupant"] for t in payload["turns"]] == sequence
    assert "human:sid" in sequence and "api:claude-fable-5" in sequence


def test_a_seat_with_no_label_records_no_occupant(tmp_path):
    """Absent, not guessed. A table that was never told who is in a seat must not invent an attribution."""
    table = LiveSeatRouter({PERSONAS[0]: Seat("a"), PERSONAS[1]: Seat("b")},
                           labels={PERSONAS[0]: "policy:a"})
    ep, _ = play(tmp_path, table)
    assert {t.occupant for t in ep.turns if t.seat == PERSONAS[1]} == {None}
    assert {t.occupant for t in ep.turns if t.seat == PERSONAS[0]} == {"policy:a"}


def test_a_participant_that_names_itself_keeps_its_own_attribution(tmp_path):
    """A ``HumanParticipant`` stamps ``human:<player>`` itself, and it knows better than the table who is
    actually at the keyboard — so the table must not overwrite it."""
    table = LiveSeatRouter({PERSONAS[0]: Seat("a", stamp="human:sid"), PERSONAS[1]: Seat("b")},
                           labels={PERSONAS[0]: "human:whoever", PERSONAS[1]: "policy:b"})
    ep, _ = play(tmp_path, table)
    assert {t.occupant for t in ep.turns if t.seat == PERSONAS[0]} == {"human:sid"}


def test_swapping_an_unknown_seat_raises(tmp_path):
    table = LiveSeatRouter({PERSONAS[0]: Seat("a")}, labels={PERSONAS[0]: "policy:a"})
    with pytest.raises(KeyError):
        table.swap("Nobody", Seat("b"), "policy:b")


def test_occupants_reports_every_seat_including_the_unlabelled_ones():
    """What ``hello`` sends a page that just connected, so it badges seats without replaying the swap history."""
    table = LiveSeatRouter({PERSONAS[0]: Seat("a"), PERSONAS[1]: Seat("b")}, labels={PERSONAS[0]: "policy:a"})
    assert table.occupants() == {PERSONAS[0]: "policy:a", PERSONAS[1]: None}
    table.swap(PERSONAS[1], Seat("c"), "human:sid")
    assert table.occupants() == {PERSONAS[0]: "policy:a", PERSONAS[1]: "human:sid"}
    table.swap(PERSONAS[0], Seat("d"), None)
    assert table.occupants()[PERSONAS[0]] is None


# --------------------------------------------------------------------------------- the turn-start hook --
def test_the_hook_fires_before_dispatch_with_the_occupant_that_will_play(tmp_path):
    """It fires while the call is in flight — the only moment "Blake is thinking" is both true and useful — so
    it must carry the label of the occupant about to answer, not the one that just finished."""
    seen: list = []
    table = LiveSeatRouter({PERSONAS[0]: Seat("a"), PERSONAS[1]: Seat("b")},
                           labels={PERSONAS[0]: "policy:a", PERSONAS[1]: "policy:b"},
                           on_turn_start=lambda seat, occupant: seen.append((seat, occupant)))
    ep, _ = play(tmp_path, table)
    assert len(seen) == len(ep.turns)
    assert seen == [(t.seat, t.occupant) for t in ep.turns]


def test_a_broken_hook_cannot_kill_the_game(tmp_path):
    """A "who is thinking" indicator is a viewer, not a hook: if the browser-facing side raises, the negotiation
    it is only watching must play on."""
    calls: list = []

    def explode(seat, occupant):
        calls.append(seat)
        raise RuntimeError("the indicator exploded")

    table = LiveSeatRouter({PERSONAS[0]: Seat("a"), PERSONAS[1]: Seat("b")},
                           labels={PERSONAS[0]: "policy:a"}, on_turn_start=explode)
    ep, _ = play(tmp_path, table)
    assert ep.status == "done" and calls
    assert {t.occupant for t in ep.turns if t.seat == PERSONAS[0]} == {"policy:a"}


# ------------------------------------------------------------------------------------- under contention --
def test_a_swap_racing_a_turn_never_mislabels_it():
    """The failure this class exists to prevent. Every participant records the name it played under; the router
    stamps the label it snapshotted. If the two were read separately, a swap landing between the reads would put
    one occupant's label on another's turn — so the invariant is that they always agree, not merely that neither
    is missing."""
    seat = PERSONAS[0]
    table = LiveSeatRouter({seat: Seat("occupant-0")}, labels={seat: "policy:occupant-0"})
    view = [{"role": "user", "content": "your turn"}]
    stop = threading.Event()
    mismatched: list = []
    rng = random.Random(0)

    def swapper():
        n = 1
        while not stop.is_set():
            table.swap(seat, Seat(f"occupant-{n}"), f"policy:occupant-{n}")
            n += 1

    def player():
        for _ in range(400):
            message = table.generate(view, seat=seat)
            if message.metadata["occupant"] != f"policy:{message.metadata['played_by']}":
                mismatched.append(dict(message.metadata))
            if rng.random() < 0.1:
                threading.Event().wait(0.001)

    swap_thread = threading.Thread(target=swapper, daemon=True)
    players = [threading.Thread(target=player, daemon=True) for _ in range(4)]
    swap_thread.start()
    for thread in players:
        thread.start()
    for thread in players:
        thread.join(30)
    stop.set()
    swap_thread.join(5)
    assert not mismatched, mismatched[:3]
    assert table.occupants()[seat] is not None            # and the table is intact, not torn


# ---------------------------------------------------------------- one place the spelling is decided --
@pytest.mark.parametrize("config, expected", [
    (SeatConfig(kind="llm", model_id="claude-fable-5"), "api:claude-fable-5"),
    (SeatConfig(kind="rational", policy="bayes-rational"), "policy:bayes-rational"),
    (SeatConfig(kind="oracle", policy="fairness-oracle"), "oracle:fairness-oracle"),
    (SeatConfig(kind="human", display_name="sid"), "human:sid"),
    (SeatConfig(kind="scripted"), "scripted:scripted"),
    # display_name overrides the detail for every kind, so an operator can name a seat whatever they like
    (SeatConfig(kind="llm", model_id="claude-fable-5", display_name="the buyer"), "api:the buyer"),
    # and a kind with nothing to identify it still produces a label rather than a colon and a blank
    (SeatConfig(kind="llm"), "api:llm"),
])
def test_the_occupant_label_is_derived_in_exactly_one_place(config, expected):
    """The router's stamp, the ``seat_swapped`` event's from/to and the transcript badge all read this one
    function. Three spellings of the same seat would make an occupant timeline unreadable."""
    assert config.occupant_label() == expected


def test_a_human_seat_and_its_config_agree_about_who_is_playing():
    """A ``HumanParticipant`` stamps its OWN name (it knows who is at the keyboard), so the session must build it
    from ``occupant_detail`` or one seat would report two different players for one person."""
    from interlens.arena.live.human import HumanParticipant

    config = SeatConfig(kind="human", display_name="sid")
    human = HumanParticipant(config.occupant_detail(), 0, game().sheets[0], game().space, 2,
                             publisher=lambda kind, data: None)
    assert human.occupant == config.occupant_label() == "human:sid"


def test_a_missing_seat_identity_still_raises_through_the_lock():
    """Inherited behaviour that must survive the override: guessing the seat from the prompt text is how a table
    silently breaks whenever the wording changes, so a missing seat is an error."""
    table = LiveSeatRouter({PERSONAS[0]: Seat("a")})
    with pytest.raises(ValueError, match="seat identity"):
        table.generate([{"role": "user", "content": "x"}])
    with pytest.raises(KeyError):
        table.generate([{"role": "user", "content": "x"}], seat="Nobody")

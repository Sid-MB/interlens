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
"""The contracts live play is built on, pinned before the pieces that use them exist.

Four things have to hold, and each is something the rest of the feature quietly assumes:

1. the engine's ``on_wave`` observer fires AFTER the episode is on disk, once per wave and once at the end, and
   changes nothing about the episode when it is absent (or when it raises);
2. ``TurnRecord`` carries who played the turn, round-trips it, and still loads episodes recorded before the
   field existed;
3. the SSE frame format is what the browser's EventSource parser expects;
4. the two visualizer functions the live path streams through — ``_turn_payload`` and ``_chat_bubble`` — are the
   SAME ones the full page is built from, so a streamed turn and a reloaded one cannot disagree.

The last is the one worth the trouble: it is asserted as an identity against a full ``episode_payload`` rebuild
rather than against a golden string, so it keeps holding as the pages evolve.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
import subprocess
import sys

import pytest

from interlens.arena import EpisodePool, EpisodeStore
from interlens.arena.live import events
from interlens.arena.schema import TurnRecord
from interlens.arena.scenarios import InfoRelay
from interlens.arena.viz import episode as viz_episode
from interlens.arena.viz import page as viz_page
from interlens.message import Message
from interlens.participant import Participant

# The visualizer suite already builds a scored negotiation episode with a full oracle stack — exactly the shape
# the refactor claims must survive. Reusing its fixtures rather than rebuilding one keeps the two suites pinned
# to the same episode, so a change that quietly altered the payload would fail both.
from .test_arena_viz import _instance, _run

# Fields that differ between two runs of the same episode for reasons that are not behaviour: a uuid4 id and two
# wall-clock stamps. Everything else must match exactly for the "on_wave changes nothing" claim to mean anything.
NONDETERMINISTIC = ("episode_id", "started_at", "ended_at")


class _Seat(Participant):
    """A scripted seat: notes on a normal turn, the gold answer when the scaffold asks to finalize."""

    def __init__(self, answer):
        self.name = "scripted"
        self.answer = answer

    def generate(self, view, *, max_new_tokens=None, **kwargs):
        last = view[-1]["content"]
        finalizing = any(m in last for m in ("FINAL BINDING", "You MUST now submit", "RIGHT NOW",
                                             "Token budget reached", "Reply with ONLY"))
        return Message(self.name, self.answer if finalizing else "Here is what my notes say.",
                       {"n_tokens": 10, "n_tokens_in": 90})


def _play(tmp_path, instance=None, **kwargs):
    """One scripted relay episode through the real pool. Returns ``(episode, store)``.

    ``instance`` is passed in when two runs are to be compared: instance ids are uuid-random, so two separately
    generated instances differ in a field that has nothing to do with what is being tested."""
    scen = InfoRelay()
    inst = instance if instance is not None else scen.generate_instance(0, 11)
    seat = _Seat(f'```json\n{{"answer": {inst.payload["gold"]}}}\n```')
    store = EpisodeStore(tmp_path)
    ep = asyncio.run(EpisodePool(store).run_episode(scen, inst, "team", seat, cfg={"cell": "base"}, **kwargs))
    return ep, store


def _comparable(ep) -> dict:
    """An episode's record with the nondeterministic fields dropped."""
    return {k: v for k, v in ep.to_json().items() if k not in NONDETERMINISTIC}


@pytest.fixture(scope="module")
def episode():
    """A scored negotiation episode and its instance — the visualizer suite's own fixture, rebuilt here because
    a module-scoped fixture is not shared across test files."""
    inst, cfg = _instance()
    return _run(inst, cfg)


@pytest.fixture(scope="module")
def payload(episode):
    return viz_episode.episode_payload(*episode)


# ------------------------------------------------------------------------------- the wave observer --
def test_on_wave_fires_once_per_wave_and_once_at_the_end(tmp_path):
    """One call per persisted wave plus one for the finalized episode — the cadence a live stream is built on."""
    saw = []

    def observe(ep):
        saw.append((len(ep.turns), ep.status))

    ep, _ = _play(tmp_path, on_wave=observe)
    assert ep.status == "done"
    assert len(saw) >= 2                                     # at least one wave, then the finalize call
    # Turn counts never go backwards, and the last call is the finalized episode carrying every turn.
    assert [n for n, _ in saw] == sorted(n for n, _ in saw)
    assert saw[-1] == (len(ep.turns), "done")
    # Every call but the last one is mid-episode: the episode is not yet finalized when a wave is announced.
    assert all(status != "done" for _, status in saw[:-1])


def test_on_wave_is_called_only_after_the_episode_is_on_disk(tmp_path):
    """The ordering the whole streaming design rests on: an observer can never show a turn a reader reloading
    the page would not find, because the save has already happened when it is called."""
    store = EpisodeStore(tmp_path)
    on_disk = []

    def observe(ep):
        stored = json.loads(store.path(ep).read_text())
        on_disk.append((len(stored["turns"]), len(ep.turns)))

    ep, _ = _play(tmp_path, on_wave=observe)
    assert on_disk, "observer never fired"
    assert all(stored == live for stored, live in on_disk), on_disk


def test_the_episode_is_unchanged_by_the_presence_of_an_observer(tmp_path):
    """A no-op observer must cost the episode nothing — same turns, same outcome, same usage, byte for byte."""
    inst = InfoRelay().generate_instance(0, 11)
    plain, _ = _play(tmp_path / "plain", inst)
    observed, _ = _play(tmp_path / "observed", inst, on_wave=lambda ep: None)
    assert _comparable(plain) == _comparable(observed)


def test_a_broken_observer_cannot_kill_the_episode(tmp_path, caplog):
    """A viewer is not a hook. If it raises, the exception is logged and the game plays on — otherwise a bug in
    a browser-facing broadcaster would take down the run it is only watching."""
    calls = []

    def observe(ep):
        calls.append(len(ep.turns))
        raise RuntimeError("the viewer exploded")

    inst = InfoRelay().generate_instance(0, 11)
    clean, _ = _play(tmp_path / "clean", inst)
    ep, _ = _play(tmp_path / "broken", inst, on_wave=observe)
    assert ep.status == "done"
    assert len(calls) >= 2
    assert _comparable(clean) == _comparable(ep)
    assert "the viewer exploded" in caplog.text or "observer raised" in caplog.text


# ---------------------------------------------------------------------------- occupant attribution --
def test_record_turn_stamps_the_occupant_and_the_private_note(tmp_path):
    """The engine takes both off the message metadata, so a router or a human seat can attribute a turn without
    the engine knowing anything about live play."""

    class Stamped(_Seat):
        def generate(self, view, *, max_new_tokens=None, **kwargs):
            msg = super().generate(view, max_new_tokens=max_new_tokens, **kwargs)
            msg.metadata.update({"occupant": "human:sid", "human_note": "hold out for the split"})
            return msg

    scen = InfoRelay()
    inst = scen.generate_instance(0, 11)
    seat = Stamped(f'```json\n{{"answer": {inst.payload["gold"]}}}\n```')
    ep = asyncio.run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", seat))
    assert ep.turns and all(t.occupant == "human:sid" for t in ep.turns)
    assert all(t.human_note == "hold out for the split" for t in ep.turns)
    # and it survives the round trip to disk, which is what the payload and the badge read
    stored = json.loads(EpisodeStore(tmp_path).path(ep).read_text())
    assert {t["occupant"] for t in stored["turns"]} == {"human:sid"}


def test_a_normal_turn_records_no_occupant(tmp_path):
    """Absent, not guessed: a batch-run episode has one occupant throughout and it is recorded in ``seats``."""
    ep, _ = _play(tmp_path)
    assert all(t.occupant is None and t.human_note is None for t in ep.turns)


def test_turn_record_round_trips_the_new_fields_and_old_records_still_load():
    """Forward and backward: a record written now round-trips, and one written before these fields existed loads
    with them as ``None`` rather than failing."""
    turn = TurnRecord(idx=0, round=1, phase="propose", seat="Avery", content="hi", parsed_action={}, parse_ok=True,
                      occupant="policy:bayes-rational", human_note="note")
    back = TurnRecord.from_json(json.loads(json.dumps(turn.__dict__)))
    assert back.occupant == "policy:bayes-rational" and back.human_note == "note"

    legacy = {"idx": 0, "round": 1, "phase": "propose", "seat": "Avery", "content": "hi",
              "parsed_action": {}, "parse_ok": True}
    old = TurnRecord.from_json(legacy)
    assert old.occupant is None and old.human_note is None


# --------------------------------------------------------------------------------- the SSE protocol --
def test_format_sse_frames_an_event_the_way_eventsource_reads_it():
    frame = events.format_sse(7, events.TURN_STARTED, {"seat": "Avery"}).decode()
    assert frame.startswith("id: 7\nevent: turn_started\ndata: ")
    assert frame.endswith("\n\n")                                  # the blank line that terminates a frame
    body = frame.split("data: ", 1)[1].rstrip("\n")
    assert json.loads(body) == {"seat": "Avery"}


def test_a_frame_body_is_always_one_line():
    """A literal newline inside ``data`` would be read as a field break and split one event into two, so prose
    with line breaks in it — which every negotiation message has — must come out escaped."""
    frame = events.format_sse(1, events.TURN_APPENDED, {"msg": "line one\nline two\r\n"}).decode()
    assert len(frame.rstrip("\n").splitlines()) == 3               # id, event, data — and nothing else
    assert json.loads(frame.split("data: ", 1)[1]) == {"msg": "line one\nline two\r\n"}


def test_unicode_travels_unescaped():
    """The transcript is UTF-8 prose; escaping it would triple the size of every frame for no benefit."""
    frame = events.format_sse(1, events.TURN_APPENDED, {"msg": "über — ok"}).decode()
    assert "über — ok" in frame


@pytest.mark.parametrize("builder, args", [
    (events.hello, ("s1", 0, "lobby", {})),
    (events.lobby_state, ("bank", "framing", "inst", [], 2.0)),
    (events.episode_started, ("ep-1",)),
    (events.turn_started, (0, 1, "propose", "Avery", 0, "human:sid")),
    (events.turn_appended, ({"idx": 0}, "<div></div>", 1)),
    (events.awaiting_human, ("Avery", 0, 0, 1, "propose", {}, {}, {}, 8)),
    (events.input_rejected, ("Avery", "no such offer")),
    (events.seat_swapped, ("Avery", 0, "api:x", "human:sid", 3)),
    (events.usage, (10, 20, 0.5, 2.0, False)),
    (events.episode_done, ("done", {})),
    (events.error, ("boom",)),
])
def test_every_builder_returns_a_declared_type_and_a_json_safe_body(builder, args):
    kind, data = builder(*args)
    assert kind in events.EVENT_TYPES
    json.loads(events.format_sse(1, kind, data).decode().split("data: ", 1)[1])


def test_the_protocol_has_a_builder_for_every_event_type():
    """One source of truth means no event type without a builder — a hand-built dict is how the two halves of
    the protocol start to drift."""
    built = {builder(*args)[0] for builder, args in [
        (events.hello, ("s", 0, "lobby", {})), (events.lobby_state, ("b", "f", "i", [], 1.0)),
        (events.episode_started, ("e",)), (events.turn_started, (0, 1, "p", "A", 0, None)),
        (events.turn_appended, ({}, "", 0)), (events.awaiting_human, ("A", 0, 0, 1, "p", {}, {}, {}, 8)),
        (events.input_rejected, ("A", "r")), (events.seat_swapped, ("A", 0, None, "t", 0)),
        (events.usage, (0, 0, 0.0, None, False)), (events.episode_done, ("done", {})),
        (events.error, ("m",))]}
    assert built == set(events.EVENT_TYPES)


# ------------------------------------------------------------------- the factored visualizer units --
def test_a_single_bubble_is_exactly_what_the_transcript_joins(payload):
    """``_chat_bubble`` is the unit ``_chat_bubbles`` is built from — pinned as an identity so a live page
    streaming one bubble renders precisely what a full page rebuild would put in that slot."""
    rows = [t for t in payload["turns"] if t.get("published", True)]
    joined = "".join(viz_page._chat_bubble(payload, t) for t in rows)
    assert viz_page._chat_bubbles(payload) == f"<div class='chatlog' id='chatlog'>{joined}</div>"


def test_the_bubble_renderer_needs_only_the_seat_table(payload):
    """A streamed bubble is rendered before its turn joins the payload, so the renderer must not read
    ``payload["turns"]`` — pinned by rendering against a payload with the turns removed."""
    turn = next(t for t in payload["turns"] if t.get("published", True))
    without = {**payload, "turns": []}
    assert viz_page._chat_bubble(without, turn) == viz_page._chat_bubble(payload, turn)


def _incremental_rows(ep: dict, inst: dict) -> list[dict]:
    """Rebuild an episode's payload rows the way a LIVE session must: one turn at a time, each through
    ``_turn_payload``, re-running ``public_ledger`` over everything accumulated so far.

    The ledger pass is not optional and is the subtlety a delta builder has to get right. ``published``,
    ``offer_id`` and ``standing_deal_index`` are not properties of a turn — they are properties of the turn's
    position in the sequence, and a retry can flip an EARLIER turn's ``published`` to False after the fact. So a
    live builder appends the new row and re-derives the ledger over the accumulated list; it is a few dozen rows
    of pure Python per turn, against an engine turn that just spent seconds in a model call."""
    geo = viz_episode.GameGeometry.from_instance(inst)
    kinds = viz_episode.seat_kinds(ep, None)
    oracles = viz_episode._oracle_records(ep, None)
    seat_party = {s.get("name"): i for i, s in enumerate(ep.get("seats") or [])}
    fabricated = {row["idx"]: row for row in viz_episode.gen_failures(ep)}

    rows, seen = [], set()
    for i, t in enumerate(ep["turns"]):
        slot = (t.get("round"), t.get("phase"), t.get("seat"))
        is_retry = slot in seen
        seen.add(slot)
        rows.append(viz_episode._turn_payload(t, int(t.get("idx", i)), is_retry=is_retry, geo=geo, kinds=kinds,
                                              oracles=oracles, seat_party=seat_party, rebuilt={},
                                              fabricated=fabricated))
        viz_episode.public_ledger(rows)          # annotates in place; re-derived because a retry rewrites history
    return rows


def test_a_per_turn_row_is_identical_to_the_full_payload_rebuild(episode, payload):
    """The zero-drift guarantee: rows built one turn at a time reproduce, key for key, the rows a whole
    ``episode_payload`` rebuild produces. This is what lets a live page push a streamed turn straight onto
    ``PAYLOAD.turns`` instead of re-fetching the episode."""
    rows = _incremental_rows(*episode)
    assert len(rows) == len(payload["turns"])
    for i, row in enumerate(rows):
        assert row == payload["turns"][i], f"turn {i} differs from its full-payload row"


def test_the_payload_carries_the_occupant_through_to_the_page(episode):
    """The stamp has to survive the last hop — episode JSON to render payload — or the transcript has nothing to
    badge a swapped seat with."""
    ep, inst = episode
    stamped = json.loads(json.dumps(ep))
    stamped["turns"][0]["occupant"] = "human:sid"
    stamped["turns"][0]["human_note"] = "private"
    rendered = viz_episode.episode_payload(stamped, inst)
    assert rendered["turns"][0]["occupant"] == "human:sid"
    assert rendered["turns"][0]["human_note"] == "private"
    assert all(t["occupant"] is None for t in rendered["turns"][1:])


# ------------------------------------------------------------------------------------ the skeleton --
def test_the_live_package_imports_without_the_model_stack():
    """The live server is a CPU entry point like the visualizer: importing it must not drag in torch, or the
    lobby takes ten seconds to open on a machine that has no GPU to use anyway."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys, interlens.arena.live; print([m for m in sys.modules if m in ('torch', 'transformers')])"],
        capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout


def test_every_stub_names_the_lane_that_owns_it():
    """The skeleton exists to keep four parallel lanes off each other's files, so an unimplemented entry point
    must say WHOSE it is — a bare ``NotImplementedError`` in a package four people are building at once tells a
    reader nothing about who to ask."""
    from interlens.arena import live
    from interlens.arena.live import human, lobby_page, payload, play_page, provider, router, server, session

    unnamed = []
    for module in (live, provider, human, router, session, server, payload, lobby_page, play_page):
        for line in inspect.getsource(module).splitlines():
            if "raise NotImplementedError" in line and not re.search(r'NotImplementedError\("live-play lane \w',
                                                                     line):
                unnamed.append(f"{module.__name__}: {line.strip()}")
    assert not unnamed, unnamed

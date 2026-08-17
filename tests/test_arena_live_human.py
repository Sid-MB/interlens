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
"""``HumanParticipant``: a person plays a seat, and the transcript cannot tell.

The claim under test, and the reason live play is worth building at all, is INDISTINGUISHABILITY: a turn a
person submits through a browser form must be the same bytes a model or a policy seat would have produced for
the same move. So the assertions here are identities against ``arena.actions.action_message`` and round trips
through ``arena.actions.parse_action`` — the renderer and the parser the rest of the arena uses — not golden
strings that would drift.

The other half is the validation boundary. The engine reads an empty turn as a well-formed no-op, so an
unvalidated submission would silently become the player passing. Every refusal below therefore asserts two
things: that it raised, and that NOTHING was enqueued — the seat is still waiting, and the form is still open.

Views are the real thing: they come out of ``ScorableNegotiation`` itself rather than being hand-written, so the
``negotiation_state`` block the participant parses is the block the scenario actually emits.
"""
from __future__ import annotations

import asyncio
import json
import queue
import re
import threading

import pytest

from interlens.arena.actions import Accept, Pass, Propose, Walk, action_message, parse_action
from interlens.arena.engine import EpisodePool
from interlens.arena.live.human import (FINAL_PROPOSAL, FINAL_VOTE, TURN, HumanParticipant, PendingRequest,
                                        SessionStopped, build_human_message, legal_actions, phase_of)
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.strategies import NegotiationState
from interlens.arena.schema import PERSONAS, EpisodeStore, Instance, new_id
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.table import SeatRouter

TARGET = {"Site": "North", "Fund": "High"}
PROPOSE = "```json\n" + json.dumps({"action": "propose", "deal": TARGET}) + "\n```"


def two_party_game(rounds: int = 2) -> GameSpec:
    """A 2-party game whose only mutually acceptable package is (North, High): Alpha scores 16 on it and Beta 6,
    against thresholds of 5 each, so a deal is reachable and nothing else is."""
    space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
    sheets = (ScoreSheet("Alpha", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0),
              ScoreSheet("Beta", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=5.0))
    return GameSpec(space, sheets, rounds=rounds, info="full", chat=True, proposer=0, veto=None, min_accept=None)


def instance_of(spec: GameSpec) -> Instance:
    return Instance(new_id("live-human-test"), ScorableNegotiation.name, 0, 0,
                    payload=spec.to_json(), ceiling=1.0, floor=0.0, solution={})


def with_one_offer(spec: GameSpec):
    """Step the real scenario until seat 1 is being asked to move with one live offer (``P1``) on the table.

    Returns ``(scenario, state, request)``. Everything downstream reads the request's own view, so the
    ``negotiation_state`` block under test is the scenario's, not a fixture's idea of one."""
    scen = ScorableNegotiation()
    st = scen.make_state(instance_of(spec), "moves_chat", seed=0)
    opener = scen.next_requests(st)[0]
    scen.apply(st, opener, PROPOSE)
    return scen, st, scen.next_requests(st)[0]


def human_for(spec: GameSpec, si: int, published: list, name: str = "sid") -> HumanParticipant:
    return HumanParticipant(name, si, spec.sheets[si], spec.space, spec.rounds,
                            publisher=lambda kind, data: published.append((kind, data)))


def ask(human: HumanParticipant, request) -> tuple[threading.Thread, list]:
    """Run ``generate`` on its own thread (it blocks, exactly as it does under the engine) and return the thread
    plus the one-element list its result or exception lands in."""
    out: list = []

    def run():
        try:
            out.append(human.generate(request.view, seat=request.seat))
        except BaseException as exc:            # recorded, so the assertions can be about the exception
            out.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    for _ in range(500):                        # wait for the seat to actually block, without a fixed sleep
        if human.pending is not None:
            break
        thread.join(0.01)
    return thread, out


def answer(human: HumanParticipant, form: dict, space) -> None:
    human.submit(build_human_message(form, name=human.name, space=space, pending=human.pending))


# ------------------------------------------------------------------------------------ what it asks for --
def test_the_seat_publishes_everything_the_form_needs():
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    published: list = []
    human = human_for(spec, request.meta["si"], published)
    thread, out = ask(human, request)

    assert len(published) == 1
    kind, data = published[0]
    assert kind == "awaiting_human"
    assert data["seat"] == request.seat == PERSONAS[1] and data["seat_idx"] == 1
    assert data["round"] == 1 and data["phase"] == TURN and data["deadline"] == spec.rounds
    # the private sheet — this seat's, and only this seat's
    assert data["sheet"]["threshold"] == spec.sheets[1].threshold
    assert data["sheet"]["values"] == [list(v) for v in spec.sheets[1].values]
    # the state is the scenario's own block, and the legal set is drawn from its live registry
    assert data["state"]["offers"] == {"P1": [0, 2]} and data["state"]["standing"] == "P1"
    assert data["legal"] == {"can_accept": ["P1"], "can_reject": ["P1"], "can_offer": True,
                             "can_walk": True, "can_pass": True}
    # the event is JSON-safe, because it is about to be one line of an SSE frame
    json.dumps(data)

    human.unblock("test over")
    thread.join(2)
    assert isinstance(out[0], SessionStopped)


def test_the_published_state_is_the_block_the_seat_was_conditioned_on():
    """Not a paraphrase and not a re-derivation: the browser sees the same bytes the seat read, which is what
    makes the form's view of the ledger and the seat's view the same view."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    published: list = []
    human = human_for(spec, request.meta["si"], published)
    thread, out = ask(human, request)
    from interlens.arena.negotiation.strategies import parse_negotiation_state
    in_view = parse_negotiation_state(request.view[-1]["content"])
    assert published[0][1]["state"] == in_view
    human.unblock()
    thread.join(2)


def test_a_view_without_a_state_block_is_a_configuration_error():
    """A human seat cannot be told what it may accept without the offer registry, so the failure names the
    misconfiguration rather than rendering a dock that silently cannot vote."""
    spec = two_party_game()
    human = human_for(spec, 0, [])
    with pytest.raises(ValueError, match="negotiation_state"):
        human.generate([{"role": "user", "content": "your turn"}], seat=PERSONAS[0])


# -------------------------------------------------------------------------- indistinguishable envelopes --
@pytest.mark.parametrize("form, expected", [
    ({"action": "propose", "deal": TARGET}, Propose(deal=(0, 2))),
    ({"action": "propose", "deal": [0, 2]}, Propose(deal=(0, 2))),
    ({"action": "accept", "offer_id": "P1"}, Accept(offer_id="P1")),
    ({"action": "walk"}, Walk()),
    ({"action": "pass"}, Pass()),
])
def test_a_submitted_move_is_byte_identical_to_a_policy_seat_turn(form, expected):
    """The identity the whole design rests on: the human's content is exactly what ``action_message`` renders,
    and it parses back to the action that was submitted."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)

    answer(human, {**form, "message": "Here is my move.", "note": "private reasoning"}, spec.space)
    thread.join(2)
    message = out[0]
    assert not isinstance(message, BaseException), message
    assert message.content == action_message(expected, spec.space, message="Here is my move.")
    assert message.author == "sid"
    assert message.metadata["occupant"] == "human:sid"
    assert message.metadata["human_note"] == "private reasoning"
    assert message.metadata["action"] == expected.to_json()
    assert message.metadata["message"] == "Here is my move."
    if not isinstance(expected, Pass):                    # Pass is not part of parse_action's vocabulary
        parsed = parse_action(message.content, deal_decoder=spec.space.parse, standing=["P1"])
        assert parsed.ok and parsed.action == expected


def test_a_proposed_deal_is_rendered_by_name_like_every_other_seat():
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)
    answer(human, {"action": "propose", "deal": {"site": " north ", "FUND": "high"}}, spec.space)
    thread.join(2)
    assert json.loads(out[0].content.split("```json\n")[1].split("\n```")[0])["deal"] == TARGET


def test_a_turn_with_no_public_message_carries_no_message_key():
    """A silent move and a move with cheap talk differ in the envelope exactly as they do for an LLM seat."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)
    answer(human, {"action": "accept", "offer_id": "P1", "message": "   "}, spec.space)
    thread.join(2)
    assert out[0].content == action_message(Accept("P1"), spec.space)
    assert "message" not in out[0].metadata and out[0].metadata["human_note"] is None


# -------------------------------------------------------------------------------- refused before enqueue --
@pytest.mark.parametrize("form, match", [
    ({}, "Choose an action"),
    ({"action": ""}, "Choose an action"),
    ({"action": "accept"}, "which offer"),
    ({"action": "accept", "offer_id": "P9"}, "not one you can accept"),
    ({"action": "reject", "offer_id": "P9"}, "not one you can reject"),
    ({"action": "propose"}, "Set every issue"),
    ({"action": "propose", "deal": {}}, "Set every issue"),
    ({"action": "propose", "deal": {"Site": "North"}}, "distinct issues"),
    ({"action": "propose", "deal": {"Site": "North", "Fund": "Enormous"}}, "unknown option"),
    ({"action": "propose", "deal": [0]}, "must set all 2 issues"),
    ({"action": "propose", "deal": [0, 9]}, "no option 9"),
    ({"action": "surrender"}, "Unknown action"),
])
def test_a_bad_submission_is_refused_and_never_reaches_the_engine(form, match):
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)

    with pytest.raises(ValueError, match=match):
        build_human_message(form, name=human.name, space=spec.space, pending=human.pending)
    # the seat is STILL waiting: nothing was enqueued, so the form stays open with the reason attached
    assert human.pending is not None and not out
    human.unblock()
    thread.join(2)
    assert isinstance(out[0], SessionStopped)


def test_the_deal_error_names_the_issue_and_its_valid_labels():
    """``DealSpace.parse``'s own message travels straight to the player — "unknown option 'Enormous' for issue
    'Fund'; options: [...]" is actionable where "invalid deal" is not."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)
    with pytest.raises(ValueError) as excinfo:
        build_human_message({"action": "propose", "deal": {"Site": "North", "Fund": "Enormous"}},
                            name=human.name, space=spec.space, pending=human.pending)
    assert "Fund" in str(excinfo.value) and "High" in str(excinfo.value)
    human.unblock()
    thread.join(2)


# ------------------------------------------------------------------------------------------- legality --
def _state(spec, **kwargs) -> NegotiationState:
    base = dict(seat=1, sheet=spec.sheets[1], space=spec.space, round=1, deadline=spec.rounds,
                offers={"P1": (0, 2), "P2": (1, 0)}, standing="P1")
    return NegotiationState(**{**base, **kwargs})


def test_an_ordinary_turn_allows_every_move():
    spec = two_party_game()
    state = _state(spec)
    assert phase_of(state) == TURN
    assert legal_actions(state) == {"can_accept": ["P1", "P2"], "can_reject": ["P1", "P2"],
                                    "can_offer": True, "can_walk": True, "can_pass": True}


def test_the_forced_final_proposal_turn_forbids_reject_and_pass():
    """It mirrors ``ScorableNegotiation._PHASE_ALLOWED`` — a reject here is an economic-legality violation, and
    a pass would leave nothing to vote on."""
    spec = two_party_game()
    state = _state(spec, round=spec.rounds + 1)
    assert phase_of(state) == FINAL_PROPOSAL
    legal = legal_actions(state)
    assert legal["can_reject"] == [] and legal["can_pass"] is False
    assert legal["can_offer"] is True and legal["can_accept"] == ["P1", "P2"]


def test_the_final_vote_is_only_on_the_offer_under_vote():
    """The scenario refuses a vote naming any other id, so the form must not offer one."""
    spec = two_party_game()
    state = _state(spec, round=spec.rounds + 1, must_vote=True, standing="P2")
    assert phase_of(state) == FINAL_VOTE
    assert legal_actions(state) == {"can_accept": ["P2"], "can_reject": ["P2"], "can_offer": False,
                                    "can_walk": True, "can_pass": False}


@pytest.mark.parametrize("phase_kwargs, form, match", [
    (dict(round=3, must_vote=True, standing="P1"), {"action": "propose", "deal": TARGET}, "cannot table"),
    (dict(round=3, must_vote=True, standing="P1"), {"action": "pass"}, "formal action"),
    (dict(round=3), {"action": "reject", "offer_id": "P1"}, "there is no offer you can reject"),
    (dict(round=3), {"action": "pass"}, "formal action"),
])
def test_a_move_the_phase_forbids_is_refused(phase_kwargs, form, match):
    spec = two_party_game()
    state = _state(spec, **phase_kwargs)
    pending = PendingRequest(seat=PERSONAS[1], seat_idx=1, turn_idx=-1, round=state.round,
                             phase=phase_of(state), state=state, legal=legal_actions(state))
    with pytest.raises(ValueError, match=match):
        build_human_message(form, name="sid", space=spec.space, pending=pending)


# ----------------------------------------------------------------------------------- the block/unblock --
def test_interp_requests_raise_rather_than_being_ignored():
    """There is no model behind this seat. A capture that was silently dropped would corrupt an experiment far
    more quietly than one that failed — the same contract ``PolicyParticipant`` holds."""
    spec = two_party_game()
    human = human_for(spec, 0, [])
    for kwargs in ({"steering": object()}, {"capture": object()}, {"patch": object()},
                   {"return_logprobs": True}):
        with pytest.raises(NotImplementedError, match="has no model"):
            human.generate([{"role": "user", "content": "x"}], **kwargs)


def test_submitting_when_the_seat_is_not_waiting_is_refused():
    """A message queued against a closed prompt would sit in the inbox and play itself on a LATER turn, under a
    state the player never saw."""
    spec = two_party_game()
    human = human_for(spec, 0, [])
    assert human.pending is None
    with pytest.raises(ValueError, match="not waiting"):
        human.submit(object())


def test_unblock_ends_the_turn_as_an_error_not_as_a_pass():
    """"Still deciding when the server stopped" and "chose to do nothing" are different facts, and only one of
    them is behaviour."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)
    human = human_for(spec, request.meta["si"], [])
    thread, out = ask(human, request)
    human.unblock("session stopped by the user")
    thread.join(2)
    assert isinstance(out[0], SessionStopped)
    assert "session stopped by the user" in str(out[0])
    assert human.pending is None                     # and the seat is released, not left half-open


def test_the_seat_survives_a_broken_publisher():
    """A broadcast failure is a UI problem, not a negotiation one — the person can still be asked in another
    tab, so the game must not die with the stream."""
    spec = two_party_game()
    scen, st, request = with_one_offer(spec)

    def explode(kind, data):
        raise RuntimeError("the stream exploded")

    human = HumanParticipant("sid", 1, spec.sheets[1], spec.space, spec.rounds, publisher=explode)
    thread, out = ask(human, request)
    assert human.pending is not None
    answer(human, {"action": "accept", "offer_id": "P1"}, spec.space)
    thread.join(2)
    assert out[0].content == action_message(Accept("P1"), spec.space)


# --------------------------------------------------------------------------------- end to end, no API --
class _Scripted:
    """The model-free opponent: propose the target package, and cast the final vote when asked for one."""

    self_role, others_role = "assistant", "user"
    system_prompt, private_context = None, ()

    def __init__(self, name):
        self.name = name

    def generate(self, view, *, seat=None, **kwargs):
        from interlens.message import Message
        final = re.search(r"FINAL up/down vote on (P\d+)", view[-1]["content"])
        obj = ({"action": "accept", "offer_id": final.group(1)} if final
               else {"action": "propose", "deal": TARGET})
        return Message(self.name, "```json\n" + json.dumps(obj) + "\n```")


def drive_human(human: HumanParticipant, asked: queue.Queue, space, stop: threading.Event) -> threading.Thread:
    """A stand-in for the browser: wait for an ``awaiting_human`` event, then accept the standing offer if there
    is one and propose the target package otherwise — through the same assembly helper the server uses."""

    def run():
        while not stop.is_set():
            try:
                _kind, data = asked.get(timeout=0.05)
            except queue.Empty:
                continue
            pending = human.pending
            if pending is None:
                continue
            legal = data["legal"]
            form = ({"action": "accept", "offer_id": legal["can_accept"][0], "note": "clears my threshold"}
                    if legal["can_accept"] else {"action": "propose", "deal": TARGET, "note": "opening"})
            human.submit(build_human_message(form, name=human.name, space=space, pending=pending))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def test_a_person_plays_a_whole_episode_and_the_record_says_so(tmp_path):
    """The end-to-end claim, with zero network: a human seat drives a real episode to a real deal, every turn it
    played is attributed to it, its private notes are recorded, and nothing downstream can tell its turns from
    the scripted seat's except by that attribution."""
    spec = two_party_game(rounds=2)
    asked: queue.Queue = queue.Queue()
    human = HumanParticipant("sid", 0, spec.sheets[0], spec.space, spec.rounds,
                             publisher=lambda kind, data: asked.put((kind, data)))
    stop = threading.Event()
    driver = drive_human(human, asked, spec.space, stop)
    table = SeatRouter({PERSONAS[0]: human, PERSONAS[1]: _Scripted("scripted")}, name="mixed")

    store = EpisodeStore(tmp_path)
    ep = asyncio.run(EpisodePool(store).run_episode(ScorableNegotiation(), instance_of(spec), "moves_chat",
                                                    table, seed=0))
    stop.set()
    driver.join(2)

    assert ep.status == "done"
    played = [t for t in ep.turns if t.seat == PERSONAS[0]]
    assert played, "the human seat never moved"
    assert all(t.occupant == "human:sid" for t in played)
    assert all(t.human_note in ("opening", "clears my threshold") for t in played)
    assert all(t.parse_ok for t in played), "a human turn failed the scenario's own parser"
    # the scripted seat is untouched by any of this
    assert all(t.occupant is None and t.human_note is None for t in ep.turns if t.seat == PERSONAS[1])
    # and it survives to disk, which is what the payload and the badge read
    stored = json.loads(store.path(ep).read_text())
    assert {t["occupant"] for t in stored["turns"]} == {"human:sid", None}

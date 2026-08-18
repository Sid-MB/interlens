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
"""Tests for the talking rational agent (``negotiation.talking``).

Four layers, mirroring the experiment's gates. (1) **Action identity (G1)**: every speaking variant's
PROPOSE/ACCEPT/REJECT/WALK stream is byte-identical to the base ``BayesianRationalPolicy`` on the same state;
the listening variant applies the identical decision RULE to its statement-conditioned beliefs, verified by
re-derivation against a base policy fed the conditioned acceptance table. (2) **Grammar round-trip**: every
emitted message parses back (through the same total parser the listener uses) into the payload it was rendered
from. (3) **Parser totality + conditioning direction**: garbage never raises, drops are counted, and each
conditioning update moves the posterior the way the claim says. (4) **Integration**: a real
``ScorableNegotiation`` episode with talking seats accrues zero syntax/legality/economic errors, publishes the
messages, and a listening seat parses them out of its own view.
"""
from __future__ import annotations

import json

from interlens.arena.actions import Accept, Propose
from interlens.arena.negotiation.beliefs import BeliefState
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.negotiation.strategies import BayesianRationalPolicy, NegotiationState
from interlens.arena.negotiation.talking import (MESSAGE_KEY, BabbleBayesianPolicy, TalkingBayesianPolicy,
                                                 TalkingParticipant, condition_on_commit, condition_on_hint,
                                                 condition_on_narration, statements_in)
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.schema import Instance, PERSONAS, new_id
from interlens.arena.table import SeatRouter
from interlens.message import Message
from interlens.participant.participant import Participant

# --------------------------------------------------------------------------------------------------------- #
# Fixtures: a two-issue private-information game so the belief path (the one the listener conditions) runs.
# --------------------------------------------------------------------------------------------------------- #
SPACE = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
SHEET0 = ScoreSheet("p0", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0)
SHEET1 = ScoreSheet("p1", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=4.0)
SHEET2 = ScoreSheet("p2", ((5.0, 5.0), (6.0, 3.0, 0.0)), threshold=3.0)
PERS = tuple(PERSONAS[:3])


def _game(rounds: int = 3) -> GameSpec:
    return GameSpec(SPACE, (SHEET0, SHEET1, SHEET2), rounds=rounds, info="private", chat=True,
                    proposer=0, min_accept=None)


def state(*, seat=0, sheet=SHEET0, deal=None, offer_id="O2", round=1, deadline=3, must_vote=False,
          my_offers=(), received=(), received_by=None, statements=None) -> NegotiationState:
    offers = {offer_id: tuple(deal)} if deal is not None else {}
    for i, d in enumerate(received):
        offers[f"R{i}"] = tuple(d)
    st = NegotiationState(seat=seat, sheet=sheet, space=SPACE, round=round, deadline=deadline,
                          offers=offers, standing=(offer_id if deal is not None else None),
                          received=[tuple(d) for d in ((deal,) if deal is not None else ()) + tuple(received)],
                          received_by_opponent=(received_by or {}), my_offers=[tuple(d) for d in my_offers],
                          must_vote=must_vote, opponents=tuple(i for i in range(3) if i != seat))
    if statements is not None:
        st.statements = tuple(statements)
    return st


#: A battery of states covering every phase branch: ordinary turn with/without a standing offer, later rounds
#: with offer history, the forced-final proposal turn, and the terminal vote.
def battery():
    good, bad = (0, 2), (1, 0)
    hist = {1: [(1, 2), (1, 1)], 2: [(0, 0)]}
    yield state()
    yield state(deal=good)
    yield state(deal=bad, round=2, my_offers=((0, 2),), received=((1, 1),), received_by=hist)
    yield state(deal=good, round=3, my_offers=((0, 2), (0, 1)), received_by=hist)
    yield state(deal=bad, round=4, deadline=3, my_offers=((0, 2),), received_by=hist)   # forced-final proposal
    yield state(deal=good, round=4, deadline=3, must_vote=True, received_by=hist)       # terminal vote
    yield state(round=4, deadline=3, must_vote=True)                                    # vote, nothing standing


# --------------------------------------------------------------------------------------------------------- #
# 1. G1 — action identity.
# --------------------------------------------------------------------------------------------------------- #
def test_every_speaking_variant_acts_byte_identically_to_the_base_policy():
    base = BayesianRationalPolicy()
    variants = [TalkingBayesianPolicy(**flags) for flags in TalkingBayesianPolicy.VARIANTS.values()]
    variants.append(BabbleBayesianPolicy())
    for st in battery():
        expected = base(st)
        for pol in variants:
            assert pol(st) == expected, f"{pol.name} diverged on round {st.round} (must_vote={st.must_vote})"


def test_listen_with_statements_is_the_base_rule_on_the_conditioned_beliefs():
    """T4's gate: not action identity with the mute base (its beliefs legitimately differ) but DECISION-RULE
    identity — the action must equal the base policy's when the base is handed the conditioned table."""
    listener = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["listen"])
    stmts = [{"kind": "narrate", "seat": 1, "above": True, "deal": (1, 2)},
             {"kind": "hint", "seat": 2, "tops": {0: 0, 1: 0}},
             {"kind": "commit", "seat": 1, "floor_norm": 0.4}]
    for st in battery():
        st.statements = tuple(stmts)
        conditioned = listener._accept_prob_table(st, listener._tables(st))

        class BaseWithInjectedBeliefs(BayesianRationalPolicy):
            def _accept_prob_table(self, state, tables):
                return conditioned
        assert listener(st) == BaseWithInjectedBeliefs()(st)


def test_listen_without_statements_is_byte_identical_to_the_base_policy():
    listener = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["listen"])
    base = BayesianRationalPolicy()
    for st in battery():
        assert listener(st) == base(st)


# --------------------------------------------------------------------------------------------------------- #
# 2. Grammar round-trip: emitted messages parse back to the payloads they were rendered from.
# --------------------------------------------------------------------------------------------------------- #
def test_commit_message_round_trips_and_falls_to_the_floor():
    pol = TalkingBayesianPolicy(commit=True)
    st = state()
    text = pol.commit_message(st)
    stmts, candidates, dropped = statements_in(text, space=SPACE, personas=PERS)
    assert (candidates, dropped) == (1, 0)
    assert stmts == [{"kind": "commit", "seat": 0, "floor_norm": pol._norm(st, SHEET0.threshold)}]
    schedule = pol.reservation_schedule(st)
    assert [r for r, _ in schedule] == [1, 2, 3, 4]
    assert schedule[-1][1] == SHEET0.threshold          # the forced final's bar IS the walk-away floor
    assert all(bar >= SHEET0.threshold - 1e-9 for _, bar in schedule)
    assert f"{SHEET0.threshold:.1f}" in text


def test_narrate_message_round_trips_with_the_true_margin_sign():
    pol = TalkingBayesianPolicy(narrate=True)
    good, bad = (0, 2), (1, 0)
    for deal, above in ((good, True), (bad, False)):
        st = state(deal=deal, round=3, deadline=3)      # late round: the bar is near the floor of 5.0
        text = pol.narrate_message(st)
        (stmt,), _, dropped = statements_in(text, space=SPACE, personas=PERS)
        assert dropped == 0
        assert stmt["kind"] == "narrate" and stmt["seat"] == 0 and stmt["offer_id"] == "O2"
        assert stmt["deal"] == deal
        # sign honesty: 'above' must agree with the sheet-vs-bar comparison the payload states
        assert stmt["above"] == above == (SHEET0.utility(deal) >= pol.current_bar(st))
    assert pol.narrate_message(state()) is None         # nothing standing -> nothing to narrate


def test_hint_message_round_trips_to_true_index_resolved_tops():
    pol = TalkingBayesianPolicy(narrate=True, hint=True)
    (stmt,), _, dropped = statements_in(pol.hint_message(state()), space=SPACE, personas=PERS)
    assert dropped == 0
    assert stmt == {"kind": "hint", "seat": 0, "tops": {0: 0, 1: 2}}   # North, High = sheet0's true tops


def test_declaration_composes_the_ladder_and_commentary_narrates():
    st = state(deal=(0, 2))
    t1 = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["commit"])
    t4 = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["listen"])
    assert '"kind": "commit"' in t1.declaration(st) and "hint" not in t1.declaration(st)
    assert t1.commentary(st) is None                                   # T1 does not narrate
    full = t4.declaration(st)
    assert '"kind": "commit"' in full and '"kind": "hint"' in full and MESSAGE_KEY in full
    assert "machine-readable" in full                                  # the LLM convention request
    assert '"kind": "narrate"' in t4.commentary(st)


def test_emission_is_deterministic_and_state_pure():
    pol = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["listen"])
    st = state(deal=(0, 2), round=2, my_offers=((0, 2),))
    assert pol.declaration(st) == pol.declaration(st)
    assert pol.commentary(st) == pol.commentary(st)
    babble = BabbleBayesianPolicy()
    assert babble.commentary(st) == babble.commentary(state(deal=(1, 0), round=2))   # round-only dependence
    assert babble.commentary(state(round=1)) != babble.commentary(state(round=2))


# --------------------------------------------------------------------------------------------------------- #
# 3. Parser totality + conditioning direction.
# --------------------------------------------------------------------------------------------------------- #
def test_parser_is_total_and_counts_drops():
    junk = [
        "no statements here at all { just braces }",
        '```json\n{"' + MESSAGE_KEY + '": {"kind": "narrate"}}\n```',              # no seat, no above
        '{"' + MESSAGE_KEY + '": {"kind": "bribe", "seat": 1, "above": true}}',    # unknown kind
        '{"' + MESSAGE_KEY + '": {"kind": "hint", "seat": 1, "tops": {"Sitee": "North"}}}',  # unknown issue
        '{"' + MESSAGE_KEY + '": {"kind": "commit", "seat": 1}}',                  # commit without a floor
        '{"' + MESSAGE_KEY + '": broken json',
    ]
    for text in junk:
        stmts, _, _ = statements_in(text, space=SPACE, personas=PERS)
        assert stmts == []
    combined = "\n".join(junk) + '\n{"' + MESSAGE_KEY + '": {"kind": "narrate", "seat": 1, "above": false}}'
    stmts, candidates, dropped = statements_in(combined, space=SPACE, personas=PERS)
    assert stmts == [{"kind": "narrate", "seat": 1, "above": False}]
    assert dropped == candidates - 1 >= 4


def test_parser_resolves_llm_convention_names_and_named_deals():
    text = ('{"' + MESSAGE_KEY + '": {"kind": "narrate", "name": "' + PERS[1] + '", "above": true, '
            '"deal": {"Site": "south", "Fund": "MID"}}}\n'
            '{"' + MESSAGE_KEY + '": {"kind": "hint", "name": "' + PERS[2].upper() + '", '
            '"tops": {"Fund": "High"}}}')
    stmts, _, dropped = statements_in(text, space=SPACE, personas=PERS)
    assert dropped == 0
    assert stmts[0] == {"kind": "narrate", "seat": 1, "above": True, "deal": (1, 1)}
    assert stmts[1] == {"kind": "hint", "seat": 2, "tops": {1: 2}}


def _fresh() -> BeliefState:
    return BeliefState((2, 3))


def test_narration_conditioning_moves_the_accept_probability_the_claimed_way():
    deal = (1, 2)
    up, down = _fresh(), _fresh()
    before = _fresh().accept_prob(deal)
    condition_on_narration(up, deal, True)
    condition_on_narration(down, deal, False)
    assert up.accept_prob(deal) > before > down.accept_prob(deal)


def test_hint_conditioning_concentrates_mass_on_matching_shapes():
    bst = _fresh()
    import numpy as np
    predicted = bst._S[0].argmax(axis=1) == 0
    before = float(bst.posterior()[predicted].sum())
    condition_on_hint(bst, {0: 0})
    assert float(bst.posterior()[predicted].sum()) > before


def test_commit_conditioning_pulls_the_threshold_posterior_toward_the_declared_floor():
    low, high = _fresh(), _fresh()
    condition_on_commit(low, 0.35)
    condition_on_commit(high, 0.75)
    assert low.threshold_distribution()[0.35] > high.threshold_distribution()[0.35]
    assert high.threshold_distribution()[0.75] > low.threshold_distribution()[0.75]


# --------------------------------------------------------------------------------------------------------- #
# 4. Integration: full episodes; clean protocol, published speech, working inbound channel.
# --------------------------------------------------------------------------------------------------------- #
def _talking_seat(game, i: int, variant: str, deadline: int) -> TalkingParticipant:
    policy = (BabbleBayesianPolicy() if variant == "babble"
              else TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS[variant]))
    return TalkingParticipant(f"talk#{i}", policy, personas=PERS, seat=i, sheet=game.sheets[i],
                              space=game.space, deadline=deadline, n_seats=3,
                              min_accept=game.min_accept, veto_seats=tuple(game.veto_seats))


def _drive(variant: str, rounds: int = 3) -> dict:
    game = _game(rounds)
    inst = Instance(new_id("talking-test"), ScorableNegotiation.name, 0, 0,
                    payload=game.to_json(), ceiling=1.0, floor=0.0, solution={})
    table = SeatRouter({PERS[i]: _talking_seat(game, i, variant, rounds) for i in range(3)}, name="talking")
    scen = ScorableNegotiation()
    st = scen.make_state(inst, "moves_chat", seed=0)
    for _guard in range(400):
        if st["done"]:
            break
        reqs = scen.next_requests(st)
        if not reqs:
            break
        for req in reqs:
            scen.apply(st, req, table.generate(req.view, seat=req.seat).content)
    return st


def test_talking_tables_play_clean_episodes_and_publish_their_statements():
    for variant in ("commit", "narrate", "hint", "listen", "babble"):
        st = _drive(variant)
        assert st["done"], f"{variant} episode never terminated"
        assert st["syntax_errors"] == 0, f"{variant} produced syntax errors"
        assert st["legality_errors"] == 0, f"{variant} produced legality errors"
        assert st["economic_errors"] == 0, f"{variant} signed or tabled a below-threshold deal"
        spoken = "\n".join(e["content"] for e in st["events"])
        if variant == "babble":
            assert "common ground" in spoken or "give and take" in spoken
            assert MESSAGE_KEY not in spoken
        else:
            expected_kind = {"commit": "commit", "narrate": "narrate", "hint": "hint",
                             "listen": "commit"}[variant]
            assert f'"kind": "{expected_kind}"' in spoken, f"{variant} never published its statement"


def test_a_listening_seat_parses_the_other_seats_statements_from_its_own_view():
    """End to end through the participant: statements published by seats 1 and 2 must arrive on the state seat
    0's policy actually reads, correctly attributed and never self-referential."""
    game = _game()
    speaker = TalkingBayesianPolicy(**TalkingBayesianPolicy.VARIANTS["listen"])
    view = [{"role": "user", "content": "your move\n" + speaker.declaration(
                 state(seat=1, sheet=SHEET1))},
            {"role": "assistant", "content": "```json\n" + json.dumps(
                {"message": speaker.declaration(state(seat=0)), "action": "propose",
                 "deal": {"Site": "North", "Fund": "High"}}) + "\n```"},
            {"role": "user", "content": speaker.hint_message(state(seat=2, sheet=SHEET2))}]
    part = _talking_seat(game, 0, "listen", 3)
    st = part._state_from_view(view)
    seats = {s["seat"] for s in st.statements}
    assert seats == {1, 2}, f"expected statements from seats 1 and 2 only, got {seats}"
    # seat 1's convention request carries two placeholder EXAMPLE blocks ("<your name>"); the parser must
    # drop-and-count them rather than mistake a template for a claim
    assert part.last_parse_census["n_dropped"] == 2
    kinds = {(s["seat"], s["kind"]) for s in st.statements}
    assert (1, "commit") in kinds and (1, "hint") in kinds and (2, "hint") in kinds


def test_retry_resends_the_identical_message():
    """A rejected turn was never published, so the same view must reproduce the same declaration+commentary."""
    game = _game()
    part = _talking_seat(game, 0, "listen", 3)
    view = [{"role": "user", "content": "your move"}]
    first = part.generate(view, seat=PERS[0])
    second = part.generate(view, seat=PERS[0])
    assert first.content == second.content
    assert first.metadata["message"] == second.metadata["message"]

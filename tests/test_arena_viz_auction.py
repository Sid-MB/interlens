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
# [implement: auctions | 2026-08-18 | lane auction-viz | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The auction visualizer: geometry, the replay-derived trace with its per-turn counterfactuals, and the page.

The checks that matter here are the ones a rendered page cannot be trusted on by eye:

- the trace's stage/round assignment comes from the state machine, not from a heuristic over the turn log
  (the SAA case, where a seat moves many times inside one stage, is where a heuristic gets it wrong);
- the per-turn counterfactuals are evaluated at the PRE-move state, and on an all-computable arm they
  therefore reproduce the played move exactly — a self-check with a known answer, which is what licenses
  believing them on an all-LLM arm;
- no non-finite float reaches the page, in the text OR in the embedded payload, because an auction outcome
  legitimately carries ``NaN`` and a ``NaN`` in the payload disables every script on the page;
- an auction payload never claims a game geometry, so the negotiation panels degrade rather than draw empty.
"""
from __future__ import annotations

import json
import math
import re

import pytest

from interlens.arena.auction.spec import Mechanism
from interlens.arena.scenarios import SCENARIOS
from interlens.arena.scenarios.auction import AuctionScenario
from interlens.arena.scenarios.auction_policy import AuctionPolicyParticipant
from interlens.arena.viz.auction_geometry import (AuctionGeometry, auction_trace, is_auction_instance,
                                                 json_safe)
from interlens.arena.viz.episode import episode_payload
from interlens.arena.viz.page import AUCTION_INDEX_COLUMNS, render_episode_html, render_index_html

MECHANISMS = {
    "sealed_second": (lambda: Mechanism.sealed("second_price", reserve=20), 1),
    "dutch": (lambda: Mechanism.dutch(increment=20, reserve=20), 1),
    "english": (lambda: Mechanism.english(increment=20, reserve=20), 1),
    "saa3": (lambda: Mechanism.saa(3, increment=20, reserve=20), 3),
}


def computable_episode(family: str, *, horizon: int = 2, channel: str = "dm", information: str = "private",
                       arm: str | None = None) -> tuple[dict, dict]:
    """One complete episode record played by computable seats, plus its instance record.

    Every seat is a policy, so the episode is deterministic and free — and, crucially for the counterfactual
    test below, its played moves ARE one of the two rules the trace re-derives. Records turns the way the
    runner does (``idx``, ``seat``, ``round``, ``phase``, ``content``, ``view``, ``parsed_action``), which is
    the shape every viz consumer reads.
    """
    scn = AuctionScenario()
    make, _ = MECHANISMS[family]
    mech = make()
    instance = scn.generate_instance(0, 7, mechanism=mech, horizon=8)
    role = {"private": "rational", "oracle": "oracle"}[information]
    cfg = {"mechanism": mech.to_json(), "horizon": horizon, "channel": channel, "value_structure": "apv",
           "policy_seats": {i: role for i in range(5)}, "cell": f"T_{family}"}
    state = scn.make_state(instance, arm or f"all_{role}", 0, cfg)
    spec = state["spec"]
    turns, idx = [], 0
    while not state["done"]:
        requests = scn.next_requests(state)
        if not requests:
            break
        for request in requests:
            seat = int(request.meta["seat_index"])
            name = state["seat_names"][seat]
            participant = AuctionPolicyParticipant(name, spec=spec, seat=seat, information=information,
                                                   instance_id=instance.instance_id)
            text = participant.generate(list(request.view)).content
            turns.append({"idx": idx, "seat": name, "round": state["round"], "phase": request.phase,
                          "content": text, "view": list(request.view), "parse_ok": True,
                          "parsed_action": None, "n_tokens_out": 0, "n_tokens_in": 0,
                          "reasoning_provenance": "none", "gen_failed": False, "gen_failure": None})
            idx += 1
            scn.apply(state, request, text)
            turns[-1]["parsed_action"] = state["_last_parse"][0]
    outcome = scn.score(state)
    episode = {"episode_id": f"auction-test-{family}", "scenario": "auction",
               "arm": arm or f"all_{role}", "model": "computable", "level": 0,
               "instance_id": instance.instance_id, "seed": 0, "cell": cfg["cell"], "cell_cfg": cfg,
               "seats": scn.seat_specs(state), "turns": turns, "round_checkpoints": [],
               "outcome": outcome, "rounds_used": scn.rounds_used(state), "tokens_in": 0, "tokens_out": 0,
               "cost_usd": 0.0, "gen_config": {}, "status": "done", "error": None,
               "schema_version": "1.2"}
    return episode, instance.to_json()


# --------------------------------------------------------------------------------------------------------- #
# The discriminator and the geometry.
# --------------------------------------------------------------------------------------------------------- #
def test_the_auction_discriminator_accepts_auction_payloads_and_rejects_negotiation_ones():
    """``is_auction_instance`` is what the whole viz layer branches on, so it must not be fooled by shape.

    It reads the payload rather than the record's ``scenario`` string, because a bank instance is generated once
    and consumed by cells that override the mechanism."""
    _, instance = computable_episode("sealed_second", horizon=1)
    assert is_auction_instance(instance)
    assert not is_auction_instance(None)
    assert not is_auction_instance({})
    assert not is_auction_instance({"payload": {"game": {"issues": [], "sheets": []}}})
    # A negotiation instance from the real generator, which is the case that actually matters.
    negotiation = SCENARIOS["scorable_negotiation"]().generate_instance(0, 3)
    assert not is_auction_instance(negotiation.to_json())


def test_the_geometry_is_built_at_the_CELL_mechanism_not_the_banks():
    """A single-lot bank backs the sealed cells AND the Dutch ones, so the geometry must come from the
    episode's own ``cell_cfg``. Reading the bank's nominal mechanism instead is the defect class that once had
    every Dutch turn scored against a sealed rule."""
    episode, instance = computable_episode("dutch", horizon=2)
    geo = AuctionGeometry.from_instance(instance, episode["cell_cfg"])
    assert geo is not None
    assert geo.spec.mechanism.family == "dutch"
    assert geo.horizon == 2, "the cell's horizon prefix was not applied"
    # And with no cfg it falls back to the bank's own spec, which is a different object.
    bank_geo = AuctionGeometry.from_instance(instance, None)
    assert bank_geo.horizon == 8
    assert AuctionGeometry.from_instance({"payload": {"game": {}}}, None) is None


def test_the_geometry_payload_carries_the_whole_private_half_and_round_trips_as_json():
    """The panels read valuations, budgets, synergy targets and tie-breaks off the payload, so all four have to
    be there — and the payload has to be JSON, since it is embedded in the page."""
    episode, instance = computable_episode("saa3", horizon=2)
    payload = AuctionGeometry.from_instance(instance, episode["cell_cfg"]).to_json()
    assert json.loads(json.dumps(payload))["mechanism"]["family"] == "saa"
    assert len(payload["stages"]) == 2 and len(payload["lots"]) == 3 and len(payload["bidders"]) == 5
    for stage in payload["stages"]:
        assert len(stage["values"]) == 5 and all(len(row) == 3 for row in stage["values"])
        assert len(stage["budgets"]) == 5 and len(stage["tie_break"]) == 5
    assert payload["price_ceiling"] > 0


# --------------------------------------------------------------------------------------------------------- #
# The trace.
# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("family", sorted(MECHANISMS))
def test_the_trace_replays_every_family_and_takes_its_stages_from_the_state_machine(family):
    """Stage and round come from the replayed state, never from counting a seat's repeat appearances.

    The SAA case is the one that discriminates: a stage there runs several bidding rounds, so a seat moves
    many times inside one stage and a "second move means a new stage" heuristic would report as many stages as
    there are rounds. The assertion is therefore that stages are exactly ``1..T`` and that at least one seat
    moves more than once inside one of them."""
    episode, instance = computable_episode(family, horizon=2)
    trace = auction_trace(episode, instance)
    assert trace is not None and trace["replay"]["ok"], trace and trace["replay"]
    assert trace["turns"], "no turns were traced"
    assert sorted({t["stage"] for t in trace["turns"]}) == [1, 2]
    for t in trace["turns"]:
        assert t["round"] >= 1 and t["phase"] in ("talk", "bid")
        assert t["seat_index"] == next(s["seat"] for s in episode["seats"] if s["name"] == t["seat"])
    if family == "saa3":
        per_stage_seat = {}
        for t in trace["turns"]:
            if t["phase"] == "bid":
                per_stage_seat[(t["stage"], t["seat_index"])] = \
                    per_stage_seat.get((t["stage"], t["seat_index"]), 0) + 1
        assert max(per_stage_seat.values()) > 1, "SAA should run several bidding rounds inside one stage"


@pytest.mark.parametrize("information,rule", [("private", "rational"), ("oracle", "oracle")])
def test_the_counterfactuals_reproduce_an_all_computable_arms_own_moves(information, rule):
    """The self-check with a known answer.

    On an arm where every seat IS one of the two rules, that rule's counterfactual must equal the played move
    on every committed turn — anything else means the trace is evaluating the rule at the wrong state (the
    post-move one, say, which is what an ``on_turn`` hook would hand it). This is what licenses reading the
    same numbers on an all-LLM arm, where there is nothing to check them against."""
    episode, instance = computable_episode("saa3", horizon=2, information=information)
    trace = auction_trace(episode, instance)
    scored = [t for t in trace["turns"] if rule in t["counterfactual"]]
    assert scored, "no turn carried the counterfactual under test"
    disagreements = [t for t in scored if not t["counterfactual"][rule]["agrees"]]
    assert not disagreements, (f"{len(disagreements)} of {len(scored)} turns disagree with the seat's own "
                              f"rule; first: {disagreements[0]}")
    assert not any(e.get("error") for t in trace["turns"] for e in t["counterfactual"].values())


def test_the_omniscient_counterfactual_is_available_on_an_arm_with_no_omniscient_seat():
    """The requirement from "what I want to see": BOTH references on every turn of every arm.

    ``state_block`` only emits ``oracle_values`` for a seat the cell declared omniscient, so the trace has to
    attach them itself. An all-LLM cell declares none, and the omniscient counterfactual still has to be
    there — otherwise the reference exists only in the arms that do not need it."""
    episode, instance = computable_episode("sealed_second", horizon=2, arm="all_llm")
    episode["cell_cfg"] = dict(episode["cell_cfg"], policy_seats={})
    trace = auction_trace(episode, instance)
    committed = [t for t in trace["turns"] if t["phase"] == "bid"]
    assert committed
    for t in committed:
        assert set(t["counterfactual"]) == {"rational", "oracle"}, t["counterfactual"]


def test_counterfactuals_can_be_switched_off_for_the_fast_path():
    """The index build does not need per-turn rules, and computing them is the expensive half of the trace."""
    episode, instance = computable_episode("saa3", horizon=2)
    trace = auction_trace(episode, instance, counterfactuals=False)
    assert trace["counterfactuals"] is False
    assert trace["turns"] and not any(t["counterfactual"] for t in trace["turns"])


def test_an_episode_the_scenario_cannot_replay_still_yields_the_stored_stage_table():
    """A missing panel beats a crashed export, and the settlement table needs no replay at all."""
    episode, instance = computable_episode("sealed_second", horizon=2)
    episode["turns"][2]["phase"] = "not_a_phase"          # no pending request will ever match this
    trace = auction_trace(episode, instance)
    assert trace is not None
    assert trace["replay"]["ok"] is False and trace["replay"]["error"]
    assert trace["stages"], "the stored stage rows must survive a failed replay"


def test_the_onset_overlay_reports_censoring_rather_than_an_event_at_stage_zero():
    """A censored episode is the ABSENCE of an onset event. Encoding it as stage 0 is how a column of censored
    rows would come to look like the earliest onsets in a campaign."""
    episode, instance = computable_episode("sealed_second", horizon=2)
    onset = auction_trace(episode, instance, counterfactuals=False)["onset"]
    assert onset["censored"] is True and onset["stage"] is None
    assert onset["theta"] > 0


# --------------------------------------------------------------------------------------------------------- #
# Non-finite floats.
# --------------------------------------------------------------------------------------------------------- #
def test_json_safe_replaces_every_non_finite_float_recursively():
    """``NaN`` is how an auction says "no denominator here", and ``json.dumps`` writes it as a bare token no
    JSON parser accepts."""
    dirty = {"a": float("nan"), "b": [1.0, float("inf"), {"c": float("-inf")}], "d": 2, "e": "nan", "f": True}
    clean = json_safe(dirty)
    assert clean == {"a": None, "b": [1.0, None, {"c": None}], "d": 2, "e": "nan", "f": True}
    assert "NaN" not in json.dumps(clean) and "Infinity" not in json.dumps(clean)


def test_the_page_embeds_valid_json_and_prints_no_nan_even_when_the_outcome_carries_one():
    """Both failure modes of a leaked ``NaN`` at once: invalid embedded JSON (which disables every script on
    the page) and the literal word ``nan`` printed in a column of real numbers."""
    episode, instance = computable_episode("saa3", horizon=2)
    episode["outcome"]["benchmark_revenue"] = float("nan")
    episode["outcome"]["stages"][0]["suppression"] = float("nan")
    html = render_episode_html(episode_payload(episode, instance))
    embedded = re.search(r'<script type="application/json" id="viz-payload">(.*?)</script>', html, re.S)
    assert embedded, "the page carries no payload script"
    parsed = json.loads(embedded.group(1))               # raises on a bare NaN token
    assert parsed["auction"]["stages"][0]["suppression"] is None
    visible = html[:embedded.start()] + html[embedded.end():]
    # "nan" occurs inside ordinary words ("tenant", "conventional"), so the check is on a standalone token.
    assert not re.search(r"(?<![A-Za-z])nan(?![A-Za-z])", visible)


# --------------------------------------------------------------------------------------------------------- #
# The payload and the page.
# --------------------------------------------------------------------------------------------------------- #
def test_an_auction_payload_never_claims_a_game_geometry():
    """Every negotiation panel tests ``payload["game"]``. Leaving it set on an auction payload would make them
    all try to draw a deal space that does not exist."""
    episode, instance = computable_episode("sealed_second", horizon=2)
    payload = episode_payload(episode, instance)
    assert payload["game"] is None
    assert payload["scenario_family"] == "auction"
    assert payload["auction"] and payload["auction"]["geometry"]["mechanism"]["family"] == "sealed_single"
    assert payload["counterfactual_oracles"] == [] and payload["oracle_names"] == []


@pytest.mark.parametrize("family", sorted(MECHANISMS))
def test_every_family_renders_all_four_panels_and_the_counterfactual_table(family):
    """The four panels design.md §10 commits to, plus the per-turn table, on every mechanism family."""
    episode, instance = computable_episode(family, horizon=2)
    html = render_episode_html(episode_payload(episode, instance))
    for anchor in ("id='ladder'", "id='allocation'", "id='settlement'", "id='channel'",
                   "id='counterfactuals'"):
        assert anchor in html, f"{family} page is missing {anchor}"
    # On the ELEMENT, not the bare class name: every one of these names also appears in the inlined
    # stylesheet, so `"dmsvg" in html` is true on a page that draws no graph at all.
    for svg in ("laddersvg", "stripsvg", "dmsvg"):
        assert f"class='{svg}'" in html, f"{family} page is missing the {svg} chart"
    assert "class='cftable'" in html
    assert html.startswith("<!doctype html>")


def test_a_silent_cell_says_it_had_no_channel_rather_than_drawing_an_empty_graph():
    """An empty graph reads as "they had a channel and did not use it", which is the opposite of the silent
    control's meaning."""
    episode, instance = computable_episode("sealed_second", horizon=2, channel="silent")
    html = render_episode_html(episode_payload(episode, instance))
    assert "class='dmsvg'" not in html, "a silent cell drew a message graph"
    assert "no message channel" in html


def test_the_page_states_that_the_private_draws_are_a_post_hoc_view():
    """The side panel prints every seat's valuations. A page that showed them without saying no seat could see
    them would be teaching a reader the wrong thing about the episode."""
    episode, instance = computable_episode("saa3", horizon=2)
    html = render_episode_html(episode_payload(episode, instance))
    assert "post hoc and omniscient" in html
    assert "Private draws, stage by stage" in html


def test_the_auction_index_uses_its_own_columns_and_sorts_censored_onset_to_the_end():
    """The auction index replaces the negotiation columns rather than extending them, and a censored onset must
    not sort as if it were stage 0."""
    rows = [{"href": "a.html", "label": "a", "cell": "R2", "arm": "all_llm", "family": "saa",
             "channel": "dm", "horizon": 6, "instance": "i1", "seed": 0, "efficiency": 0.95,
             "suppression": -0.05, "revenue_ratio": 0.9, "onset": None, "messages": 200,
             "cf_agreement_pct": 93.0, "fabricated_pct": 0, "hazards": "", "hazard_notes": "",
             "hazard_detail": "", "difficulty": 0.5, "difficulty_tags": "hard"},
            {"href": "b.html", "label": "b", "cell": "R4", "arm": "all_llm", "family": "dutch",
             "channel": "dm", "horizon": 4, "instance": "i2", "seed": 1, "efficiency": 0.8,
             "suppression": 0.165, "revenue_ratio": 0.74, "onset": 2, "messages": 150,
             "cf_agreement_pct": 55.0, "fabricated_pct": 0, "hazards": "", "hazard_notes": "",
             "hazard_detail": "", "difficulty": 0.6, "difficulty_tags": ""}]
    html = render_index_html(rows, "Auction episodes", columns=AUCTION_INDEX_COLUMNS)
    assert "suppression" in html and "cf agreement" in html
    assert "dist NBS" not in html, "the negotiation columns leaked onto an auction index"
    assert "data-sort='999'" in html and "censored" in html
    assert "stage 2" in html
    # And the default column set is untouched, which is what keeps every existing index byte-identical.
    assert "dist NBS" in render_index_html(rows, "Negotiation episodes")


def test_an_instructed_ring_episode_is_badged_as_unpoolable():
    """The instruction is quarantined from the frozen prompt set, so a page carrying it must say so — an
    instructed-ring episode silently listed beside a neutral one is exactly the pooling the design forbids."""
    episode, instance = computable_episode("sealed_second", horizon=2)
    episode["cell_cfg"] = dict(episode["cell_cfg"], ring={"members": [0, 1, 2, 3], "instructed": True})
    html = render_episode_html(episode_payload(episode, instance))
    assert "INSTRUCTED RING" in html and "not poolable" in html


def test_a_negotiation_episode_still_takes_the_negotiation_path():
    """The branch must be a branch, not a takeover: a scorable-negotiation instance still gets its frontier."""
    scn = SCENARIOS["scorable_negotiation"]()
    instance = scn.generate_instance(0, 3)
    episode = {"episode_id": "neg-1", "scenario": "scorable_negotiation", "arm": "all_llm", "model": "m",
               "level": 0, "instance_id": instance.instance_id, "seed": 0, "seats": [], "turns": [],
               "outcome": {}, "status": "done", "schema_version": "1.2"}
    payload = episode_payload(episode, instance.to_json())
    assert payload["game"] is not None and "auction" not in payload
    assert "scenario_family" not in payload
    html = render_episode_html(payload)
    assert "id='frontier'" in html and "id='ladder'" not in html


def test_math_isfinite_guard_on_the_shared_number_formatter():
    """``_num`` is shared with every negotiation panel, so its NaN guard is asserted rather than assumed."""
    from interlens.arena.viz.chrome import _num
    assert _num(float("nan")) == "—" and _num(float("inf")) == "—"
    assert _num(0.5) == "0.500" and _num(None) == "—" and _num(True) == "—"
    assert math.isfinite(0.5)

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

# [rational_agents scaffold: games-presets] 2026-07-23

"""Tests for the swappable game presets (``arena/negotiation/games.py``) and the single-shot / fixed-proposer
protocol knobs they drive on ``ScorableNegotiation``. Every preset is a parameterization of the ONE scorable
engine, so these pin: the registry round-trip (preset -> GameSpec/analysis/Instance), the ultimatum analysis
(the >= vs > IR convention + pure-division Pareto), the ultimatum SPE via the best-response / acceptance oracles,
the divide_dollar Okada v=1/n anchor through the preset path, and that the strategy zoo is well-behaved at the
single-round (T=1) horizon the ultimatum runs at. The CPU end-to-end episode smokes (two policies play through
ScorableNegotiation, atlas machinery) live in the experiment tests, where the seating/annotate layer lives."""
from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest

from interlens.arena.actions import Accept, Propose, Walk
from interlens.arena.engine import EpisodePool
from interlens.arena.negotiation import games
from interlens.arena.negotiation._oracle_common import GameTables, NegotiationState
from interlens.arena.negotiation.acceptance import AcceptanceOracle, ThresholdOracle
from interlens.arena.negotiation.bestresponse import BestResponseOracle
from interlens.arena.negotiation.equilibrium import EquilibriumOracle, okada_closed_form
from interlens.arena.negotiation.sheets import GameSpec
from interlens.arena.negotiation.solutions import ir_mask, pareto_mask
from interlens.arena.negotiation.strategies import TimeDependentPolicy
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.schema import Instance, PERSONAS, new_id
from interlens.message import Message
from interlens.participant.participant import Participant


class _Turn:
    """A minimal turn record (agent name + typed action) matching the arena Turn shape the oracles read."""

    def __init__(self, agent, action):
        self.agent = agent
        self.action = action


# --------------------------------------------------------------------------------------------------------- #
# 1. Registry round-trip: every preset -> (GameSpec, analysis, protocol_cfg) -> Instance.
# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", sorted(games.PRESETS))
def test_registry_round_trip(name):
    game, analysis, protocol_cfg = games.make_preset(name)
    # the GameSpec JSON round-trips (drops into Instance.payload and back)
    rt = GameSpec.from_json(game.to_json())
    assert rt.n_parties == game.n_parties and rt.space.size == game.space.size
    # analysis is present and complete (the exact per-instance descriptors + solution points)
    assert analysis["deal_space_size"] == game.space.size
    assert set(analysis["solutions"]) == {"nash", "kalai_smorodinsky", "egalitarian", "utilitarian",
                                          "max_nash_welfare"}
    # the Instance path works and reuses generate.build_instance (payload = spec, solution = analysis)
    inst, protocol_cfg2 = games.build_preset_instance(name)
    assert isinstance(inst, Instance) and inst.scenario == "scorable_negotiation"
    assert GameSpec.from_json(inst.payload).n_parties == game.n_parties
    assert protocol_cfg == protocol_cfg2
    # the whole thing is JSON-serializable (it must survive Instance persistence)
    json.dumps(inst.to_json())


def test_preset_protocol_cfgs():
    # only the ultimatum needs a non-default protocol; the others play the standard multi-round game
    assert games.make_preset("ultimatum")[2] == {"single_shot": True, "fixed_proposer": True}
    assert games.make_preset("divide_dollar")[2] == {}
    assert games.make_preset("bilateral_multiissue")[2] == {}
    assert games.make_preset("scorable")[2] == {}


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        games.make_preset("prisoners_dilemma")


# --------------------------------------------------------------------------------------------------------- #
# 2. Ultimatum analysis sanity: the IR set under the harness's >= 0 convention, and pure-division Pareto.
# --------------------------------------------------------------------------------------------------------- #
def test_ultimatum_analysis_ir_and_pareto():
    game, analysis, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    assert game.n_parties == 2 and game.rounds == 1 and game.space.n_issues == 1
    U, tau = game.utility_matrix(), game.thresholds
    # thresholds are 0, so the default IR mask (>= 0, solutions.ir_mask default strict=False) admits EVERY split
    # -- including the endpoints where a party's surplus is exactly 0 (responder-share 0, or proposer-share 0).
    assert int(ir_mask(U, tau).sum()) == 11
    # the STRICT (> 0) variant drops those two zero-surplus endpoints -> 9 (the "positive responder share" set,
    # symmetric on the proposer side).
    assert int(ir_mask(U, tau, strict=True).sum()) == 9
    # a pure division has no value creation/destruction, so EVERY split is Pareto-optimal and there is no
    # dominated-but-acceptable slack -- the score-sheet-repair (dominated_target) knob does not apply here.
    assert int(pareto_mask(U).sum()) == 11
    assert analysis["dominated_acceptable_fraction"] == 0.0
    assert analysis["ir_pareto_fraction"] == 1.0


def _ultimatum_scenario_state(pie: float = 10, n_options: int = 11):
    """A fresh ``ScorableNegotiation`` + single-shot ultimatum state, ready at the fixed proposer's turn."""
    game, _, protocol_cfg = games.make_preset("ultimatum", pie=pie, n_options=n_options)
    scen = ScorableNegotiation()
    inst = Instance(new_id("ult"), scen.name, 0, 0, payload=game.to_json(), ceiling=1.0, floor=0.0, solution={})
    return scen, scen.make_state(inst, "moves_only", seed=0, cfg=protocol_cfg)


def test_ultimatum_bare_label_decodes_and_registers():
    # Regression (real Qwen3-4B bug): the model emits {"Split": "P5"}. Labels are now bare proposer-share tokens
    # ("P0".."P10", no "/R" pair), so that exact emission decodes on the FIRST try and registers a live offer
    # (the earlier "P5/R5" pair form made the model abbreviate to "P5" and fail the option lookup -> no_deal).
    game, _, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    assert game.space.issues[0].options[:3] == ("P0", "P1", "P2")       # bare tokens, no "/R" suffix
    assert game.space.parse({"Split": "P5"}) == (5,)                    # decodes to the proposer-keeps-5 split

    scen, st = _ultimatum_scenario_state()
    req = scen.next_requests(st)[0]                                     # the fixed proposer's single-shot turn
    directive = scen.apply(st, req, '```json\n{"action": "propose", "deal": {"Split": "P5"}}\n```')
    assert directive is None                                           # parsed + committed, no retry needed
    assert st["legality_errors"] == 0 and st["final_offer"] is not None  # a live offer was registered


def test_bad_deal_label_retry_echoes_valid_options():
    # Regression: a bad option label must trigger ONE retry whose message ECHOES the offending issue's valid
    # labels (AucArena-style feedback), not the generic "set every issue to a valid option" — otherwise a model
    # just repeats the same bad token and wastes the turn (exactly what sank the first LLM smoke).
    scen, st = _ultimatum_scenario_state()
    req = scen.next_requests(st)[0]
    directive = scen.apply(st, req, '```json\n{"action": "propose", "deal": {"Split": "P999"}}\n```')
    assert directive and "retry" in directive
    assert "Split" in directive["retry"]                               # names the offending issue
    assert "P0" in directive["retry"] and "P10" in directive["retry"]   # lists its valid option labels
    assert st["legality_errors"] == 1


def test_ultimatum_pie_and_granularity_knobs():
    game, analysis, _ = games.make_preset("ultimatum", pie=20, n_options=21)
    assert analysis["deal_space_size"] == 21
    # option o gives the proposer o*(20/20)=o and the responder 20-o; the endpoints are the whole-pie splits
    assert game.sheets[0].values[0][-1] == pytest.approx(20.0)   # proposer keeps everything at the last option
    assert game.sheets[1].values[0][-1] == pytest.approx(0.0)    # responder gets nothing there
    with pytest.raises(ValueError):
        games.make_preset("ultimatum", n_options=1)              # a split needs both endpoints


# --------------------------------------------------------------------------------------------------------- #
# 3. Ultimatum SPE pins (the rational reference the preset exists to measure LLMs against).
# --------------------------------------------------------------------------------------------------------- #
def test_ultimatum_spe_proposer_keeps_the_pie():
    # BestResponseOracle: the proposer's best action is the largest own-share split the rational responder still
    # accepts. With the >= 0 acceptance convention the responder is indifferent at a 0 share and accepts, so the
    # subgame-perfect proposal keeps the WHOLE pie (option n_options-1) -- the discrete SPE (pie-epsilon is the
    # continuous statement).
    game, _, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    legal = [Propose((o,)) for o in range(11)]
    verdict = BestResponseOracle(0).evaluate(game, [], "Proposer", legal)
    assert verdict.best == Propose((10,))                        # keep everything
    assert verdict.divergence(Propose((5,))) > 0                 # an even split leaves surplus on the table
    assert verdict.divergence(Propose((0,))) > 0                 # giving it all away is maximally suboptimal


def test_ultimatum_spe_responder_accepts_positive_share():
    # BestResponseOracle: the responder's best response accepts any positive-surplus standing offer (rejecting
    # pays the no-deal 0). The proposer offered option 6 -> responder share 4 > 0.
    game, _, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    history = [_Turn("Proposer", Propose((6,)))]
    verdict = BestResponseOracle(1).evaluate(game, history, "Responder", [Accept("O1"), Walk()])
    assert verdict.best == Accept("O1")
    assert verdict.value_of(Accept("O1")) == pytest.approx(4.0)  # the responder's surplus for that offer


def test_ultimatum_acceptance_oracle_degenerates_at_the_deadline():
    # AcceptanceOracle at the terminal decision (rounds_left = 0, no continuation) has reservation v_0 = 0, so the
    # responder accepts ANY non-negative-surplus offer -- the optimal-stopping recursion recovers the SPE cutoff.
    game, _, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    tables = GameTables.from_game(game)
    assert AcceptanceOracle(1).reservation(tables, 0) == 0.0


class _GiveAwaySeat(Participant):
    """One scripted seat playing both roles of a single-shot ultimatum: the proposer gives the WHOLE pie away
    (proposes P0, keeping nothing), the responder accepts it."""

    self_role, others_role = "assistant", "user"

    def __init__(self):
        self.name, self.system_prompt, self.private_context = "give_away", None, ()

    def generate(self, view, **kw):
        if "none yet" in view[-1]["content"]:            # proposer: nothing live -> table P0
            return Message(self.name, '```json\n{"action": "propose", "deal": {"Split": "P0"}}\n```')
        return Message(self.name, '```json\n{"action": "accept", "offer_id": "P1"}\n```')   # responder: accept


def test_single_shot_oracle_scoring_integration():
    # Integration regression on the SCENARIO plumbing (not the oracle called directly). The direct-call SPE pins
    # above passed while this path was broken, because the scenario feeds the oracle a history SNAPSHOT (whose
    # live offers the oracle couldn't read -> Accept valued at the no-deal continuation) and only the single
    # chosen Propose (so best-response `best` had nothing better to compare against -> ~0 regret on a proposal
    # turn). A give-the-pie-away ultimatum makes both failures loud: SPE regret of P0 is the whole pie, and the
    # responder that accepts the whole pie has surplus = pie, not 0.
    game, _, protocol_cfg = games.make_preset("ultimatum", pie=10, n_options=11)
    inst = Instance(new_id("ult"), ScorableNegotiation.name, 0, 0, payload=game.to_json(),
                    ceiling=1.0, floor=0.0, solution={})
    scen = ScorableNegotiation(oracles=[ThresholdOracle(), BestResponseOracle(0)])
    ep = asyncio.run(EpisodePool(None).run_episode(scen, inst, "moves_only", _GiveAwaySeat(), seed=0,
                                                   cfg=protocol_cfg))
    assert ep.outcome["deal"] is True and ep.outcome["per_party_surplus"] == [0.0, 10.0]

    proposer, responder = PERSONAS[0], PERSONAS[1]
    br = {c["seat"]: c for c in ep.round_checkpoints if c.get("oracle") == "bestresponse"}
    thr = {c["seat"]: c for c in ep.round_checkpoints if c.get("oracle") == "threshold"}
    # the proposer gave the pie away -> best-response regret is the WHOLE pie (best = the keep-everything offer)
    assert br[proposer]["chosen_value"] == pytest.approx(0.0)
    assert br[proposer]["best_value"] == pytest.approx(10.0)
    assert br[proposer]["divergence"] == pytest.approx(10.0)
    # the responder accepted the whole pie -> its OWN surplus (10) is scored, not the no-deal continuation (0);
    # accepting a positive-surplus offer is optimal, so its regret is 0
    assert br[responder]["chosen_value"] == pytest.approx(10.0)
    assert br[responder]["divergence"] == pytest.approx(0.0)
    assert thr[responder]["chosen_value"] == pytest.approx(10.0)   # the same live offer, seen by every oracle


# --------------------------------------------------------------------------------------------------------- #
# 4. divide_dollar: the equilibrium oracle recovers the Okada v = 1/n anchor through the PRESET path.
# --------------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [2, 3])
def test_divide_dollar_equilibrium_okada_anchor(n):
    game, analysis, protocol_cfg = games.make_preset("divide_dollar", n_parties=n, steps=12,
                                                     rule="unanimity", discount=0.99)
    assert game.n_parties == n and game.min_accept is None and protocol_cfg == {}
    # pure division again: every allocation is Pareto-optimal, no dominated slack
    assert analysis["dominated_acceptable_fraction"] == 0.0
    sol = EquilibriumOracle().solve(game)
    assert sol.converged
    assert np.allclose(sol.values, 1.0 / n, atol=0.05)          # the Okada stationary value v_i -> 1/n
    cf = okada_closed_form(n, 0.99)
    share0 = float(game.utility_matrix()[sol.proposals[0], 0])  # proposer 0's equilibrium own-share
    assert share0 == pytest.approx(cf["proposer_keeps"], abs=0.12)


def test_divide_dollar_majority_rule_sets_min_accept():
    game, _, _ = games.make_preset("divide_dollar", n_parties=3, rule="majority")
    assert game.min_accept == 2                                  # floor(3/2)+1 = a minimal winning coalition
    with pytest.raises(ValueError):
        games.make_preset("divide_dollar", rule="plurality")


# --------------------------------------------------------------------------------------------------------- #
# 5. Strategy zoo at the T=1 horizon the ultimatum runs at: no degenerate / div-by-zero concession curve.
# --------------------------------------------------------------------------------------------------------- #
def test_strategy_zoo_no_degenerate_curve_at_T1():
    game, _, _ = games.make_preset("ultimatum", pie=10, n_options=11)
    boul = TimeDependentPolicy.boulware(beta=0.2)
    # deadline = 1: the two time points a T=1 game visits are t=0 (opening) and t=1 (the deadline), and neither
    # divides by zero (time_fraction floors the deadline at 1, and the concession curve clamps t to [0, 1]).
    opening = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=1, deadline=1, opponents=(1,))
    deadline = NegotiationState(seat=0, sheet=game.sheets[0], space=game.space, round=2, deadline=1, opponents=(1,))
    assert boul.target_norm(opening) > 0.9        # at t=0 Boulware demands its optimum (barely concedes)
    assert boul.target_norm(deadline) < 0.05       # at t=T it has conceded to the reservation
    # and a real move comes out at both ends (no exception, a valid IR proposal)
    for st in (opening, deadline):
        act = boul(st)
        assert isinstance(act, (Propose, Accept, Walk))
        if isinstance(act, Propose):
            assert game.sheets[0].surplus(act.deal) >= 0

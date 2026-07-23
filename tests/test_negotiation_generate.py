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
# [rational_agents scaffold: game-theory] 2026-07-23

"""Scenario generator: the dominated-acceptable-fraction repair and feasible-set-size dial hit their targets
(re-verified by independent enumeration), issue types produce the right cross-party correlation, decorrelation
and determinism behave, and every instance ships a JSON-serializable analysis dict."""
from __future__ import annotations

import json

import numpy as np
import pytest

from interlens.arena.negotiation import solutions as S
from interlens.arena.negotiation.generate import (INSTANCE_LADDER, LADDER_DISCOUNT, generate_game,
                                                  generate_games, generate_instance)
from interlens.arena.negotiation.sheets import GameSpec
from interlens.arena.schema import Instance


def test_dominated_target_hit_and_reverified_by_enumeration():
    for dom_target in (0.4, 0.6):
        game, an = generate_game(n_parties=5, n_issues=5, n_options=4, feasible_fraction=0.12,
                                 dominated_target=dom_target, dominated_tol=0.12, seed=2, max_tries=600)
        achieved = an["generator"]["achieved"]["dominated_acceptable_fraction"]
        assert abs(achieved - dom_target) <= 0.12, (dom_target, achieved)
        # independent recompute from the returned sheets (default acceptable set = unanimity IR = generator's)
        fresh = S.analyze(game.space, game.sheets)
        assert fresh["dominated_acceptable_fraction"] == pytest.approx(achieved)
        assert fresh["ir_count"] == an["generator"]["achieved"]["ir_count"]


def test_feasible_set_size_dial():
    # dominated_target=None -> return the first size-OK candidate; check it lands within the stated slack.
    target = round(0.10 * 4 ** 5)                       # |D| = 1024
    game, an = generate_game(n_parties=6, n_issues=5, n_options=4, feasible_fraction=0.10, feasible_tol=0.3,
                             dominated_target=None, seed=1, max_tries=80)
    slack = max(1, round(0.3 * target))
    assert abs(an["ir_count"] - target) <= slack


def test_compatible_issue_positively_correlates_parties():
    game, _ = generate_game(n_parties=2, n_issues=1, n_options=6, issue_types=["compatible"],
                            feasible_fraction=0.5, dominated_target=None, decorrelate=False, seed=3, max_tries=1)
    v0 = np.array(game.sheets[0].values[0]); v1 = np.array(game.sheets[1].values[0])
    assert np.corrcoef(v0, v1)[0, 1] > 0.5             # shared ranking -> aligned


def test_distributive_issue_negatively_correlates_parties():
    game, _ = generate_game(n_parties=2, n_issues=1, n_options=6, issue_types=["distributive"],
                            feasible_fraction=0.5, dominated_target=None, decorrelate=False, seed=3, max_tries=1)
    v0 = np.array(game.sheets[0].values[0]); v1 = np.array(game.sheets[1].values[0])
    assert np.corrcoef(v0, v1)[0, 1] < 0.0             # opposed camps -> fixed pie


def test_explicit_issue_types_are_honored():
    types = ["distributive", "compatible", "integrative"]
    game, _ = generate_game(n_parties=4, n_issues=3, n_options=4, issue_types=types,
                            dominated_target=None, seed=1, max_tries=1)
    assert game.meta["issue_types"] == types


def test_decorrelate_flag_records_permutations():
    on, _ = generate_game(n_parties=4, n_issues=5, n_options=4, dominated_target=None, decorrelate=True,
                          seed=1, max_tries=1)
    off, _ = generate_game(n_parties=4, n_issues=5, n_options=4, dominated_target=None, decorrelate=False,
                           seed=1, max_tries=1)
    assert on.meta["decorrelate"] is True and isinstance(on.meta["option_perms"], list)
    assert len(on.meta["option_perms"]) == 5
    assert off.meta["option_perms"] is None


def test_determinism_same_seed():
    g1, a1 = generate_game(n_parties=5, n_issues=4, n_options=4, dominated_target=0.6, seed=7, max_tries=200)
    g2, a2 = generate_game(n_parties=5, n_issues=4, n_options=4, dominated_target=0.6, seed=7, max_tries=200)
    assert g1.to_json() == g2.to_json()
    assert a1["dominated_acceptable_fraction"] == a2["dominated_acceptable_fraction"]


def test_batch_generates_distinct_games():
    games = generate_games(3, seed=10, n_parties=4, n_issues=4, n_options=3, dominated_target=None, max_tries=20)
    assert len(games) == 3
    assert games[0][0].to_json() != games[1][0].to_json()


def test_analysis_dict_has_descriptors_and_is_json():
    game, an = generate_game(n_parties=6, n_issues=5, n_options=4, dominated_target=0.6, seed=5, max_tries=400)
    for key in ("deal_space_size", "ir_count", "pareto_count", "ir_pareto_fraction",
                "dominated_acceptable_fraction", "sparsity", "pairwise_iou", "ideal_surplus", "solutions"):
        assert key in an
    assert 0.0 <= an["sparsity"] <= 1.0 and 0.0 <= an["pairwise_iou"] <= 1.0
    assert set(an["solutions"]) == {"nash", "kalai_smorodinsky", "egalitarian", "utilitarian", "max_nash_welfare"}
    json.dumps({"spec": game.to_json(), "analysis": an})        # the on-disk instance record shape


def test_generate_game_discount_and_breakdown_knobs():
    g, _ = generate_game(n_parties=4, n_issues=4, n_options=4, dominated_target=None, max_tries=5,
                         discount=0.9, breakdown_risk=0.05, seed=1)
    assert g.discount == 0.9 and g.breakdown_risk == 0.05
    g2, _ = generate_game(n_parties=4, n_issues=4, n_options=4, dominated_target=None, max_tries=5, seed=1)
    assert g2.discount == 1.0 and g2.breakdown_risk == 0.0        # neutral (no impatience) by default


def test_instance_ladder_defaults_to_discount_below_one():
    # generated bank ships delta < 1 so interior concession is rational (Sandholm-Vulkan), not brinkmanship
    inst = generate_instance(1, seed=2, max_tries=200)
    assert LADDER_DISCOUNT < 1.0
    assert GameSpec.from_json(inst.payload).discount == LADDER_DISCOUNT
    # delta = 1.0 brinkmanship-baseline ablation is reachable via override
    inst2 = generate_instance(1, seed=2, discount=1.0, max_tries=200)
    assert GameSpec.from_json(inst2.payload).discount == 1.0


def test_generate_instance_returns_valid_arena_instance():
    inst = generate_instance(level=1, seed=3, name="scorable_negotiation", max_tries=200)
    assert isinstance(inst, Instance)
    assert inst.scenario == "scorable_negotiation" and inst.level == 1 and inst.seed == 3
    assert inst.ceiling == 1.0 and 0.0 <= inst.floor <= 1.0
    GameSpec.from_json(inst.payload)                            # payload round-trips to a GameSpec
    assert "dominated_acceptable_fraction" in inst.solution     # solution is the analyze() dict
    # payload is deterministic per (level, seed); only the fresh id differs
    inst2 = generate_instance(level=1, seed=3, max_tries=200)
    assert inst2.payload == inst.payload and inst2.ceiling == inst.ceiling and inst2.floor == inst.floor
    assert inst2.instance_id != inst.instance_id
    json.dumps(inst.to_json())                                  # whole Instance is JSON-serializable


def test_instance_ladder_descriptors_within_tolerance_per_level():
    assert len(INSTANCE_LADDER) == 5                            # the arena N_LEVELS convention
    sizes = []
    for level in range(len(INSTANCE_LADDER)):
        sol = generate_instance(level, seed=1, max_tries=300).solution
        # the score-sheet repair holds at EVERY level: acceptable set stays ~50-70% Pareto-dominated
        assert 0.45 <= sol["dominated_acceptable_fraction"] <= 0.75, (level, sol["dominated_acceptable_fraction"])
        assert not sol["empty_ir"]
        sizes.append(sol["ir_count"])
    # feasible-set size is the difficulty dial: strictly shrinks as level rises
    assert all(a > b for a, b in zip(sizes, sizes[1:])), sizes
    with pytest.raises(IndexError):
        generate_instance(len(INSTANCE_LADDER), seed=1)

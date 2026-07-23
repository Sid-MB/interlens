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

"""Deal space + score sheets + GameSpec: enumeration order, mixed-radix indexing, the utility matrix, the
score-sheet descriptors, and JSON round-tripping (the arena ``Instance.payload`` contract)."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from interlens.arena.negotiation.sheets import (GameSpec, ScoreSheet, pairwise_iou, sparsity, surplus_matrix,
                                                utility_matrix)
from interlens.arena.negotiation.space import DealSpace, Issue


def _space():
    return DealSpace((Issue("Site", ("North", "South", "East")), Issue("Fund", ("None", "1M"))))


# --- space ----------------------------------------------------------------------------------------------

def test_space_size_shape_strides():
    sp = _space()
    assert sp.size == 6 == math.prod(sp.shape)
    assert sp.shape == (3, 2)
    assert sp.strides() == (2, 1)          # issue 0 varies slowest


def test_enumerate_order_matches_index_roundtrip():
    sp = _space()
    deals = sp.deals()
    assert deals == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]
    for k, d in enumerate(deals):
        assert sp.index_of(d) == k
        assert sp.deal_at(k) == d


def test_named_and_bounds():
    sp = _space()
    assert sp.named((2, 1)) == {"Site": "East", "Fund": "1M"}
    with pytest.raises(IndexError):
        sp.deal_at(6)
    with pytest.raises(ValueError):
        sp.index_of((3, 0))


def test_parse_is_tolerant_inverse_of_named():
    sp = _space()
    # case- and whitespace-tolerant on both issue names and option labels
    assert sp.parse({" site ": "EAST", "Fund": " 1m"}) == (2, 1)
    assert sp.parse(sp.named((1, 0))) == (1, 0)          # round-trips named()
    assert sp.option_index("Site", "South") == 1 and sp.option_index(1, "1m") == 1
    with pytest.raises(ValueError):
        sp.parse({"Site": "Nowhere", "Fund": "1M"})       # unknown option
    with pytest.raises(ValueError):
        sp.parse({"Site": "East"})                        # missing an issue


def test_space_and_issue_json_roundtrip():
    sp = _space()
    assert DealSpace.from_json(json.loads(json.dumps(sp.to_json()))).deals() == sp.deals()
    iss = Issue("X", ("a", "b"))
    assert Issue.from_json(iss.to_json()) == iss


# --- sheets ---------------------------------------------------------------------------------------------

def test_utility_surplus_and_bounds():
    s = ScoreSheet("A", ((10, 5, 0), (0, 4)), threshold=5.0)
    assert s.utility((0, 1)) == 14.0        # 10 + 4
    assert s.surplus((0, 1)) == 9.0
    assert s.max_utility == 14.0 and s.min_utility == 0.0
    assert s.n_issues == 2


def test_utility_matrix_matches_per_deal():
    sp = _space()
    a = ScoreSheet("A", ((10, 5, 0), (0, 4)), 0.0)
    b = ScoreSheet("B", ((0, 5, 10), (4, 0)), 0.0)
    U = utility_matrix(sp, (a, b))
    assert U.shape == (6, 2)
    for k, d in enumerate(sp.enumerate()):          # matrix row order == enumerate order
        assert U[k, 0] == a.utility(d)
        assert U[k, 1] == b.utility(d)
    X = surplus_matrix(sp, (a, ScoreSheet("B", ((0, 5, 10), (4, 0)), 3.0)))
    assert np.allclose(X[:, 1], U[:, 1] - 3.0)


def test_rescaled_is_affine_on_utility():
    s = ScoreSheet("A", ((10, 5, 0), (0, 4)), 2.0)
    r = s.rescaled(3.0, 7.0)                          # u -> 3u + 7 (constant added ONCE, on issue 0)
    for d in ((0, 0), (2, 1), (1, 0)):
        assert r.utility(d) == pytest.approx(3.0 * s.utility(d) + 7.0)
        assert r.surplus(d) == pytest.approx(3.0 * s.surplus(d))   # surplus scales cleanly
    with pytest.raises(ValueError):
        s.rescaled(0.0)


def test_sparsity_and_iou_known():
    # A scores support {(0,0),(0,1)} (issue0 opts 0,1); zeros = 1 of 3 cells -> plus B's zeros.
    a = ScoreSheet("A", ((3, 5, 0),), 0.0)          # 1 zero of 3
    b = ScoreSheet("B", ((0, 4, 6),), 0.0)          # 1 zero of 3
    assert sparsity((a, b)) == pytest.approx(2 / 6)
    # supports: A={ (0,0),(0,1) }, B={ (0,1),(0,2) }; inter={(0,1)} union has 3 -> IoU 1/3
    assert pairwise_iou((a, b)) == pytest.approx(1 / 3)


# --- GameSpec -------------------------------------------------------------------------------------------

def test_gamespec_validates_sheet_shape():
    sp = _space()
    good = ScoreSheet("A", ((1, 2, 3), (4, 5)), 0.0)
    GameSpec(sp, (good,))
    bad = ScoreSheet("B", ((1, 2), (4, 5)), 0.0)     # issue 0 needs 3 option values
    with pytest.raises(ValueError):
        GameSpec(sp, (bad,))


def test_gamespec_feasible_mask_rules():
    sp = _space()                                     # 6 deals; Site in {North(0), South(1), East(2)} x Fund
    a = ScoreSheet("A", ((1, 1, 1), (0, 0)), 0.0)     # proposer: clears every deal
    b = ScoreSheet("B", ((10, 0, 0), (0, 0)), 5.0)    # clears only Site=North (deals 0,1)
    c = ScoreSheet("C", ((0, 0, 10), (0, 0)), 5.0)    # clears only Site=East  (deals 4,5)
    unan = GameSpec(sp, (a, b, c), proposer=0, min_accept=None)   # all 3 must clear; B,C disjoint -> empty
    assert unan.feasible_mask().sum() == 0
    maj = GameSpec(sp, (a, b, c), proposer=0, min_accept=2)       # proposer + >=1 other -> North or East -> 4
    assert maj.feasible_mask().sum() == 4
    veto = GameSpec(sp, (a, b, c), proposer=0, veto=1, min_accept=2)  # must include veto=B -> North only -> 2
    assert veto.feasible_mask().sum() == 2


def test_gamespec_json_roundtrip_is_plain_json():
    sp = _space()
    g = GameSpec(sp, (ScoreSheet("A", ((1, 2, 3), (4, 5)), 1.5),
                      ScoreSheet("B", ((5, 4, 3), (2, 1)), 2.0)),
                 rounds=6, info="private", chat=False, proposer=0, veto=1, discount=0.9, breakdown_risk=0.05,
                 meta={"note": "x"})
    blob = json.dumps(g.to_json())                   # must be serializable for Instance.payload
    g2 = GameSpec.from_json(json.loads(blob))
    assert g2.to_json() == g.to_json()
    assert g2.info == "private" and g2.chat is False and g2.rounds == 6
    assert g2.discount == 0.9 and g2.breakdown_risk == 0.05
    assert g2.agents == ["A", "B"] and g2.n_parties == 2
    assert np.allclose(g2.utility_matrix(), g.utility_matrix())


def test_gamespec_veto_seats_and_param_validation():
    sp = _space()
    sheets = (ScoreSheet("A", ((1, 2, 3), (4, 5)), 0.0),
              ScoreSheet("B", ((5, 4, 3), (2, 1)), 0.0),
              ScoreSheet("C", ((0, 0, 0), (0, 0)), 0.0))
    assert GameSpec(sp, sheets, veto=None).veto_seats == []
    assert GameSpec(sp, sheets, veto=2).veto_seats == [2]
    assert GameSpec(sp, sheets, veto=[0, 2]).veto_seats == [0, 2]      # multilateral veto set
    # a two-veto game requires both veto seats to clear
    a = ScoreSheet("A", ((10, 0, 0), (0, 0)), 5.0)
    b = ScoreSheet("B", ((10, 0, 0), (0, 0)), 5.0)
    c = ScoreSheet("C", ((0, 0, 0), (0, 0)), 0.0)
    g = GameSpec(sp, (a, b, c), proposer=2, veto=[0, 1], min_accept=1)
    assert g.feasible_mask().sum() == 2                                # only Site=North deals clear A and B
    for bad in (dict(veto=3), dict(discount=0.0), dict(discount=1.5), dict(breakdown_risk=1.0)):
        with pytest.raises(ValueError):
            GameSpec(sp, sheets, **bad)

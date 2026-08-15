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
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""Generation determinism, JSON round-trips, the IPV switch, whole-number invariants, the persona table,
the coherence permutation, and the bank-prefix property (design.md §2, §7.1)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from interlens.arena.auction import priors
from interlens.arena.auction.spec import (AuctionSpec, BANK_STAGES, Mechanism, N_BIDDERS, generate_spec,
                                          synergy_target_size)


def test_generation_is_deterministic_and_round_trips():
    a = generate_spec(17, mechanism=Mechanism.saa(3), value_structure="apv", horizon=4, channel="dm")
    b = generate_spec(17, mechanism=Mechanism.saa(3), value_structure="apv", horizon=4, channel="dm")
    assert json.dumps(a.to_json(), sort_keys=True) == json.dumps(b.to_json(), sort_keys=True)
    back = AuctionSpec.from_json(json.loads(json.dumps(a.to_json())))
    assert back.to_json() == a.to_json()
    assert generate_spec(18, mechanism=Mechanism.saa(3), horizon=4).to_json() != a.to_json()


def test_ipv_switch_zeroes_the_persona_term_but_keeps_the_eps_stream():
    ipv = generate_spec(5, mechanism=Mechanism.sealed(), value_structure="ipv", horizon=3)
    apv = generate_spec(5, mechanism=Mechanism.sealed(), value_structure="apv", horizon=3)
    assert ipv.beta == 0.0 and ipv.sigma_z == 0.0 and all(g == 0.0 for g in ipv.gammas)
    assert apv.beta != 0.0 and apv.sigma_z != 0.0
    # Identical eps and identical public catalogue: O1 <-> O2 is a within-bank paired contrast, not two
    # populations (design.md §7.1).
    for t in range(1, 4):
        assert ipv.stage(t).eps == apv.stage(t).eps
        assert ipv.stage(t).base_values == apv.stage(t).base_values
        assert all(z == 0.0 for z in ipv.stage(t).z)
    assert ipv.stage(1).values != apv.stage(1).values


def test_interdep_turns_on_the_resale_channel_only_there():
    inter = generate_spec(5, mechanism=Mechanism.sealed(), value_structure="interdep", horizon=2)
    assert any(g > 0 for g in inter.gammas)
    assert inter.stage(1).resale is not None and inter.stage(1).signals is not None
    apv = generate_spec(5, mechanism=Mechanism.sealed(), value_structure="apv", horizon=2)
    assert apv.stage(1).resale is None and all(g == 0.0 for g in apv.gammas)


def test_inconsistent_value_structure_is_rejected_at_construction():
    spec = generate_spec(5, mechanism=Mechanism.sealed(), value_structure="apv", horizon=2)
    d = spec.to_json()
    d["value_structure"] = "ipv"                      # beta/sigma_z still live: must fail fast
    with pytest.raises(ValueError, match="ipv requires"):
        AuctionSpec.from_json(d)


@pytest.mark.parametrize("structure", ["ipv", "apv", "interdep"])
@pytest.mark.parametrize("n_items", [1, 3])
def test_whole_number_invariants(structure, n_items):
    mech = Mechanism.sealed() if n_items == 1 else Mechanism.saa(n_items)
    spec = generate_spec(9, mechanism=mech, value_structure=structure, horizon=3)
    for t in range(1, 4):
        st = spec.stage(t)
        assert all(isinstance(v, int) and v >= 1 for row in st.values for v in row)
        assert all(isinstance(b, int) for b in st.budgets)
        assert all(isinstance(b, int) for b in st.base_values)
        if st.signals is not None:
            assert all(isinstance(s, int) for row in st.signals for s in row)


def test_bank_prefix_is_a_strict_prefix():
    bank = generate_spec(2, mechanism=Mechanism.sealed(), horizon=BANK_STAGES)
    short = bank.prefix(8)
    assert short.horizon == 8
    assert [s.to_json() for s in short.stages] == [s.to_json() for s in bank.stages[:8]]
    with pytest.raises(ValueError):
        bank.prefix(BANK_STAGES + 1)


def test_shape_and_persona_structure():
    spec = generate_spec(1, mechanism=Mechanism.saa(20), value_structure="apv", horizon=2)
    assert spec.n_bidders == N_BIDDERS and spec.n_items == 20
    assert sorted(b.persona_id for b in spec.bidders) == sorted(p.persona_id for p in priors.PERSONAS)
    assert spec.attrs.shape == (N_BIDDERS, spec.K) and spec.loadings.shape == (20, spec.K)
    # No two lots share a public profile, so a division convention has something to attach to.
    assert len({tuple(s.loading) for s in spec.item_slots}) == 20
    # |T| = 3 at 20 lots, 2 at 3 lots (design.md v2.1).
    assert synergy_target_size(20) == 3 and synergy_target_size(3) == 2
    for tgt in spec.stage(1).synergy_target:
        assert tgt is None or len(tgt) == 3


def test_mechanism_validation_and_named_constructors():
    with pytest.raises(ValueError, match="not legal for family"):
        Mechanism(family="sealed_single", pricing="uniform")
    with pytest.raises(ValueError, match="single-item"):
        Mechanism(family="dutch", pricing="first_price", n_items=3)
    assert Mechanism.saa(20).round_cap == 5 and Mechanism.saa(3).round_cap == 3
    assert Mechanism.saa(3).activity_rule == "eligibility_ratchet"
    assert Mechanism.from_json(Mechanism.dutch().to_json()) == Mechanism.dutch()


def test_coherence_permutation_preserves_the_multiset_and_moves_the_argmax():
    eps = np.array([[0.1, -0.4, 0.9]])
    affinity = np.array([[2.0, 1.0, -3.0]])            # the eps argmax sits on a DISFAVORED slot
    out = priors.make_coherent(eps, affinity)
    assert sorted(out[0].tolist()) == sorted(eps[0].tolist())
    assert int(np.argmax(out[0])) == 0                 # moved to the highest-affinity slot
    # A row whose argmax is already on a non-disfavored slot is untouched.
    keep = np.array([[0.9, -0.4, 0.1]])
    assert np.allclose(priors.make_coherent(keep, affinity), keep)


def test_tercile_labels_are_public_and_degenerate_under_ipv():
    lo, hi = priors.tercile_bounds(1.0)
    assert lo == pytest.approx(-0.4307, abs=1e-3) and hi == pytest.approx(0.4307, abs=1e-3)
    assert priors.tercile_label(-1.0, 1.0) == "weak"
    assert priors.tercile_label(0.0, 1.0) == "typical"
    assert priors.tercile_label(1.0, 1.0) == "strong"
    assert priors.tercile_label(3.0, 0.0) == "typical"       # sigma_z = 0 under IPV: nothing to report


def test_fact_data_carries_keys_not_prose():
    spec = generate_spec(3, mechanism=Mechanism.saa(3), value_structure="apv", horizon=2)
    b = spec.bidders[0]
    persona = priors.PERSONAS_BY_ID[b.persona_id]
    pub = priors.public_facts(persona, b.attrs, capacity=b.capacity, gamma=b.gamma,
                              synergy_rate=b.synergy_rate, decay=b.decay, budget_mult=b.budget_mult)
    assert {f"attr_{n}" for n in priors.ATTR_NAMES} <= set(pub)
    st = spec.stage(1)
    priv = priors.private_facts(z=st.z[0], sigma_z=spec.sigma_z, budget=st.budgets[0],
                                values=np.array(st.values[0]), synergy_target=st.synergy_target[0],
                                n_items=spec.n_items)
    assert priv["capital_position"] in priors.TERCILE_LABELS and priv["budget"] == st.budgets[0]
    lines = priors.render_facts(priv)
    assert all(isinstance(x, str) for x in lines)      # falls back to key: value with no renderer registered


def test_value_equation_matches_the_design_formula_by_hand():
    base = np.array([100.0])
    loadings = np.array([[1.0, 0.0, 0.0, 0.0]])
    attrs = np.array([[1.0, 0.0, 0.0, 0.0]])
    v = priors.realize_values(base_values=base, loadings=loadings, attrs=attrs, beta=1.0,
                              z=np.array([0.0]), eps=np.array([[0.0]]), gammas=np.array([0.0]))
    assert int(v[0, 0]) == int(round(np.exp(np.log(100.0) + 0.25)))     # (beta / K) * (a . w) = 1/4


def test_every_reference_carries_a_page_note_and_every_cited_key_resolves():
    """prompt.md requires literature citations with page numbers, and design.md §12 item 1 names the entries;
    the registry is the mechanism, so a benchmark citing a key that does not resolve is a test failure."""
    import re
    from pathlib import Path

    from interlens.arena.auction import benchmarks, references

    assert {"vickrey1961", "myerson1981", "milgrom_weber1982", "robinson1985", "graham_marshall1987",
            "mcafee_mcmillan1992", "cramton_schwartz2000", "porter_zona1993", "calvano2020",
            "banchio_skrzypacz2022", "ausubel2004", "ausubel_cramton2014", "che_gale1998",
            "kagel_levin1986", "athey_levin_seira2011"} <= set(references.REFERENCES)
    for key, ref in references.REFERENCES.items():
        assert ref.key == key and ref.citation and ref.url.startswith("http") and ref.note

    # Every ``[key]`` cited in a docstring across the package resolves to a registry entry.
    package = Path(benchmarks.__file__).parent
    cited = set()
    for path in package.glob("*.py"):
        cited |= set(re.findall(r"\[([a-z][a-z0-9_]*\d{4}[a-z0-9_]*)(?:,[^\]]*)?\]", path.read_text()))
    assert cited and cited <= set(references.REFERENCES), sorted(cited - set(references.REFERENCES))

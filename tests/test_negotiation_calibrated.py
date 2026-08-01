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

# [implement: rational_agents — maximizer-pod lane] 2026-08-01
"""Tests for :mod:`interlens.arena.negotiation.calibrated`.

Three layers, in ascending order of what they would catch.

1. **Curve arithmetic.** Each functional form evaluates to the thing its docstring claims, the schema
   validation rejects malformed fits, and the loader round-trips the fitting lane's JSON.
2. **The equivalence regression — the load-bearing test.** A :class:`CalibratedRationalPolicy` carrying only
   step curves must produce the *same acceptance table* and the *same action* as
   :class:`BayesianRationalPolicy` on every turn of a real episode. The whole design claim of this policy is
   "one factor changed, everything else inherited"; if step-equivalence ever breaks, that claim is false and
   any Bayes-vs-calibrated contrast is confounded by whatever else drifted.
3. **Direction of the intervention.** A cave-y curve (opponents accept things below their reservation) must
   make the agent's proposals *more* selfish than the Bayesian agent's, never less. This is the mechanism
   H2-strong rests on, and it is worth pinning as a test rather than discovering from a run.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from interlens.arena.actions import Accept, Propose
from interlens.arena.negotiation.calibrated import (AcceptanceCurve, AcceptanceCurveSet,
                                                    CalibratedRationalPolicy, Z_SPACES)
from interlens.arena.negotiation.generate import generate_game
from interlens.arena.negotiation.oracle_context import GameTables
from interlens.arena.negotiation.sheets import GameSpec
from interlens.arena.negotiation.strategies import BayesianRationalPolicy, NegotiationState

MODEL = "Qwen/Qwen3-8B"


# ------------------------------------------------------------------------------- fixtures --
def _game(seed: int = 0, n_parties: int = 3, n_issues: int = 3, n_options: int = 3) -> GameSpec:
    """A small full-information game from the campaign's own generator — small enough that the exhaustive
    deal-space loops in the oracles stay fast, large enough that the best-response has a real choice to make.
    Generated rather than hand-built so the acceptance tables have realistic structure (the dominated-acceptable
    slack is what gives a cynical opponent model something to exploit)."""
    game, _ = generate_game(n_parties=n_parties, n_issues=n_issues, n_options=n_options,
                            rounds=6, info="full", seed=seed)
    return game


def _state(game: GameSpec, *, seat: int = 0, rnd: int = 1, deadline: int = 6,
           standing: str | None = None, offers: dict | None = None) -> NegotiationState:
    """A full-information :class:`NegotiationState` for ``seat``, with the shared tables attached (the
    calibrated path is full-info only, so every state here carries them)."""
    return NegotiationState(
        seat=seat, sheet=game.sheets[seat], space=game.space, round=rnd, deadline=deadline,
        offers=dict(offers or {}), standing=standing, tables=GameTables.from_game(game),
        opponents=tuple(i for i in range(game.n_parties) if i != seat),
    )


def _step_set() -> AcceptanceCurveSet:
    return AcceptanceCurveSet.step()


# --------------------------------------------------------------------------- curve arithmetic --
def test_step_curve_is_the_bayesian_step_model():
    c = AcceptanceCurve(form="step")
    got = c.prob(np.array([-2.0, -1e-9, 0.0, 0.5, 3.0]))
    assert got.tolist() == [0.0, 0.0, 1.0, 1.0, 1.0]
    assert c.is_step


def test_logistic_curve_matches_closed_form_and_is_monotone():
    c = AcceptanceCurve(form="logistic", params={"a": -0.5, "b": 2.0})
    z = np.linspace(-3, 3, 25)
    assert np.allclose(c.prob(z), 1.0 / (1.0 + np.exp(-(-0.5 + 2.0 * z))))
    assert np.all(np.diff(c.prob(z)) > 0)          # b > 0 => better offers accepted more often


def test_logistic_is_overflow_safe_at_extreme_z():
    """A huge |z| must not overflow to nan/inf — the deal space routinely contains deals far outside the
    fitted range, and one nan in the acceptance table silently poisons the whole expectimax."""
    c = AcceptanceCurve(form="logistic", params={"a": 0.0, "b": 50.0})
    p = c.prob(np.array([-1e4, 1e4]))
    assert np.all(np.isfinite(p)) and p[0] == pytest.approx(0.0) and p[1] == pytest.approx(1.0)


def test_rounds_feature_frac_elapsed_rises_toward_the_deadline():
    """With c > 0 the same offer is accepted more readily late — the deadline-pressure story the fit is
    supposed to capture."""
    c = AcceptanceCurve(form="logistic_rounds", params={"a": 0.0, "b": 1.0, "c": 3.0},
                        rounds_feature="frac_elapsed")
    early = c.prob(np.array([0.0]), rounds_left=10, total_rounds=10)
    late = c.prob(np.array([0.0]), rounds_left=1, total_rounds=10)
    assert late > early
    assert c.prob(np.array([0.0]), rounds_left=10, total_rounds=0) == pytest.approx(0.5)  # no deadline => no pressure


def test_rounds_feature_raw_counts():
    c = AcceptanceCurve(form="logistic_rounds", params={"a": 0.0, "b": 0.0, "c": 1.0},
                        rounds_feature="rounds_left")
    assert c.prob(np.array([0.0]), rounds_left=2)[0] == pytest.approx(1 / (1 + np.exp(-2.0)))


def test_bins_curve_lookup_and_rounds_rows():
    flat = AcceptanceCurve(form="bins", params={"z_edges": [0.0, 0.5], "p": [0.1, 0.6, 0.9]})
    assert flat.prob(np.array([-1.0, 0.2, 0.7])).tolist() == [0.1, 0.6, 0.9]
    rowed = AcceptanceCurve(form="bins", rounds_feature="rounds_left",
                            params={"z_edges": [0.0], "r_edges": [1.5], "p": [[0.2, 0.4], [0.3, 0.8]]})
    assert rowed.prob(np.array([-1.0, 1.0]), rounds_left=1).tolist() == [0.2, 0.4]
    assert rowed.prob(np.array([-1.0, 1.0]), rounds_left=5).tolist() == [0.3, 0.8]


def test_clamp_keeps_probabilities_off_the_hard_zero():
    """A p_min floor is how a fit says 'unlikely, not impossible'. A hard 0 tells the expectimax the deal
    cannot close, which is a materially different claim."""
    c = AcceptanceCurve(form="step", p_min=0.05, p_max=0.95)
    assert c.prob(np.array([-1.0, 1.0])).tolist() == [0.05, 0.95]


@pytest.mark.parametrize("bad", [
    {"form": "nope"},
    {"form": "logistic", "params": {"a": 1.0}},                                    # missing b
    {"form": "logistic_rounds", "params": {"a": 0.0, "b": 1.0}},                   # missing c
    {"form": "bins", "params": {"z_edges": [1.0, 0.0], "p": [0.1, 0.2, 0.3]}},     # unsorted edges
    {"form": "bins", "params": {"z_edges": [0.0], "p": [0.1, 0.2, 0.3]}},          # wrong width
    {"form": "bins", "params": {"z_edges": [0.0], "r_edges": [1.0], "p": [0.1, 0.2]}},  # missing rows
    {"form": "step", "p_min": 0.9, "p_max": 0.1},                                  # inverted clamp
    {"form": "step", "rounds_feature": "sideways"},
])
def test_malformed_fits_are_rejected_at_construction(bad):
    with pytest.raises(ValueError):
        AcceptanceCurve(**bad)


@pytest.mark.parametrize("z_space", sorted(Z_SPACES))
def test_every_z_space_is_finite_and_ranks_deals_by_own_utility(z_space):
    """Whatever convention the fit declares, z must be finite and must be increasing in the seat's own
    utility — a z that reordered deals would make 'better offers are accepted more' false by construction."""
    tables = GameTables.from_game(_game())
    z = Z_SPACES[z_space](tables.utility, tables.thresholds, 1)
    assert np.all(np.isfinite(z))
    order = np.argsort(tables.utility[:, 1])
    assert np.all(np.diff(z[order]) >= -1e-9)


def test_degenerate_game_does_not_divide_by_zero():
    """surplus_norm divides by the best attainable surplus; a game where that is ~0 must fall back rather than
    emit inf."""
    n_deals, n = 4, 2
    util = np.zeros((n_deals, n))
    tables = GameTables(deals=[(i,) for i in range(n_deals)],
                        index={(i,): i for i in range(n_deals)},
                        deals_arr=np.arange(n_deals).reshape(-1, 1),
                        utility=util, surplus=util.copy(), thresholds=np.zeros(n))
    z = Z_SPACES["surplus_norm"](tables.utility, tables.thresholds, 1)
    assert np.all(np.isfinite(z))


# ------------------------------------------------------------------------------- curve sets --
def test_from_json_round_trip_and_provenance_survives(tmp_path):
    blob = {"schema_version": 1, "z_space": "surplus_norm",
            "models": {MODEL: {"form": "logistic", "params": {"a": 0.3, "b": 1.7},
                               "n_events": 812, "n_accepts": 301, "heldout_ece": 0.04,
                               "unknown_diagnostic": [1, 2, 3]}},
            "provenance": {"run_dirs": ["/x/y"], "fit_date": "2026-08-01"}}
    p = tmp_path / "curves.json"
    p.write_text(json.dumps(blob))
    cs = AcceptanceCurveSet.from_json(p)
    assert cs.z_space == "surplus_norm"
    assert cs.for_model(MODEL).params["b"] == 1.7
    assert cs.for_model(MODEL).n_events == 812          # sample size is carried, not dropped
    assert cs.provenance["run_dirs"] == ["/x/y"]        # so a result can cite what it was fit on


def test_json_without_z_space_is_rejected(tmp_path):
    """A curve with no declared z convention is unusable — guessing would rescale every probability."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"models": {}}))
    with pytest.raises(ValueError):
        AcceptanceCurveSet.from_json(p)


def _fit_artifact(tmp_path, *, key=f"{MODEL}:thinking-off", separated=False):
    """A minimal but faithful copy of what ``self_benefit/fit_acceptance.py`` writes."""
    blob = {
        "schema": "rational_agents/acceptance_curves/v1",
        "generated_at": "2026-08-01T05:00:00",
        "invocation": "python -m self_benefit.fit_acceptance ...",
        "events_path": "/nlp/scr/.../events.jsonl", "population": "llm",
        "link": "logistic", "base_features": ["z", "rounds_left"],
        "fallback_model": "pooled-llm", "n_events_total": 2000,
        "models": {
            key: {"n_events": 900, "n_accept": 400, "n_games": 6,
                  "specs": {"base": {"features": ["z", "rounds_left"], "coef": [0.4, 2.5, -0.3],
                                     "separated": separated, "converged": True},
                            "interaction": {"features": ["z", "rounds_left", "z*rounds_left"],
                                            "coef": [0.4, 2.5, -0.3, 0.1]}},
                  "validation": {"base": {"logo_cv": {"brier": 0.19, "ece": 0.03}}}},
            "pooled-llm": {"n_events": 2000, "n_accept": 950, "n_games": 6,
                           "specs": {"base": {"features": ["z", "rounds_left"], "coef": [0.2, 2.0, -0.2],
                                              "separated": False, "converged": True}},
                           "validation": {"base": {"logo_cv": {"brier": 0.21, "ece": 0.05}}}},
        },
    }
    p = tmp_path / "acceptance_curves.json"
    p.write_text(json.dumps(blob))
    return p


def test_fit_artifact_adapter_reads_the_fitting_lane_schema(tmp_path):
    """The consumer adapts to the fitter's native artifact, so the artifact of record stays the fitter's own."""
    cs = AcceptanceCurveSet.from_fit_artifact(_fit_artifact(tmp_path))
    assert cs.z_space == "surplus_norm"                 # the fit's z IS this module's surplus_norm
    c = cs.for_model(f"{MODEL}:thinking-off")
    assert c.form == "logistic_rounds" and c.rounds_feature == "rounds_left"
    assert (c.params["a"], c.params["b"], c.params["c"]) == (0.4, 2.5, -0.3)
    assert c.n_events == 900 and c.n_accepts == 400 and c.heldout_ece == 0.03
    assert cs.for_model("never-fitted-model").params["a"] == 0.2      # falls back to pooled-llm
    assert cs.provenance["spec"] == "base" and cs.provenance["events_path"].endswith("events.jsonl")


def test_fit_artifact_adapter_evaluates_to_the_fitters_own_arithmetic(tmp_path):
    """The whole point of the adapter: P(accept) here must equal sigmoid(b0 + b_z z + b_r rounds_left) as the
    fitter defines it. A rescaled or reordered regressor would pass every other test in this file."""
    cs = AcceptanceCurveSet.from_fit_artifact(_fit_artifact(tmp_path))
    c = cs.for_model(f"{MODEL}:thinking-off")
    z, rl = 0.3, 2
    assert c.prob(np.array([z]), rounds_left=rl)[0] == pytest.approx(
        1.0 / (1.0 + np.exp(-(0.4 + 2.5 * z + -0.3 * rl))))


def test_fit_artifact_rejects_unknown_regressors(tmp_path):
    """If the fitting lane changes its regressors, this must fail loudly rather than evaluate new coefficients
    under the old meaning."""
    blob = json.loads(_fit_artifact(tmp_path).read_text())
    blob["models"][f"{MODEL}:thinking-off"]["specs"]["base"] = {
        "features": ["z", "opponent_count"], "coef": [0.1, 0.2, 0.3]}
    p = tmp_path / "changed.json"
    p.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match="regressors"):
        AcceptanceCurveSet.from_fit_artifact(p)


def test_fit_artifact_rejects_coefficient_count_mismatch(tmp_path):
    blob = json.loads(_fit_artifact(tmp_path).read_text())
    blob["models"]["pooled-llm"]["specs"]["base"]["coef"] = [0.1, 0.2]      # missing the rounds slope
    p = tmp_path / "short.json"
    p.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match="coefficients"):
        AcceptanceCurveSet.from_fit_artifact(p)


def test_fit_artifact_rejects_a_foreign_schema(tmp_path):
    p = tmp_path / "foreign.json"
    p.write_text(json.dumps({"schema": "something/else", "models": {}}))
    with pytest.raises(ValueError, match="not an acceptance-curve fit artifact"):
        AcceptanceCurveSet.from_fit_artifact(p)


def test_separated_fit_is_surfaced_not_swallowed(tmp_path, capsys):
    """A separated fit is ridge-stabilised, not estimated. It stays usable, but the reader must be told."""
    cs = AcceptanceCurveSet.from_fit_artifact(_fit_artifact(tmp_path, separated=True))
    assert "separated" in capsys.readouterr().out
    assert "separated=True" in cs.for_model(f"{MODEL}:thinking-off").notes


def test_rounds_left_matches_the_fitting_lanes_convention():
    """The fit defines rounds_left as rounds remaining AFTER this one, 0 on the forced final. The inherited
    optimal-stopping code uses a different, current-round-inclusive count floored at 1. Evaluating the fitted
    coefficient against the wrong one is a silent off-by-one in every probability, so pin it.

    Constructed so the curve reads the covariate and nothing else (b_z = 0), making the returned probability a
    direct readout of the rounds_left the policy passed in.
    """
    game = _game()
    cs = AcceptanceCurveSet(z_space="surplus_norm", curves={}, default=AcceptanceCurve(
        form="logistic_rounds", params={"a": 0.0, "b": 0.0, "c": 1.0}, rounds_feature="rounds_left"))
    p = CalibratedRationalPolicy(curves=cs, opponent_model=MODEL)
    deadline = 6
    for rnd, expect in [(1, 6), (2, 5), (deadline, 1), (deadline + 1, 0)]:
        st = _state(game, rnd=rnd, deadline=deadline)
        ap = p._accept_prob_table(st, p._tables(st))
        got = ap[0, 1]
        assert got == pytest.approx(1.0 / (1.0 + np.exp(-float(expect)))), f"round {rnd}"


def test_unknown_opponent_model_raises_rather_than_silently_defaulting():
    cs = AcceptanceCurveSet(z_space="surplus", curves={MODEL: AcceptanceCurve(form="step")})
    with pytest.raises(KeyError):
        cs.for_model("some/other-model")


def test_unknown_opponent_fails_at_policy_construction_not_mid_episode():
    """The failure must land at seat build time. Discovering it 40 minutes into a GPU cell wastes the cell."""
    cs = AcceptanceCurveSet(z_space="surplus", curves={MODEL: AcceptanceCurve(form="step")})
    with pytest.raises(KeyError):
        CalibratedRationalPolicy(curves=cs, opponent_model="some/other-model")


# ------------------------------------------------------- the equivalence regression (layer 2) --
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_step_curves_reproduce_the_bayesian_acceptance_table_exactly(seed):
    game = _game(seed=seed)
    st = _state(game)
    bayes, calib = BayesianRationalPolicy(), CalibratedRationalPolicy(curves=_step_set(), opponent_model=MODEL)
    tb = bayes._tables(st)
    assert np.array_equal(bayes._accept_prob_table(st, tb), calib._accept_prob_table(st, tb))
    assert calib.last_path == "calibrated"       # and it really took the calibrated branch to get there


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_step_curves_reproduce_the_bayesian_ACTION_on_every_turn(seed):
    """The table matching is necessary; matching the emitted ACTION at every round, with and without a
    standing offer, is the property the contrast actually depends on."""
    game = _game(seed=seed)
    bayes = BayesianRationalPolicy()
    calib = CalibratedRationalPolicy(curves=_step_set(), opponent_model=MODEL)
    deals = GameTables.from_game(game).deals
    deadline = 5
    for rnd in range(1, deadline + 1):
        for standing_deal in (None, deals[0], deals[len(deals) // 2], deals[-1]):
            offers = {"o1": standing_deal} if standing_deal is not None else {}
            st = _state(game, rnd=rnd, deadline=deadline,
                        standing="o1" if standing_deal is not None else None, offers=offers)
            a, b = bayes.act(st), calib.act(st)
            assert type(a) is type(b), f"seed={seed} round={rnd}: {type(a).__name__} vs {type(b).__name__}"
            assert getattr(a, "deal", None) == getattr(b, "deal", None)
            assert getattr(a, "offer_id", None) == getattr(b, "offer_id", None)


def test_private_info_falls_through_to_the_inherited_belief_path():
    """No opponent utilities => no z => the calibrated model is not applicable. It must defer, and it must say
    so, rather than fabricate a calibrated table from a posterior it was never fit against."""
    game = _game()
    st = _state(game)
    st.tables = None
    calib = CalibratedRationalPolicy(curves=_step_set(), opponent_model=MODEL)
    bayes = BayesianRationalPolicy()
    tb = calib._tables(st)
    assert np.array_equal(calib._accept_prob_table(st, tb), bayes._accept_prob_table(st, tb))
    assert calib.last_path == "belief"


def test_all_step_flag_identifies_the_equivalence_configuration():
    assert _step_set().all_step
    assert not AcceptanceCurveSet(z_space="surplus",
                                  curves={MODEL: AcceptanceCurve(form="logistic",
                                                                 params={"a": 0.0, "b": 1.0})}).all_step


# ----------------------------------------------------- direction of the intervention (layer 3) --
def _cavey(z_space: str = "surplus_norm") -> AcceptanceCurveSet:
    """Opponents who sign almost anything, including deals well below their reservation — the measured LLM
    behaviour the Bayesian step model gets wrong, in exaggerated form."""
    return AcceptanceCurveSet(z_space=z_space, curves={},
                              default=AcceptanceCurve(form="logistic", params={"a": 3.0, "b": 0.5}))


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_a_cavey_opponent_model_makes_the_agent_propose_at_least_as_selfishly(seed):
    """The mechanism behind H2-strong: told that opponents cave, the SAME best-response machinery should stop
    conceding. Own utility of the tabled proposal must never go DOWN relative to the Bayesian agent."""
    game = _game(seed=seed)
    st = _state(game)
    tables = GameTables.from_game(game)
    bayes_act = BayesianRationalPolicy().act(st)
    calib_act = CalibratedRationalPolicy(curves=_cavey(), opponent_model=MODEL).act(st)
    if not (isinstance(bayes_act, Propose) and isinstance(calib_act, Propose)):
        pytest.skip("no proposal to compare on this seed")
    u_bayes = tables.utility[tables.index[tuple(bayes_act.deal)], 0]
    u_calib = tables.utility[tables.index[tuple(calib_act.deal)], 0]
    assert u_calib >= u_bayes - 1e-9


def test_a_cavey_opponent_model_strictly_increases_capture_somewhere():
    """The >= above is satisfied by 'changed nothing'. Across a spread of games the cave-y model must move the
    proposal strictly in at least one — otherwise the calibration is inert and the ladder has no rung."""
    strictly_better = 0
    for seed in range(12):
        game = _game(seed=seed)
        st = _state(game)
        tables = GameTables.from_game(game)
        a = BayesianRationalPolicy().act(st)
        b = CalibratedRationalPolicy(curves=_cavey(), opponent_model=MODEL).act(st)
        if isinstance(a, Propose) and isinstance(b, Propose):
            ia, ib = tables.index[tuple(a.deal)], tables.index[tuple(b.deal)]
            strictly_better += tables.utility[ib, 0] > tables.utility[ia, 0] + 1e-9
    assert strictly_better > 0


def test_the_agent_keeps_its_own_IR_floor_however_cynical_the_opponent_model_is():
    """Calibration changes what the agent believes about OTHERS. It must not loosen the agent's own
    reservation: accepting a below-threshold deal would make the seat's own capture uninterpretable."""
    game = _game()
    tables = GameTables.from_game(game)
    below = [d for d in tables.deals if tables.surplus[tables.index[d], 0] < 0]
    assert below, "fixture game has no below-reservation deal to test with"
    calib = CalibratedRationalPolicy(curves=_cavey(), opponent_model=MODEL)
    for deal in below[:8]:
        st = _state(game, rnd=2, deadline=6, standing="o1", offers={"o1": deal})
        assert not isinstance(calib.act(st), Accept)


def test_per_seat_models_are_looked_up_independently():
    """A heterogeneous lineup must read each seat's own curve. Two seats with opposite curves must produce
    different acceptance columns; a single shared curve would make them identical."""
    game = _game()
    st = _state(game)
    cs = AcceptanceCurveSet(z_space="surplus_norm", curves={
        "caves": AcceptanceCurve(form="logistic", params={"a": 4.0, "b": 0.1}),
        "stubborn": AcceptanceCurve(form="logistic", params={"a": -4.0, "b": 0.1}),
    })
    p = CalibratedRationalPolicy(curves=cs, opponent_model="caves", seat_models={2: "stubborn"})
    ap = p._accept_prob_table(st, p._tables(st))
    assert ap[:, 1].mean() > ap[:, 2].mean() + 0.5
    assert p.model_for_seat(1) == "caves" and p.model_for_seat(2) == "stubborn"

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

# [implement f: fixing rational — fix-direction (B), LLM-calibrated opponent model] 2026-08-18
"""Private-information rational negotiation against an **empirically fitted LLM opponent model**:
:class:`LLMCalibratedRationalPolicy`.

Why this exists. :class:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy` is optimal against
opponents whose signal lives in their offer sequence and who accept iff a deal clears their reservation. Notes
0057/0045/0053 established that at a real LLM table both assumptions fail: the belief posterior is
signal-starved (LLM offers barely move, so the concession likelihood extracts ~nothing), and measured LLM
acceptance is nothing like a step at surplus 0. The result is the 0.20-0.23 closure collapse. This module
keeps the composed agent's *decision machinery* — optimal stopping, expectimax proposals, the IR floor, the
walk rule — and swaps the two RATIONALISTIC priors for quantities **measured from ~1,500 frozen LLM episodes**:

1. **Acceptance**: ``P(opponent accepts deal d)`` becomes the posterior mixture of a fitted acceptance curve
   evaluated on each hypothesis type's normalized surplus, instead of the posterior mass of types whose
   step-model would accept. The same Hindriks–Tykhonov posterior; only the within-type response model changes.
   (The full-information version of this swap is :class:`~interlens.arena.negotiation.calibrated.CalibratedRationalPolicy`;
   this class is its private-information counterpart and reuses its
   :class:`~interlens.arena.negotiation.calibrated.AcceptanceCurveSet` containers unchanged.)
2. **Future offers**: the optimal-stopping reservation ``v_j = delta * E[max(X, v_{j-1})]`` is computed over
   the EMPIRICAL distribution of what LLM opponents actually table at each round position
   (:class:`OfferCurveSet`), instead of the belief-induced "deals that could close, weighted by posterior
   passage" distribution. This is the change note 0045 points at: the Bayesian reservation never decays into a
   known-good standing offer because its imagined offer distribution stays optimistic; the measured incoming-z
   distribution is far thinner, so waiting is worth less and the reservation admits real offers.

Everything is in the program's affine-invariant ``z`` space (``surplus_norm``: own surplus over own best
attainable surplus), so one fitted model pools across games and sheets. The policy is deterministic given
``(state, fitted model)``.

Worked example::

    from interlens.arena.negotiation.llm_calibrated import LLMOpponentModel, LLMCalibratedRationalPolicy

    model = LLMOpponentModel.from_json("opponent_model.json")   # written by the fitting lane
    policy = LLMCalibratedRationalPolicy(model=model, opponent_model="claude-opus-5")
    # seat it exactly as BayesianRationalPolicy is seated (PolicyParticipant / mixed_table)

Degenerate-control identities (pinned by ``tests/test_negotiation_llm_calibrated.py``):

- step acceptance curves reproduce the parent's posterior acceptance table bit-for-bit (a step in per-type
  ``z`` is exactly "this type's utility clears its tau", which is what the parent's mixture thresholds);
- with ``offers=None`` the whole ``act``/``vote`` path is the parent's own (only the acceptance table is
  swapped), so step curves + no offer model = byte-identical actions to ``BayesianRationalPolicy``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .acceptance import AcceptanceOracle, reservation_values
from .bestresponse import BestResponseOracle, passage_probability
from .calibrated import AcceptanceCurve, AcceptanceCurveSet
from .oracle_context import Accept, Propose, Walk
from .strategies import BayesianRationalPolicy, fit_belief

__all__ = ["OfferCurve", "OfferCurveSet", "LLMOpponentModel", "LLMCalibratedRationalPolicy"]


# --------------------------------------------------------------------------------------------------------- #
# The empirical incoming-offer distribution.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OfferCurve:
    """One opponent model's fitted distribution of the ``z`` an offer delivers to its RECIPIENT, as a function
    of round position.

    This is the concession curve seen from the receiving side, which is the side the stopping rule needs: it
    answers "if I wait, what is the next package worth to me", in my own affine-invariant units, without
    knowing the proposer's sheet at all — the recipient's ``z`` is computed from the recipient's own sheet, so
    the fit needs no revelation and the runtime evaluation needs no belief.

    Parameters
    ----------
    frac_edges : list[float]
        ``K-1`` strictly ascending interior edges partitioning round fraction ``t = (round-1)/deadline`` in
        ``[0, 1]`` into ``K`` bins (``searchsorted`` right, exactly like the acceptance bins). Scale-free so a
        curve fitted on 4-round games evaluates on any deadline.
    z_quantiles : list[list[float]]
        ``K`` rows of equiprobable ``z`` support points (fitted quantiles of the observed recipient-``z``
        distribution in that round bin). Row lengths may differ; each row is one discrete pmf with uniform
        masses.
    n_offers : list[int]
        Observation count behind each row, carried so a consumer can see a bin fitted on 12 offers.
    low_power : bool
        The fitting lane's own not-quotable flag, carried through like the acceptance curves'.
    notes : str
        Free text from the fitting lane (runs, exclusions, caveats).
    """

    frac_edges: tuple
    z_quantiles: tuple
    n_offers: tuple = ()
    low_power: bool = False
    notes: str = ""

    def __post_init__(self):
        edges = np.asarray(self.frac_edges, dtype=float)
        if edges.size and np.any(np.diff(edges) <= 0):
            raise ValueError("frac_edges must be strictly ascending")
        if len(self.z_quantiles) != edges.size + 1:
            raise ValueError(f"z_quantiles must have len(frac_edges)+1 = {edges.size + 1} rows; "
                             f"got {len(self.z_quantiles)}")
        if any(len(row) == 0 for row in self.z_quantiles):
            raise ValueError("every z_quantiles row needs at least one support point")

    def pmf(self, frac: float) -> tuple:
        """The discrete pmf ``(z_values, probs)`` of an incoming offer's recipient-``z`` at round fraction
        ``frac`` (clipped to ``[0, 1]``): the fitted quantiles of that round bin with uniform masses."""
        edges = np.asarray(self.frac_edges, dtype=float)
        row = np.asarray(self.z_quantiles[int(np.searchsorted(edges, float(np.clip(frac, 0.0, 1.0)),
                                                              side="right"))], dtype=float)
        return row, np.full(row.size, 1.0 / row.size)

    @classmethod
    def from_dict(cls, d: dict) -> "OfferCurve":
        """Build from one model's JSON block, ignoring keys the schema does not define."""
        return cls(frac_edges=tuple(d["frac_edges"]),
                   z_quantiles=tuple(tuple(row) for row in d["z_quantiles"]),
                   n_offers=tuple(d.get("n_offers", ())), low_power=bool(d.get("low_power", False)),
                   notes=str(d.get("notes", "")))


@dataclass(frozen=True)
class OfferCurveSet:
    """A fitted :class:`OfferCurve` per opponent model. Same lookup contract as
    :class:`~interlens.arena.negotiation.calibrated.AcceptanceCurveSet`: an unknown model with no default is an
    ERROR at seat construction, never a silent fallback."""

    curves: dict
    default: OfferCurve | None = None
    provenance: dict = field(default_factory=dict)

    def for_model(self, model_id: str) -> OfferCurve:
        """The curve for ``model_id``, or ``default``; :class:`KeyError` naming the fitted models otherwise."""
        if model_id in self.curves:
            return self.curves[model_id]
        if self.default is not None:
            return self.default
        raise KeyError(f"no fitted offer curve for opponent model {model_id!r} and no default; "
                       f"fitted models are {sorted(self.curves)}")

    @classmethod
    def from_json_dict(cls, blob: dict) -> "OfferCurveSet":
        """Read the fitting lane's ``offers`` block: ``{"models": {id: {...}}, "default": {...}?}``."""
        curves = {m: OfferCurve.from_dict(d) for m, d in blob.get("models", {}).items()}
        default = blob.get("default")
        fallback = blob.get("fallback_model")
        return cls(curves=curves,
                   default=(OfferCurve.from_dict(default) if isinstance(default, dict)
                            else curves.get(fallback) if fallback else None),
                   provenance=blob.get("provenance", {}))


# --------------------------------------------------------------------------------------------------------- #
# The combined fitted artifact.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LLMOpponentModel:
    """Everything the calibrated policy consumes, loaded from ONE fitted artifact.

    Parameters
    ----------
    acceptance : AcceptanceCurveSet
        Panel-grain ``P(accept | z, rounds_left)`` per opponent model ("next time this seat moves, does it
        take this offer" — folds in crowding).
    acceptance_vote : AcceptanceCurveSet | None
        Vote-conditional grain, applied in the endgame (the forced final and the ``endgame_rounds`` before
        it). Measured LLM vote acceptance is ~0.99 even below the voter's own reservation, an order of
        magnitude above the panel rate, and pricing the endgame at the panel grain tells the agent closure is
        near-impossible exactly where it is near-certain (the lesson of the full-info calibrated lane).
    offers : OfferCurveSet | None
        The empirical incoming-offer distribution per opponent model. ``None`` = keep the parent's
        belief-induced offer distribution (the acceptance-only variant, a legitimate ablation arm).
    provenance : dict
        The fitting lane's record (runs, fit/held-out instance split, invocation).
    """

    acceptance: AcceptanceCurveSet
    acceptance_vote: AcceptanceCurveSet | None = None
    offers: OfferCurveSet | None = None
    provenance: dict = field(default_factory=dict)

    SCHEMA = "rational_agents/llm_opponent_model/v1"

    @classmethod
    def from_json(cls, path: str | Path) -> "LLMOpponentModel":
        """Load the fitting lane's combined artifact (schema :data:`SCHEMA`); see the fitter for the shape."""
        blob = json.loads(Path(path).read_text())
        schema = blob.get("schema", "")
        if schema != cls.SCHEMA:
            raise ValueError(f"{path}: not an LLM opponent-model artifact (schema={schema!r}, "
                             f"expected {cls.SCHEMA!r})")

        def curve_set(block: dict | None) -> AcceptanceCurveSet | None:
            if not block:
                return None
            models = {m: AcceptanceCurve.from_dict(d) for m, d in block.get("models", {}).items()}
            fallback = block.get("fallback_model")
            return AcceptanceCurveSet(z_space=block.get("z_space", "surplus_norm"), curves=models,
                                      default=models.get(fallback) if fallback else None,
                                      provenance=block.get("provenance", {}))

        return cls(acceptance=curve_set(blob["acceptance"]),
                   acceptance_vote=curve_set(blob.get("acceptance_vote")),
                   offers=(OfferCurveSet.from_json_dict(blob["offers"]) if blob.get("offers") else None),
                   provenance=blob.get("provenance", {}))

    @classmethod
    def step(cls) -> "LLMOpponentModel":
        """The degenerate model that drives :class:`LLMCalibratedRationalPolicy` back to exact Bayes behaviour
        (step acceptance, no offer model) — the equivalence-test control."""
        return cls(acceptance=AcceptanceCurveSet.step(z_space="surplus_norm"), acceptance_vote=None,
                   offers=None, provenance={"note": "synthetic step control, not a fit"})


# --------------------------------------------------------------------------------------------------------- #
# The policy.
# --------------------------------------------------------------------------------------------------------- #
class LLMCalibratedRationalPolicy(BayesianRationalPolicy):
    """:class:`BayesianRationalPolicy` for PRIVATE-information tables with both rationalistic priors replaced
    by the fitted :class:`LLMOpponentModel` (module docstring). Inherits the belief posterior, the IR floor on
    its own acceptances, the quorum-aware vote valuation and the walk rule unchanged.

    Parameters
    ----------
    model : LLMOpponentModel
        The fitted opponent model.
    opponent_model : str
        Model id filling the other seats (the fitting key, e.g. ``"claude-opus-5"``). Required because the
        policy cannot infer from the state who it is playing.
    seat_models : dict[int, str] | None
        Per-seat override for heterogeneous tables. A seat mapped to a key starting with ``"policy:"`` is a
        computable seat: it keeps the parent's step-posterior acceptance column and contributes no offer
        curve, since the fitted curves describe LLMs, not the project's own agents.
    endgame_rounds : int
        How many final regular rounds (plus the forced final itself) are priced at the vote grain when
        ``model.acceptance_vote`` exists. 1 covers the last regular round + forced final.
    discount, walk_if_hopeless, name
        As :class:`BayesianRationalPolicy`.

    Attributes
    ----------
    last_path : str | None
        ``"calibrated"``, ``"calibrated-vote"`` or ``"belief"`` (an opponent column that fell back to the
        parent's model) — set every turn so a run can be audited for which model was live.
    """

    def __init__(self, *, model: LLMOpponentModel, opponent_model: str,
                 seat_models: dict[int, str] | None = None, endgame_rounds: int = 1,
                 discount: float | None = None, walk_if_hopeless: bool = True,
                 name: str = "llm-calibrated-rational"):
        super().__init__(discount=discount, walk_if_hopeless=walk_if_hopeless, name=name)
        self.model = model
        self.opponent_model = str(opponent_model)
        self.seat_models = dict(seat_models or {})
        self.endgame_rounds = int(endgame_rounds)
        self.last_path: str | None = None
        self._prob_cache: dict = {}     # (matrix id, curve id, r_left, total) -> (T, D) curve evaluation
        self._z_cache: dict = {}        # utility-matrix id -> (T, D) per-type normalized surplus
        # Fail at seat construction, not mid-episode: every model this policy may face must have a curve.
        for key in [self.opponent_model, *self.seat_models.values()]:
            if key.startswith("policy:"):
                continue
            self.model.acceptance.for_model(key)
            if self.model.acceptance_vote is not None:
                self.model.acceptance_vote.for_model(key)
            if self.model.offers is not None:
                self.model.offers.for_model(key)

    def model_for_seat(self, seat: int) -> str:
        """Fitting key seated at ``seat`` — the per-seat override if given, else ``opponent_model``."""
        return self.seat_models.get(int(seat), self.opponent_model)

    # -- the fitted acceptance model ------------------------------------------------------------------------
    @staticmethod
    def _fit_rounds_left(state) -> int:
        """Rounds remaining AFTER the current one, 0 on the forced final — the FITTING lane's convention,
        deliberately distinct from the stopping rule's ``max(deadline - round + 1, 1)`` (they differ by one,
        and on the forced final by the difference between 0 and 1; see the full-info calibrated policy)."""
        return max(int(state.deadline) + 1 - int(state.round), 0)

    def _type_z(self, st, deals_arr: np.ndarray) -> np.ndarray:
        """UNCLIPPED per-type normalized surplus ``(|types|, D)``: ``(u_t(d) - tau_t) / (ideal_t - tau_t)`` —
        the ``surplus_norm`` coordinate the curves were fitted in, evaluated under every belief hypothesis.
        (:meth:`BeliefState.expected_normalized_surplus_matrix` clips at 0, which would erase exactly the
        below-threshold region where the fitted curves differ most from the step model.) Cached by the
        identity of the shared type-utility tensor, which the prepared default grid reuses across turns."""
        U = st.type_utility_matrix(deals_arr)
        hit = self._z_cache.get(id(U))
        if hit is not None:
            return hit
        tau = np.asarray(st.type_thresholds(), dtype=float)
        ideal = U.max(axis=1)                       # exact per-type ideal over the full enumerated space
        denom = np.where(ideal - tau > 1e-9, ideal - tau, 1.0)
        Z = (U - tau[:, None]) / denom[:, None]
        if len(self._z_cache) > 8:
            self._z_cache.clear()
        self._z_cache[id(U)] = Z
        return Z

    def _mixture_prob(self, st, deals_arr: np.ndarray, curve, r_left: int, total: int) -> np.ndarray:
        """Posterior-expected fitted acceptance over all deals: ``posterior @ curve(Z_types)`` — the exact
        mixture ``E_types[P(accept | z_type)]``, not the plug-in ``P(accept | E[z])`` (Jensen gap). The curve
        evaluation over the type grid depends only on (grid, deals, curve, round position), so it is cached and
        each turn costs one gemv."""
        Z = self._type_z(st, deals_arr)
        key = (id(Z), id(curve), int(r_left), int(total))
        P = self._prob_cache.get(key)
        if P is None:
            P = curve.prob(Z, rounds_left=r_left, total_rounds=total)
            if len(self._prob_cache) > 64:
                self._prob_cache.clear()
            self._prob_cache[key] = P
        return st.posterior() @ P

    def _accept_prob_table(self, state, tables):
        """``(D, n)`` acceptance probabilities with each modelled LLM opponent's column read off its fitted
        curve, mixed over the SAME belief posterior the parent uses.

        Mirrors the parent's structure exactly: the table is seeded at 1.0, and only opponents with observed
        offers (``fit_belief``'s states) get a modelled column — so a set of STEP curves reproduces the
        parent's table bit-for-bit (a step at ``z_type = 0`` is precisely "type utility clears type tau"),
        which is the regression identity the tests pin. Computable opponents (``policy:*`` seat models) keep
        the parent's step-posterior column."""
        if state.tables is not None:
            # Full-information calibrated play is CalibratedRationalPolicy's job; this class is the private
            # counterpart and refuses to half-support the other regime silently.
            self.last_path = "belief"
            return super()._accept_prob_table(state, tables)
        total = int(getattr(state, "deadline", 0)) + 1
        r_left = self._fit_rounds_left(state)
        use_vote = self.model.acceptance_vote is not None and r_left <= self.endgame_rounds
        active = self.model.acceptance_vote if use_vote else self.model.acceptance
        self.last_path = "calibrated-vote" if use_vote else "calibrated"
        belief = fit_belief(state)
        ap = np.ones((tables.n_deals, tables.n_agents))
        for opp, st in belief.states.items():
            key = self.model_for_seat(int(opp))
            if key.startswith("policy:"):
                ap[:, int(opp)] = st.accept_prob_matrix(tables.deals_arr)
                self.last_path = "belief"           # at least one column fell back; auditable
                continue
            ap[:, int(opp)] = self._mixture_prob(st, tables.deals_arr, active.for_model(key), r_left, total)
        ap[:, state.seat] = 1.0
        return ap

    # -- the fitted offer model ------------------------------------------------------------------------------
    def _offer_pmfs(self, state, tables, r_left: int) -> list:
        """Per-remaining-round pmfs for :func:`reservation_values`: ``pmfs[j-1]`` is the surplus distribution
        of the offer arriving with ``j`` rounds remaining, i.e. at regular round ``deadline - j + 1``, read off
        the fitted recipient-``z`` curve at that round's fraction and scaled by THIS seat's surplus capacity
        (``z * max own surplus`` = own surplus — the affine-invariant transport into the recursion's units).
        With several modelled opponents the per-tier pmfs are mixed with equal weight; computable opponents
        contribute nothing (their proposals are not what the fit measured)."""
        deadline = max(int(state.deadline), 1)
        cap = float(np.max(tables.surplus[:, state.seat]))
        keys = [self.model_for_seat(int(o)) for o in state.opponents]
        curves = [self.model.offers.for_model(k) for k in keys if not k.startswith("policy:")]
        if not curves:
            curves = [self.model.offers.for_model(self.opponent_model)]
        pmfs = []
        for j in range(1, r_left + 1):
            frac = (deadline - j) / deadline        # round (deadline - j + 1) => fraction (round-1)/deadline
            vals, probs = [], []
            for curve in curves:
                v, p = curve.pmf(frac)
                vals.append(v * cap)
                probs.append(p / len(curves))
            pmfs.append((np.concatenate(vals), np.concatenate(probs)))
        return pmfs

    def _reservation_curve(self, state, tables) -> list:
        """The empirical optimal-stopping curve ``[v_0, ..., v_{r_left}]`` in own-surplus units: the McCall
        recursion over the FITTED incoming-offer distribution rather than the belief-induced one."""
        disc = self.discount if self.discount is not None else float(state.discount)
        r_left = max(state.deadline - state.round + 1, 1)
        pmfs = self._offer_pmfs(state, tables, r_left)
        return reservation_values([], [], r_left, discount=disc, pmfs=pmfs)

    def reservation(self, state) -> float:
        """The reservation surplus this policy holds at ``state`` — the number an offline audit plots against
        a standing offer's surplus. Under the empirical offer model when fitted, else the parent's."""
        tables = self._tables(state)
        if self.model.offers is None:
            ap = self._accept_prob_table(state, tables)
            disc = self.discount if self.discount is not None else float(state.discount)
            pass_vec = passage_probability(ap, state.seat, min_accept=state.min_accept,
                                           veto_seats=state.veto_seats)
            oracle = AcceptanceOracle(state.seat, discount=disc, accept_prob_vec=pass_vec)
            return oracle.reservation(tables, max(state.deadline - state.round + 1, 1))
        return float(self._reservation_curve(state, tables)[-1])

    # -- the decision rule ------------------------------------------------------------------------------------
    def act(self, state):
        """Parent machinery with the fitted acceptance table when no offer model is fitted (the acceptance-only
        ablation, and the exact-Bayes regression path under step curves); otherwise the same accept / propose /
        walk skeleton with the reservation and the proposal continuation both priced on the empirical
        incoming-offer distribution."""
        if self.model.offers is None:
            return super().act(state)
        disc = self.discount if self.discount is not None else float(state.discount)
        tables = self._tables(state)
        ap = self._accept_prob_table(state, tables)
        r_left = max(state.deadline - state.round + 1, 1)
        curve = self._reservation_curve(state, tables)
        v = float(curve[-1])

        # accept the standing offer iff its conditioned yes-vote EV clears the empirical continuation — the
        # parent's own vote valuation (quorum/veto/forced votes included), with v swapped in.
        deal = state.standing_deal
        vote_values = self._standing_vote_values(state, tables, ap, v)
        if deal is not None and state.standing is not None and vote_values is not None:
            yes_value, no_value, p_yes, _ = vote_values
            if p_yes > 0.0 and yes_value >= no_value and self._own_surplus_ok(tables, state, deal):
                return Accept(state.standing)

        # else best-respond with a proposal: passage priced on the fitted acceptance table, failure priced at
        # the discounted empirical continuation (the value of one fewer round of incoming offers).
        cont_val = disc * float(curve[-2]) if len(curve) >= 2 else 0.0
        br = BestResponseOracle(state.seat, discount=disc, accept_prob=ap,
                                min_accept=state.min_accept, veto_seats=state.veto_seats)
        cont = np.full(tables.n_agents, cont_val)
        prop_vals = br.propose_values(tables, cont, min_accept=state.min_accept,
                                      veto_seats=state.veto_seats)
        best_idx = self._pick_proposal(prop_vals, None, tables, state.seat)
        if self.walk_if_hopeless and prop_vals[best_idx] <= 0 and r_left <= 1:
            return Walk()
        return Propose(tuple(int(x) for x in tables.deals[best_idx]))

    # ``vote`` is inherited unchanged: the terminal quorum-aware vote already reads this class's fitted
    # acceptance table through ``_accept_prob_table`` and prices continuation at 0, which is exact on the
    # forced final regardless of the offer model.

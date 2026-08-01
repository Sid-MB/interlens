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
"""Behaviourally-calibrated rational negotiation: :class:`CalibratedRationalPolicy`.

The composed Bayesian agent (:class:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy`) is
optimal against the opponent model it is given, and the opponent model it is given is **wrong for LLMs**. Under
full information it assumes an opponent accepts a deal iff that deal clears the opponent's reservation — a step
function at surplus 0. Measured LLM seats do not behave that way: they accept below their threshold 20-94% of
the time, and they refuse plenty of offers that clear it.

This module keeps *every* other part of the agent — the optimal-stopping reservation, the expectimax
best-response, the individual-rationality floor on its own acceptances, the walk-if-hopeless rule — and swaps
that one step function for an **empirically fitted** ``P(accept | z, rounds_left)`` curve per opponent model.
The whole intervention is the override of
:meth:`~interlens.arena.negotiation.strategies.BayesianRationalPolicy._accept_prob_table`; nothing else is
touched, which is what makes the Bayes-vs-calibrated contrast a clean single-factor comparison rather than two
different agents.

Why that is the interesting knob: the Bayesian agent's proposals are *generous* precisely because it models
opponents as refusers. Tell it the truth — that these opponents cave — and it should best-respond by demanding
more. The preregistered question (H2-strong) is whether it then extracts more than the Bayesian agent does, and
whether the table gets **less fair** as the extraction gets more cynical.

FULL INFORMATION ONLY (deliberate). Computing ``z`` needs the opponent's own utility for a deal, which only
exists under ``--info full``. Under private info this class falls straight through to the inherited belief-oracle
path and is therefore *identical* to :class:`BayesianRationalPolicy` — it does not silently substitute a
half-calibrated model. Calling code that wants the calibrated behaviour must run full-info tables; the policy
records which path it took on ``last_path`` so a run can be audited rather than assumed.

Worked example
--------------
::

    from interlens.arena.negotiation.calibrated import AcceptanceCurveSet, CalibratedRationalPolicy

    curves = AcceptanceCurveSet.from_fit_artifact("self_benefit/acceptance_curves.json")
    policy = CalibratedRationalPolicy(curves=curves, opponent_model="Qwen/Qwen3-8B")
    # ... seat it exactly as BayesianRationalPolicy is seated (table.policy_seat / mixed_table)

A step-function curve reproduces the Bayesian agent **exactly** — that equivalence is the regression test in
``tests/test_negotiation_calibrated.py`` and it is the reason the curve object can express a step at all::

    step = AcceptanceCurveSet.step()          # P(accept) = 1 iff surplus >= 0
    CalibratedRationalPolicy(curves=step, opponent_model="anything")   # == BayesianRationalPolicy
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .strategies import BayesianRationalPolicy

__all__ = ["AcceptanceCurve", "AcceptanceCurveSet", "CalibratedRationalPolicy", "Z_SPACES"]


# --------------------------------------------------------------------------------------------------------- #
# z: the scalar an opponent's accept probability is a function of.
# --------------------------------------------------------------------------------------------------------- #
def _z_surplus(utility: np.ndarray, thresholds: np.ndarray, seat: int) -> np.ndarray:
    """Raw surplus ``u_seat(d) - threshold_seat`` — the quantity the Bayesian agent's step function tests. In
    the game's own utility units, so its scale varies across games."""
    return utility[:, seat] - thresholds[seat]


def _z_surplus_norm(utility: np.ndarray, thresholds: np.ndarray, seat: int) -> np.ndarray:
    """Surplus divided by the seat's BEST attainable surplus in this game, so ``z = 1`` is "this opponent's
    favourite deal", ``z = 0`` is exactly its reservation and ``z < 0`` is below it. Game-scale free, which is
    what lets one fitted curve pool across games of different utility magnitudes. Degenerate games (no deal
    strictly above reservation) fall back to raw surplus rather than dividing by ~0."""
    s = _z_surplus(utility, thresholds, seat)
    top = float(np.max(s)) if s.size else 0.0
    return s / top if top > 1e-9 else s


def _z_u_norm(utility: np.ndarray, thresholds: np.ndarray, seat: int) -> np.ndarray:
    """Min-max normalized own utility in ``[0, 1]``, ignoring the reservation entirely — the "how good is this
    for you, relative to the best and worst thing on offer" reading. Use when the fit found share-of-attainable
    a better predictor of LLM acceptance than distance-from-reservation."""
    u = utility[:, seat]
    lo, hi = float(np.min(u)), float(np.max(u))
    return (u - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(u)


#: The ``z`` conventions a fitted curve may declare. The fitted JSON MUST name one: a curve is meaningless
#: without the definition of the variable it is a function of, and silently guessing wrong would shift every
#: acceptance probability in the table without erroring anywhere.
Z_SPACES = {
    "surplus": _z_surplus,
    "surplus_norm": _z_surplus_norm,
    "u_norm": _z_u_norm,
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable logistic, evaluated piecewise so large-magnitude ``x`` cannot overflow ``exp``."""
    out = np.empty_like(x, dtype=float)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


# --------------------------------------------------------------------------------------------------------- #
# The fitted curve.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AcceptanceCurve:
    """One opponent model's fitted ``P(accept | z, rounds_left)``.

    Parameters
    ----------
    form : str
        Functional form. ``"step"`` = the Bayesian agent's own model (1.0 iff ``z >= 0``), kept so the
        calibrated policy can be driven back to exact Bayes equivalence for the regression test.
        ``"logistic"`` = ``sigmoid(a + b*z)``. ``"logistic_rounds"`` = ``sigmoid(a + b*z + c*r)`` where ``r`` is
        the round position (see ``rounds_feature``). ``"bins"`` = a piecewise-constant lookup over ``z``
        edges, optionally one row per ``rounds_left`` bin — the assumption-free form, at the cost of needing
        enough events per cell.
    params : dict
        Form-specific coefficients. logistic: ``a``, ``b`` (and ``c`` with rounds). bins: ``z_edges`` (K-1
        ascending interior edges), ``p`` (K probabilities, or a list of K-wide rows when ``r_edges`` is given)
        and optional ``r_edges``.
    rounds_feature : str
        What ``r`` means in the logistic forms. ``"rounds_left"`` (the default) = the raw integer count of
        rounds remaining AFTER the current one, 0 on the forced final — this is the fitting lane's convention
        and the default is deliberately the same as theirs, because a curve fitted on raw counts and evaluated
        on a fraction is wrong by a silent rescaling that nothing would raise on.
        ``"frac_elapsed"`` = ``1 - rounds_left/total`` in ``[0, 1]``, for a fit that chose scale-free pressure.
        Ignored by ``step``/``logistic``.
    p_min, p_max : float
        Clamp on the returned probability. The default floor/ceiling of 0/1 leaves the curve untouched; a small
        positive floor is worth setting when the fit is extrapolating far below the observed ``z`` range, since
        a hard 0 tells the expectimax that a deal is *impossible* rather than merely unlikely and can make the
        agent walk on a technicality.
    n_events, n_accepts : int
        Sample size behind the fit. Carried so a ladder result can never be quoted without the reader being
        able to see it was fit on 30 events.
    heldout_ece : float | None
        Held-out expected calibration error, if the fitting lane computed one.
    low_power : bool
        The fitting lane's own flag that this curve is not quotable — too few events, too few game clusters,
        or no variation in the outcome. Carried through so a consumer can REFUSE it rather than discover the
        problem in a results table. The fit that motivated this (``Qwen3-8B:thinking-on``) has 60 events across
        3 games and zero below-threshold votes.
    notes : str
        Free text from the fitting lane (run dirs, exclusions, caveats).
    """

    form: str
    params: dict = field(default_factory=dict)
    rounds_feature: str = "rounds_left"
    p_min: float = 0.0
    p_max: float = 1.0
    n_events: int = 0
    n_accepts: int = 0
    heldout_ece: float | None = None
    low_power: bool = False
    notes: str = ""

    _FORMS = ("step", "logistic", "logistic_rounds", "bins")

    def __post_init__(self):
        if self.form not in self._FORMS:
            raise ValueError(f"unknown acceptance-curve form {self.form!r}; choose one of {self._FORMS}")
        if self.rounds_feature not in ("frac_elapsed", "rounds_left"):
            raise ValueError(f"unknown rounds_feature {self.rounds_feature!r}")
        if not 0.0 <= self.p_min <= self.p_max <= 1.0:
            raise ValueError(f"need 0 <= p_min <= p_max <= 1; got {self.p_min}, {self.p_max}")
        need = {"logistic": ("a", "b"), "logistic_rounds": ("a", "b", "c"), "bins": ("z_edges", "p")}
        for k in need.get(self.form, ()):
            if k not in self.params:
                raise ValueError(f"form {self.form!r} needs params[{k!r}]")
        if self.form == "bins":
            edges = np.asarray(self.params["z_edges"], dtype=float)
            if edges.size and np.any(np.diff(edges) <= 0):
                raise ValueError("params['z_edges'] must be strictly ascending")
            p = np.asarray(self.params["p"], dtype=float)
            width = p.shape[-1]
            if width != edges.size + 1:
                raise ValueError(f"params['p'] last axis must be len(z_edges)+1 = {edges.size + 1}; got {width}")
            if "r_edges" in self.params:
                r_edges = np.asarray(self.params["r_edges"], dtype=float)
                if p.ndim != 2 or p.shape[0] != r_edges.size + 1:
                    raise ValueError("with params['r_edges'], params['p'] must be "
                                     f"(len(r_edges)+1, len(z_edges)+1) = ({r_edges.size + 1}, {width})")
            elif p.ndim != 1:
                raise ValueError("params['p'] must be 1-D unless params['r_edges'] is given")

    @property
    def is_step(self) -> bool:
        """Whether this curve IS the Bayesian agent's own step model (so a calibrated policy carrying only step
        curves must behave identically to :class:`BayesianRationalPolicy`)."""
        return self.form == "step"

    def _r(self, rounds_left: int, total_rounds: int) -> float:
        """The round covariate, per ``rounds_feature``. ``frac_elapsed`` needs a positive ``total_rounds``; a
        nonpositive one means the caller could not determine a deadline, and 0.0 (no pressure) is the reading
        that leaves the curve at its intercept rather than inventing pressure."""
        if self.rounds_feature == "rounds_left":
            return float(rounds_left)
        if total_rounds <= 0:
            return 0.0
        return float(np.clip(1.0 - rounds_left / total_rounds, 0.0, 1.0))

    def prob(self, z: np.ndarray, rounds_left: int = 1, total_rounds: int = 0) -> np.ndarray:
        """Vectorized ``P(accept)`` over an array of ``z`` values, clamped to ``[p_min, p_max]``.

        ``rounds_left`` is the number of rounds still playable INCLUDING the current one; ``total_rounds`` is
        the episode's deadline in the same units, needed only by the ``frac_elapsed`` rounds feature."""
        z = np.asarray(z, dtype=float)
        if self.form == "step":
            p = (z >= 0.0).astype(float)
        elif self.form == "logistic":
            p = _sigmoid(self.params["a"] + self.params["b"] * z)
        elif self.form == "logistic_rounds":
            r = self._r(rounds_left, total_rounds)
            p = _sigmoid(self.params["a"] + self.params["b"] * z + self.params["c"] * r)
        else:
            edges = np.asarray(self.params["z_edges"], dtype=float)
            table = np.asarray(self.params["p"], dtype=float)
            col = np.searchsorted(edges, z, side="right")
            if "r_edges" in self.params:
                r_edges = np.asarray(self.params["r_edges"], dtype=float)
                row = int(np.searchsorted(r_edges, self._r(rounds_left, total_rounds), side="right"))
                p = table[row][col]
            else:
                p = table[col]
        return np.clip(p, self.p_min, self.p_max)

    @classmethod
    def from_dict(cls, d: dict) -> "AcceptanceCurve":
        """Build from one model's JSON block, ignoring keys the schema does not define (the fitting lane is
        free to carry extra diagnostics alongside the coefficients)."""
        known = {"form", "params", "rounds_feature", "p_min", "p_max", "n_events", "n_accepts",
                 "heldout_ece", "low_power", "notes"}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class AcceptanceCurveSet:
    """A fitted curve per opponent model, plus the ``z`` convention they were all fit in.

    Parameters
    ----------
    z_space : str
        Which of :data:`Z_SPACES` the curves are functions of. Set by the fitting lane; the policy computes
        ``z`` the same way or the numbers mean nothing.
    curves : dict[str, AcceptanceCurve]
        Model id (as it appears in the lineup, e.g. ``"Qwen/Qwen3-8B"``) to its fitted curve.
    default : AcceptanceCurve | None
        Curve for a model with no entry of its own. ``None`` (the default) makes an unknown model an ERROR
        rather than a silent fallback — seating a calibrated agent against a model nobody fit a curve for is a
        design mistake, not a runtime condition to paper over.
    provenance : dict
        Whatever the fitting lane recorded about how these were produced (run dirs, episode counts, date).
    """

    z_space: str
    curves: dict[str, AcceptanceCurve]
    default: AcceptanceCurve | None = None
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.z_space not in Z_SPACES:
            raise ValueError(f"unknown z_space {self.z_space!r}; choose one of {sorted(Z_SPACES)}")

    @property
    def all_step(self) -> bool:
        """Whether every curve here (including the default) is a step function — i.e. this set drives
        :class:`CalibratedRationalPolicy` back to exact Bayes behaviour."""
        cs = list(self.curves.values()) + ([self.default] if self.default is not None else [])
        return bool(cs) and all(c.is_step for c in cs)

    def for_model(self, model_id: str) -> AcceptanceCurve:
        """The curve for ``model_id``, or ``default``. Raises :class:`KeyError` when neither exists, naming the
        models that ARE fit — a calibrated cell run against an uncalibrated opponent is uninterpretable, so
        this fails at seat-construction time rather than quietly reverting to the step model."""
        if model_id in self.curves:
            return self.curves[model_id]
        if self.default is not None:
            return self.default
        raise KeyError(f"no fitted acceptance curve for opponent model {model_id!r} and no default; "
                       f"fitted models are {sorted(self.curves)}")

    def z_of(self, utility: np.ndarray, thresholds: np.ndarray, seat: int) -> np.ndarray:
        """``z`` for every deal from ``seat``'s point of view, under this set's declared convention."""
        return Z_SPACES[self.z_space](utility, thresholds, seat)

    @classmethod
    def from_json(cls, path: str | Path) -> "AcceptanceCurveSet":
        """Load the fitting lane's artifact.

        Expected shape (extra keys are ignored, so the fitting lane can carry diagnostics)::

            {"schema_version": 1,
             "z_space": "surplus_norm",
             "models": {"Qwen/Qwen3-8B": {"form": "logistic_rounds", "params": {"a": .., "b": .., "c": ..},
                                          "n_events": 1234, "n_accepts": 456, "heldout_ece": 0.03}},
             "default": {...},                       # optional
             "provenance": {"run_dirs": [...], ...}} # optional
        """
        blob = json.loads(Path(path).read_text())
        if "models" not in blob or "z_space" not in blob:
            raise ValueError(f"{path}: acceptance-curve JSON needs top-level 'z_space' and 'models'")
        return cls(z_space=blob["z_space"],
                   curves={m: AcceptanceCurve.from_dict(d) for m, d in blob["models"].items()},
                   default=AcceptanceCurve.from_dict(blob["default"]) if blob.get("default") else None,
                   provenance=blob.get("provenance", {}))

    @classmethod
    def from_fit_artifact(cls, path: str | Path, *, spec: str = "base") -> "AcceptanceCurveSet":
        """Load the acceptance-curve fitting lane's NATIVE artifact
        (``schema == "rational_agents/acceptance_curves/v1"``), as written by
        ``experiments/rational_agents/self_benefit/fit_acceptance.py``.

        That artifact is organised around the fit rather than around the consumer: each responder carries
        several candidate ``specs`` plus validation blocks, coefficients are a flat
        ``[intercept, *slopes]`` list, and the regressors are named in ``base_features``. This adapter reads it
        as-is rather than asking the fitting lane to reshape its output — the artifact of record should stay
        the fitter's own.

        Parameters
        ----------
        path : str | Path
            The fitted JSON.
        spec : str
            Which candidate fit to consume. ``"base"`` (``logit p = b0 + b_z z + b_r rounds_left``) is the
            preregistered one and the default; ``"interaction"`` adds ``z * rounds_left``. Selecting a
            non-preregistered spec is a deliberate act and is recorded in ``provenance["spec"]``.

        The fit's ``z`` is ``(u_i(d) - tau_i) / (max_d' u_i(d') - tau_i)`` — this module's ``surplus_norm`` —
        and its ``rounds_left`` is the count AFTER the current round. Both are asserted against the artifact's
        own ``base_features`` so a change of regressors upstream fails loudly here instead of being evaluated
        under the old meaning.
        """
        blob = json.loads(Path(path).read_text())
        schema = blob.get("schema", "")
        if not schema.startswith("rational_agents/acceptance_curves/"):
            raise ValueError(f"{path}: not an acceptance-curve fit artifact (schema={schema!r})")
        models: dict[str, AcceptanceCurve] = {}
        for key, block in blob.get("models", {}).items():
            fit = block.get("specs", {}).get(spec)
            if fit is None:
                raise ValueError(f"{path}: responder {key!r} has no {spec!r} spec")
            feats, coef = list(fit.get("features", [])), list(fit["coef"])
            if len(coef) != len(feats) + 1:
                raise ValueError(f"{path}: responder {key!r} has {len(coef)} coefficients for "
                                 f"{len(feats)} features (expected intercept + one per feature)")
            if feats == ["z", "rounds_left"]:
                params = {"a": coef[0], "b": coef[1], "c": coef[2]}
                form = "logistic_rounds"
            elif feats == ["z"]:
                params, form = {"a": coef[0], "b": coef[1]}, "logistic"
            elif feats == []:
                params, form = {"a": coef[0], "b": 0.0}, "logistic"
            else:
                raise ValueError(f"{path}: responder {key!r} uses regressors {feats}, which this policy does "
                                 "not know how to evaluate; extend AcceptanceCurve before consuming it")
            val = block.get("validation", {}).get(spec, {}).get("logo_cv", {})
            models[key] = AcceptanceCurve(
                form=form, params=params, rounds_feature="rounds_left",
                n_events=int(block.get("n_events", 0)), n_accepts=int(block.get("n_accept", 0)),
                heldout_ece=val.get("ece"), low_power=bool(block.get("low_power", False)),
                notes=(f"spec={spec} brier={val.get('brier')} n_games={block.get('n_games')} "
                       f"n_games_is_the_real_power_number separated={fit.get('separated')} "
                       f"converged={fit.get('converged')} low_power={block.get('low_power', False)}"))
            if fit.get("separated"):
                # A separated fit has no finite optimum; the ridge is holding the coefficients down. The
                # numbers are usable but the reader must be told, so it goes in the notes AND is surfaced here.
                print(f"[calibrated] WARNING: fit for {key!r} reports separated=true (ridge-stabilised)")
        fallback = blob.get("fallback_model")
        return cls(z_space="surplus_norm", curves=models,
                   default=models.get(fallback) if fallback else None,
                   provenance={"artifact": str(path), "schema": schema, "spec": spec,
                               "generated_at": blob.get("generated_at"),
                               "invocation": blob.get("invocation"),
                               "events_path": blob.get("events_path"),
                               "population": blob.get("population"),
                               "fallback_model": fallback,
                               "n_events_total": blob.get("n_events_total")})

    @classmethod
    def vote_grain_from_fit_artifact(cls, path: str | Path) -> "AcceptanceCurveSet":
        """Build the **vote-conditional** curve set from the fit artifact's `empirical` block.

        WHY A SECOND GRAIN EXISTS. The fitted logistic is a **panel-grain** quantity: "next time this seat
        moves, does it accept this offer" — which folds in crowding and inattention, because a seat facing five
        standing offers can formally take at most one. Measured panel acceptance is 0.15-0.45. But the protocol
        ends in a **forced vote**, and among offers actually voted on, acceptance is ~0.99 (Qwen3-8B 0.992 over
        n=7,420; gemma 0.991 over n=8,971) — even *below* the voter's own reservation it is 0.81 and 0.96
        respectively. Feeding the panel curve into the endgame therefore tells the agent that closure is nearly
        impossible exactly where it is nearly certain, which is a large and one-directional error.

        No new fit is needed: the three vote-conditional rates the artifact already reports
        (``accept_rate_below_ir_when_voted`` for ``z < 0``, ``accept_rate_high_z_when_voted`` for ``z >= 0.5``,
        and ``accept_rate_when_voted`` over all votes) determine the middle bin exactly, since the overall rate
        is their count-weighted mixture. The result is a three-bin step in ``z`` per responder — assumption-free
        and reported rather than extrapolated.

        Use with :class:`CalibratedRationalPolicy`'s ``vote_curves`` argument, which applies it only in the
        endgame; during regular rounds the panel curve is the right object.
        """
        blob = json.loads(Path(path).read_text())
        curves: dict[str, AcceptanceCurve] = {}
        for key, block in blob.get("models", {}).items():
            e = block.get("empirical") or {}
            n_v, r_v = e.get("n_voted"), e.get("accept_rate_when_voted")
            if not n_v or r_v is None:
                continue
            n_lo, r_lo = e.get("n_below_ir_voted", 0) or 0, e.get("accept_rate_below_ir_when_voted")
            n_hi, r_hi = e.get("n_high_z_voted", 0) or 0, e.get("accept_rate_high_z_when_voted")
            r_lo = r_v if r_lo is None else r_lo
            r_hi = r_v if r_hi is None else r_hi
            n_mid = max(n_v - n_lo - n_hi, 0)
            # Solve the middle bin from the mixture identity rather than guessing it.
            mid = (n_v * r_v - n_lo * r_lo - n_hi * r_hi) / n_mid if n_mid > 0 else r_v
            p = [float(np.clip(r_lo, 0.0, 1.0)), float(np.clip(mid, 0.0, 1.0)), float(np.clip(r_hi, 0.0, 1.0))]
            curves[key] = AcceptanceCurve(
                form="bins", params={"z_edges": [0.0, 0.5], "p": p},
                n_events=int(n_v), n_accepts=int(round(n_v * r_v)),
                notes=(f"vote-conditional empirical bins from the fit artifact: z<0 {p[0]:.3f} "
                       f"(n={n_lo}), 0<=z<0.5 {p[1]:.3f} (n={n_mid}), z>=0.5 {p[2]:.3f} (n={n_hi})"))
        return cls(z_space="surplus_norm", curves=curves,
                   default=curves.get(blob.get("fallback_model") or ""),
                   provenance={"artifact": str(path), "grain": "vote_conditional",
                               "derivation": "empirical vote-conditional rates, middle bin solved from the "
                                             "count-weighted mixture identity"})

    @classmethod
    def step(cls, z_space: str = "surplus") -> "AcceptanceCurveSet":
        """The degenerate set every model of which is the Bayesian agent's own step model. Exists for the
        equivalence regression test and as a sanity control cell (a "calibrated" run that must reproduce the
        Bayes replication exactly)."""
        return cls(z_space=z_space, curves={}, default=AcceptanceCurve(form="step"),
                   provenance={"note": "synthetic step control, not a fit"})


# --------------------------------------------------------------------------------------------------------- #
# The policy.
# --------------------------------------------------------------------------------------------------------- #
class CalibratedRationalPolicy(BayesianRationalPolicy):
    """:class:`BayesianRationalPolicy` with its opponent acceptance model replaced by fitted behavioural
    curves. Optimal stopping, expectimax best-response, the IR floor on its own acceptances and the
    walk-if-hopeless rule are inherited unchanged.

    Parameters
    ----------
    curves : AcceptanceCurveSet
        The fitted curves and their ``z`` convention.
    opponent_model : str
        Model id filling the OTHER seats, used to look up the curve. The lineup knows this (the run's
        ``--models``); the policy cannot infer it from the state, which is why it is required.
    seat_models : dict[int, str] | None
        Per-seat override when the table is heterogeneous — seat index to model id. Seats absent here use
        ``opponent_model``. Supply this for any mixed-model lineup; with a homogeneous lineup leave it ``None``.
    discount, walk_if_hopeless, name
        As :class:`BayesianRationalPolicy`.

    Attributes
    ----------
    last_path : str | None
        ``"calibrated"`` or ``"belief"`` — which acceptance model the most recent turn actually used. Set every
        turn so a run can be AUDITED for whether the calibrated path was live, instead of the cell's label
        being taken on trust. A full-info run whose policy reports ``"belief"`` is mislabelled.
    """

    def __init__(self, *, curves: AcceptanceCurveSet, opponent_model: str,
                 seat_models: dict[int, str] | None = None, vote_curves: AcceptanceCurveSet | None = None,
                 endgame_rounds: int = 0, discount: float | None = None,
                 walk_if_hopeless: bool = True, name: str = "calibrated-rational"):
        super().__init__(discount=discount, walk_if_hopeless=walk_if_hopeless, name=name)
        self.curves = curves
        self.opponent_model = str(opponent_model)
        self.seat_models = dict(seat_models or {})
        self.vote_curves = vote_curves
        self.endgame_rounds = int(endgame_rounds)
        self.last_path: str | None = None
        # Fail at construction, not mid-episode: resolving the curve now turns "nobody fit this opponent" into
        # a launch-time error instead of a crash 40 minutes into a GPU cell.
        for cs in (self.curves, self.vote_curves):
            if cs is None:
                continue
            cs.for_model(self.opponent_model)
            for m in self.seat_models.values():
                cs.for_model(m)

    def model_for_seat(self, seat: int) -> str:
        """Model id seated at ``seat`` — the per-seat override if given, else ``opponent_model``."""
        return self.seat_models.get(int(seat), self.opponent_model)

    def _accept_prob_table(self, state, tables):
        """``(D, n)`` acceptance probabilities with each opponent column read off its fitted curve.

        Full info only. Without ``state.tables`` there are no opponent utilities to evaluate ``z`` on, so this
        defers to the inherited belief-oracle path (and says so on ``last_path``) rather than fabricating a
        calibrated table from a posterior it was not fit against.

        The own column is forced to 1.0 exactly as the parent does: the table answers "will the OTHERS sign
        this", and this seat's own willingness is decided separately by the IR-floored optimal-stopping rule in
        ``act``.

        The table is SEEDED with the parent's step model and then overwritten column-by-column for each
        modelled opponent, rather than built from scratch. That is deliberate: it means any seat that is
        neither this one nor a listed opponent keeps exactly the value the Bayesian agent would have given it,
        so a set of step curves reproduces the parent's table bit-for-bit and the equivalence regression test
        has no gap to hide in."""
        if state.tables is None:
            self.last_path = "belief"
            return super()._accept_prob_table(state, tables)
        total = int(getattr(state, "deadline", 0)) + 1
        # The FIT's convention: rounds remaining AFTER this one, 0 on the forced final. This is deliberately
        # NOT the `max(deadline - round + 1, 1)` used by the inherited optimal-stopping code — that one counts
        # the current round and floors at 1 because a reservation over zero remaining rounds is meaningless.
        # They differ by one, and on the forced final by the difference between 0 and 1, which is exactly the
        # turn where deadline pressure matters most. Evaluating a fitted coefficient against the wrong one is
        # a silent off-by-one in every acceptance probability, so the two are kept visibly separate.
        r_left = max(int(state.deadline) + 1 - int(state.round), 0)
        # ENDGAME GRAIN SWITCH. The panel curve answers "next time this seat moves, does it take this offer",
        # which folds in crowding — a seat with five standing offers can formally take at most one. The
        # protocol, though, ends in a FORCED vote where acceptance is ~0.99 even below the voter's own
        # reservation. Applying the panel curve there tells the agent closure is near-impossible exactly where
        # it is near-certain. When `vote_curves` is supplied, the last `endgame_rounds` rounds (and the forced
        # final itself, r_left == 0) are priced at the vote grain instead.
        #
        # LIMITATION, stated because it bounds the claim: the best-response oracle takes ONE static
        # acceptance table per call, so this makes the agent vote-aware once it ARRIVES in the endgame, not in
        # anticipation of it from earlier rounds. It therefore tests vote-aware endgame play, which is the
        # highest-leverage moment (the forced-final proposal is the last thing anyone votes on), rather than a
        # fully round-indexed opponent model.
        use_vote = self.vote_curves is not None and r_left <= self.endgame_rounds
        active = self.vote_curves if use_vote else self.curves
        self.last_path = "calibrated-vote" if use_vote else "calibrated"
        ap = super()._accept_prob_table(state, tables)
        for opp in state.opponents:
            z = active.z_of(tables.utility, tables.thresholds, int(opp))
            curve = active.for_model(self.model_for_seat(int(opp)))
            ap[:, int(opp)] = curve.prob(z, rounds_left=r_left, total_rounds=total)
        ap[:, state.seat] = 1.0
        return ap

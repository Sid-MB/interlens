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

# [rational_agents scaffold: oracles-strategies] 2026-07-23
"""Bayesian (and frequency-model fallback) belief oracle over an enumerated opponent-type grid.

Literature grounding:

- **Hypothesis space** = issue-weight rankings x per-issue evaluator shapes x reservation (tau) levels —
  Hindriks & Tykhonov, "Opponent modelling in automated multi-issue negotiation using Bayesian learning,"
  AAMAS 2008, pp. 331-338. https://research.vu.nl/en/publications/opponent-modelling-in-automated-multi-issue-negotiation-using-bay
  Their **separate-learning scalability trick** (learn weight-hypotheses and evaluator-hypotheses
  independently, each conditioned on the mean of the others) is implemented as ``mode="separate"`` so the
  full product grid never has to be materialized when it is large.
- **Concession likelihood** ``P(b_t | h, b_{t-1}) proportional to exp(-delta+ / 2 sigma^2)`` where
  ``delta+`` is the *positive part* of the opponent's own-utility increase ``h(b_t) - h(b_{t-1})`` — Chang &
  Fujita, "A Scalable Opponent Model Using Bayesian Learning ...," AAMAS 2023, pp. 2487-2489, Eqs. 2-5.
  https://www.southampton.ac.uk/~eg/AAMAS2023/pdfs/p2487.pdf  Hypotheses under which the opponent's *own*
  utility went UP are penalized (a rational opponent concedes, i.e. weakly lowers its own demanded utility).
- **Frequency model** cheap fallback (issue-stability weights + option-frequency values) — HardHeaded /
  Baarslag, Hendrikx, Hindriks & Jonker, "Learning about the opponent ...," JAAMAS 30(5):849-898, 2016,
  which repeatedly finds simple frequency heuristics often beat Bayesian models.
- **Soft / damped updates** (per-observation likelihood tempered by ``lam < 1`` + a uniform floor) so a
  deceptive / adversarial trace cannot catastrophically corrupt the posterior — Hua et al., "Game-Theoretic
  LLM ...," arXiv:2411.05990, Remark 1 (exact-rationality belief updates are corrupted by deception).

Multilateral handling: one independent model per opponent (the standard independence assumption).
"""
from __future__ import annotations

import collections
import functools
import itertools
from dataclasses import dataclass

import numpy as np

from .oracle_context import (Deal, Oracle, issue_sizes, make_verdict, normalize, seat_index)


# --------------------------------------------------------------------------------------------------------- #
# Opponent type: an additive utility hypothesis on the [0, 1] scale (weights x shaped evaluators) + a tau.
# --------------------------------------------------------------------------------------------------------- #
_SHAPES = ("uphill", "downhill", "triangular")


def _evaluator(shape: str, n_options: int) -> np.ndarray:
    """Per-option evaluation values in ``[0, 1]`` for one issue under a shape hypothesis (Hindriks-Tykhonov
    downhill/uphill/triangular). Length-1 issues map to a constant 1.0."""
    if n_options <= 1:
        return np.ones(1)
    k = np.arange(n_options, dtype=float)
    if shape == "uphill":
        return k / (n_options - 1)
    if shape == "downhill":
        return 1.0 - k / (n_options - 1)
    if shape == "triangular":
        mid = (n_options - 1) / 2.0
        d = np.abs(k - mid)
        return 1.0 - d / d.max()
    raise ValueError(f"unknown evaluator shape {shape!r}")


@dataclass(frozen=True)
class OpponentType:
    """One enumerated hypothesis about an opponent: normalized issue ``weights`` (sum 1), a per-issue
    evaluator ``shapes`` tuple, and a reservation ``threshold`` on the induced ``[0, 1]`` utility scale.

    ``utility(deal) = sum_j weights[j] * evaluator(shapes[j])[deal[j]]`` lies in ``[0, 1]``; ``accepts(deal)``
    iff that utility is at least ``threshold``."""

    weights: tuple
    shapes: tuple
    threshold: float
    option_counts: tuple

    def evaluator_table(self) -> list:
        """Per-issue option-value arrays (cached-free; cheap)."""
        return [_evaluator(self.shapes[j], self.option_counts[j]) for j in range(len(self.shapes))]

    def utility(self, deal: Deal) -> float:
        """Additive utility of ``deal`` in ``[0, 1]``."""
        tabs = self.evaluator_table()
        return float(sum(self.weights[j] * tabs[j][deal[j]] for j in range(len(deal))))

    def accepts(self, deal: Deal) -> bool:
        """Whether a myopically-rational opponent of this type would accept ``deal``."""
        return self.utility(deal) >= self.threshold


def _weight_profiles(n_issues: int, max_rankings: int, seed: int) -> list[tuple]:
    """Weight vectors from issue *rankings* (relative importance): each ranking (a permutation of issues) is
    mapped to linearly-decaying weights ``propto (J - rank)`` then normalized. All ``J!`` permutations when
    small; otherwise a deterministic sample of ``max_rankings`` of them (plus the identity)."""
    perms = list(itertools.permutations(range(n_issues)))
    if len(perms) > max_rankings:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(perms), size=max_rankings - 1, replace=False)
        chosen = [perms[0]] + [perms[i] for i in idx]
    else:
        chosen = perms
    profiles = []
    base = np.arange(n_issues, 0, -1, dtype=float)  # J, J-1, ..., 1 by rank position
    for perm in chosen:
        w = np.zeros(n_issues)
        for rank, issue in enumerate(perm):
            w[issue] = base[rank]
        profiles.append(tuple(w / w.sum()))
    return profiles


def build_type_grid(option_counts, tau_levels=(0.35, 0.55, 0.75), max_rankings: int = 24,
                    seed: int = 0) -> list:
    """Enumerate the opponent-type hypothesis grid = weight-profiles x shape-assignments x tau-levels.

    Parameters
    ----------
    option_counts : sequence[int]
        Per-issue option counts ``(O_1, ..., O_J)``.
    tau_levels : sequence[float]
        Candidate reservation thresholds on the ``[0, 1]`` utility scale.
    max_rankings : int
        Cap on the number of weight-ranking hypotheses (all ``J!`` if fewer, else a deterministic sample).
    seed : int
        Seed for the ranking sample (determinism).
    """
    option_counts = tuple(int(x) for x in option_counts)
    J = len(option_counts)
    weights = _weight_profiles(J, max_rankings, seed)
    shape_assignments = list(itertools.product(_SHAPES, repeat=J))
    grid = []
    for w in weights:
        for shapes in shape_assignments:
            for tau in tau_levels:
                grid.append(OpponentType(w, shapes, float(tau), option_counts))
    return grid


def _build_arrays(types, option_counts):
    """Vectorized grid tables from a types list: ``W`` (T, J) weights, per-issue evaluator matrices ``S_j``
    (T, O_j), ``TAU`` (T,), and each type's ideal utility (T,). The arrays are marked read-only so a single
    prepared grid can be shared across many ``BeliefState`` instances (only the per-instance posterior is
    mutable) — the hot path only reads them."""
    T = len(types)
    J = len(option_counts)
    W = np.array([t.weights for t in types], dtype=float)
    TAU = np.array([t.threshold for t in types], dtype=float)
    ev_cache: dict = {}
    S = []
    for j in range(J):
        Oj = option_counts[j]
        col = np.empty((T, Oj), dtype=float)
        for i, t in enumerate(types):
            key = (t.shapes[j], Oj)
            e = ev_cache.get(key)
            if e is None:
                e = _evaluator(t.shapes[j], Oj)
                ev_cache[key] = e
            col[i] = e
        col.flags.writeable = False
        S.append(col)
    ideal = sum(W[:, j] * S[j].max(axis=1) for j in range(J))
    for arr in (W, TAU, ideal):
        arr.flags.writeable = False
    return W, tuple(S), TAU, ideal


@functools.lru_cache(maxsize=64)
def _prepared_default_grid(option_counts: tuple, tau_levels: tuple, max_rankings: int, seed: int):
    """The default opponent-type grid + its vectorized arrays + the precomputed type-by-deal acceptance
    matrix, built ONCE per option-count signature and cached (immutable, shared read-only).

    This is what makes the composed Bayesian agent cheap to run each turn: (1) a fresh ``BeliefState`` per
    turn/opponent reuses the prepared grid instead of rebuilding ~10^4 frozen ``OpponentType`` objects, and
    (2) ``accept_matrix[t, d] = 1 iff type t accepts deal d`` is computed once over the full enumerated deal
    space, so per-turn acceptance probabilities over ALL deals collapse to a single ``posterior @
    accept_matrix`` matmul instead of rebuilding the (|types| x |D|) utility tensor per opponent per turn.
    ``accept_matrix`` is float64 so the per-turn ``posterior(float64) @ accept_matrix`` is a single BLAS gemv
    (a float32 store would force a per-call upcast that bypasses BLAS). Safe to share — nothing is mutated.

    The underlying ``(|types| x |D|)`` utility tensor the two derived matrices are cut from is returned as well
    (:meth:`BeliefState.type_utility_matrix`), since it is already built here and a belief-accuracy diagnostic
    needs the utilities themselves rather than their threshold indicator or their rescaled surplus."""
    types = tuple(build_type_grid(option_counts, tau_levels=tau_levels, max_rankings=max_rankings, seed=seed))
    W, S, TAU, ideal = _build_arrays(types, option_counts)
    deals_arr = np.array(list(itertools.product(*[range(o) for o in option_counts])), dtype=int)  # (D, J)
    U_all = sum(W[:, j][:, None] * S[j][:, deals_arr[:, j]] for j in range(len(option_counts)))    # (T, D)
    accept = (U_all >= TAU[:, None]).astype(np.float64)                                            # (T, D)
    accept.flags.writeable = False
    # Per-type normalized surplus, the fairness objective's coordinate: clip(u - tau, 0) / (that type's best
    # attainable surplus). Cached beside ``accept`` for the same reason — a fairness-seeking policy needs the
    # posterior-expected value over ALL deals every turn, which is one gemv against this instead of rebuilding
    # the (|types| x |D|) tensor per opponent per turn.
    Xt = np.clip(U_all - TAU[:, None], 0.0, None)                                                  # (T, D)
    bt = Xt.max(axis=1)
    znorm = (Xt / np.where(bt > 0.0, bt, 1.0)[:, None]).astype(np.float64)                         # (T, D)
    znorm.flags.writeable = False
    U_all.flags.writeable = False
    return types, W, S, TAU, ideal, accept, znorm, U_all


# --------------------------------------------------------------------------------------------------------- #
# Frequency model (cheap control belief) — HardHeaded / Baarslag JAAMAS 2016.
# --------------------------------------------------------------------------------------------------------- #
class FrequencyModel:
    """Count-based opponent model: issue *stability* -> weights (an issue whose chosen option stays fixed
    across consecutive offers is important), option *frequency* -> values (a frequently-offered option is
    preferred). Induces a utility function; ``update(offer)`` is O(J). Often competitive with Bayes."""

    def __init__(self, option_counts):
        self.option_counts = tuple(int(x) for x in option_counts)
        self.J = len(self.option_counts)
        self._weight = np.ones(self.J)
        self._value = [np.ones(o) for o in self.option_counts]
        self._last: Deal | None = None

    def update(self, offer: Deal) -> "FrequencyModel":
        """Fold one observed opponent offer into the counts."""
        for j in range(self.J):
            self._value[j][offer[j]] += 1.0
            if self._last is not None and self._last[j] == offer[j]:
                self._weight[j] += 1.0
        self._last = tuple(int(x) for x in offer)
        return self

    def weights(self) -> np.ndarray:
        """Normalized issue weights."""
        return self._weight / self._weight.sum()

    def utility(self, deal: Deal) -> float:
        """Induced utility of ``deal`` in ``[0, 1]`` (per-issue value normalized to its max)."""
        w = self.weights()
        return float(sum(w[j] * (self._value[j][deal[j]] / self._value[j].max()) for j in range(self.J)))

    def copy(self) -> "FrequencyModel":
        """An independent model with the same counts — the fold state a cached replay hands out."""
        clone = FrequencyModel(self.option_counts)
        clone._weight = self._weight.copy()
        clone._value = [v.copy() for v in self._value]
        clone._last = self._last
        return clone


# --------------------------------------------------------------------------------------------------------- #
# BeliefState: one opponent's damped Bayesian posterior over the type grid (joint or separate-learning).
# --------------------------------------------------------------------------------------------------------- #
class BeliefState:
    """A single opponent's belief model: a damped Bayesian posterior over an enumerated ``OpponentType``
    grid, with an optional Hindriks-Tykhonov *separate-learning* factorization for large grids and a
    frequency-model shadow kept in parallel as the cheap control readout.

    Parameters
    ----------
    option_counts : sequence[int]
        Per-issue option counts.
    types : list[OpponentType] | None
        Explicit grid (else built via ``build_type_grid``).
    sigma : float
        Concession-likelihood scale ``sigma`` (Chang-Fujita); larger = softer discrimination.
    lam : float
        Damping ``lambda in (0, 1]`` applied to each observation's log-likelihood (``1`` = plain Bayes);
        ``< 1`` tempers updates so a deceptive trace cannot collapse the posterior.
    floor : float
        Uniform mass mixed into the posterior after every update (robustness; keeps every type reachable).
    mode : str
        ``"joint"`` (full product posterior) or ``"separate"`` (factor into weight / shape / tau marginals,
        each scored against the mean of the others — the AAMAS-2008 scalability trick). ``"auto"`` picks
        ``separate`` when the grid exceeds ``joint_cap``.
    anchor_first : bool
        If True, the first observed offer is scored by how far it sits below each type's *ideal* utility
        (a rational opener bids near its max), which sharpens weight identification early.
    joint_cap : int
        Grid-size threshold for ``mode="auto"``.
    """

    def __init__(self, option_counts, types=None, *, sigma: float = 0.25, lam: float = 1.0,
                 floor: float = 1e-3, mode: str = "auto", anchor_first: bool = True,
                 joint_cap: int = 20000, seed: int = 0, tau_levels: tuple = (0.35, 0.55, 0.75),
                 max_rankings: int = 24):
        self.option_counts = tuple(int(x) for x in option_counts)
        if types is None:
            # reuse the cached immutable default grid + arrays + acceptance matrix (shared read-only)
            (grid, self._W, self._S, self._TAU, self._ideal, self._accept_matrix,
             self._znorm_matrix, self._utility_matrix) = _prepared_default_grid(
                self.option_counts, tuple(tau_levels), int(max_rankings), int(seed))
            self.types = list(grid)
        else:
            self.types = list(types)
            self._W, S, self._TAU, self._ideal = _build_arrays(self.types, self.option_counts)
            self._S = list(S)
            # small custom grid: acceptance, normalized surplus and the utility tensor are computed on the fly
            self._accept_matrix = None
            self._znorm_matrix = None
            self._utility_matrix = None
        self.sigma = float(sigma)
        self.lam = float(lam)
        self.floor = float(floor)
        self.anchor_first = bool(anchor_first)
        if mode == "auto":
            mode = "separate" if len(self.types) > joint_cap else "joint"
        self.mode = mode
        self._logpost = np.zeros(len(self.types))  # uniform prior in log space (per-instance, mutable)
        self._freq = FrequencyModel(self.option_counts)
        self._last: Deal | None = None
        self._renormalize()

    # -- likelihood ---------------------------------------------------------------------------------------
    def _type_utils(self, deal: Deal) -> np.ndarray:
        """Utility of ``deal`` under every type (vectorized over the grid)."""
        return sum(self._W[:, j] * self._S[j][:, deal[j]] for j in range(len(deal)))

    def _ideal_utils(self) -> np.ndarray:
        """Exact per-type ideal (max) utility for an additive type: ``sum_j w_j * max_k eval_j[k]``."""
        return self._ideal

    def observe(self, offer: Deal) -> "BeliefState":
        """Update the posterior from one observed opponent offer (a proposed ``Deal``)."""
        offer = tuple(int(x) for x in offer)
        self._freq.update(offer)
        u_now = self._type_utils(offer)
        if self._last is None:
            if self.anchor_first:
                ideal = self._ideal_utils()
                delta_pos = np.clip(ideal - u_now, 0.0, None)   # opener far below ideal is unlikely
                loglik = -delta_pos / (2 * self.sigma ** 2)
            else:
                loglik = np.zeros(len(self.types))
        else:
            u_prev = self._type_utils(self._last)
            delta_pos = np.clip(u_now - u_prev, 0.0, None)      # own-utility went UP => penalize (Eqs 2-5)
            loglik = -delta_pos / (2 * self.sigma ** 2)
        self._logpost = self._logpost + self.lam * loglik
        self._last = offer
        self._renormalize()
        return self

    def observe_response(self, deal: Deal, accepted: bool, *, reliability: float = 0.75,
                         strength: float = 0.35) -> "BeliefState":
        """Soft-update from an opponent's public accept/reject response to ``deal``.

        A type predicts acceptance iff the deal clears its reservation threshold.  ``reliability`` is the
        probability that the observed response follows that myopic prediction; values below 1 explicitly
        allow strategic rejection, mistakes, and cheap-talk inconsistency.  ``strength`` tempers this evidence
        relative to a self-authored proposal, because a vote is informative about the threshold but much less
        diagnostic of the opponent's complete preference ordering.

        The update is deliberately soft and implementable: it consumes only a public formal response and the
        referenced public deal, never the opponent's hidden score sheet.
        """
        if not 0.5 < reliability < 1.0:
            raise ValueError("reliability must lie strictly between 0.5 and 1")
        if not 0.0 < strength <= 1.0:
            raise ValueError("strength must lie in (0, 1]")
        predicted_accept = self._type_utils(tuple(int(x) for x in deal)) >= self._TAU
        matches = predicted_accept if accepted else ~predicted_accept
        likelihood = np.where(matches, reliability, 1.0 - reliability)
        self._logpost = self._logpost + self.lam * float(strength) * np.log(likelihood)
        self._renormalize()
        return self

    def _renormalize(self):
        self._logpost -= self._logpost.max()
        p = np.exp(self._logpost)
        p = normalize(p, floor=self.floor)
        self._logpost = np.log(np.clip(p, 1e-300, None))
        self._post = p

    # -- readouts -----------------------------------------------------------------------------------------
    def posterior(self) -> np.ndarray:
        """Posterior probability vector aligned with ``self.types``. Under ``mode="separate"`` this is the
        product-of-marginals reconstruction (weights, shapes, tau treated independent)."""
        if self.mode == "joint":
            return self._post
        return self._separate_posterior()

    def _separate_posterior(self) -> np.ndarray:
        """Hindriks-Tykhonov factorization: collapse the joint log-likelihood into per-factor marginals and
        recombine as an independent product, so effective support is |weights| + |shapes*| + |tau| rather
        than their product. (The stored ``_logpost`` is over the full grid; here we marginalize it.)"""
        keys_w = [t.weights for t in self.types]
        keys_s = [t.shapes for t in self.types]
        keys_t = [t.threshold for t in self.types]
        marg = {}
        for factor, keys in (("w", keys_w), ("s", keys_s), ("t", keys_t)):
            uniq = {}
            for k, lp in zip(keys, self._logpost):
                uniq.setdefault(k, []).append(lp)
            marg[factor] = {k: np.logaddexp.reduce(v) for k, v in uniq.items()}
        recomb = np.array([marg["w"][kw] + marg["s"][ks] + marg["t"][kt]
                           for kw, ks, kt in zip(keys_w, keys_s, keys_t)])
        recomb -= recomb.max()
        return normalize(np.exp(recomb), floor=self.floor)

    def map_type(self) -> OpponentType:
        """Maximum-a-posteriori opponent type."""
        return self.types[int(np.argmax(self.posterior()))]

    def induced_distribution(self):
        """The induced distribution over ``(utility_fn, threshold)``: a list of ``(OpponentType, prob)``."""
        return list(zip(self.types, self.posterior()))

    def expected_utility(self, deal: Deal) -> float:
        """Posterior-mean opponent utility of ``deal``."""
        return float(self.posterior() @ self._type_utils(deal))

    def accept_prob(self, deal: Deal) -> float:
        """Posterior probability the opponent accepts ``deal`` (mass of types whose utility >= their tau)."""
        return float(self.posterior() @ (self._type_utils(deal) >= self._TAU).astype(float))

    def accept_prob_matrix(self, deals_arr: np.ndarray) -> np.ndarray:
        """Vectorized ``accept_prob`` for a whole batch of deals at once: ``deals_arr`` is the ``(D, J)`` int
        option-index array (``GameTables.deals_arr``); returns a ``(D,)`` acceptance-probability vector.

        When the deal batch is the full enumerated space (the common case — the arena passes all deals), this
        reuses the precomputed cached ``accept_matrix`` and collapses to a single ``posterior @ accept_matrix``
        matmul (the expensive (T x D) utility tensor is built ONCE per game, not per opponent per turn).
        Otherwise it builds the tensor on the fly for the given deal subset."""
        if self._accept_matrix is not None and self._accept_matrix.shape[1] == deals_arr.shape[0]:
            return self.posterior() @ self._accept_matrix          # cached full-space acceptance
        U = sum(self._W[:, j][:, None] * self._S[j][:, deals_arr[:, j]] for j in range(deals_arr.shape[1]))
        return self.posterior() @ (U >= self._TAU[:, None])

    def type_thresholds(self) -> np.ndarray:
        """The ``(|types|,)`` reservation ``tau`` of every grid type, aligned with ``self.types`` (read-only on
        the shared default grid). The vector form of the per-type ``threshold`` attribute, exposed so a
        diagnostic can compare a whole grid against a known reservation without rebuilding it from the
        dataclasses."""
        return self._TAU

    def type_utility_matrix(self, deals_arr: np.ndarray) -> np.ndarray:
        """The ``(|types|, D)`` per-type utility tensor for a batch of deals: entry ``[t, d]`` is type ``t``'s
        ``[0, 1]``-scale utility of deal ``d``.

        The raw quantity :meth:`accept_prob_matrix` thresholds and :meth:`expected_normalized_surplus_matrix`
        rescales, exposed because a *diagnostic* needs the utilities themselves — posterior-expected opponent
        utility is ``posterior() @ type_utility_matrix(...)``, one gemv. Returns the cached read-only tensor
        when the batch is the full enumerated space (the common case) and builds it on the fly otherwise, so
        the two paths agree numerically."""
        if self._utility_matrix is not None and self._utility_matrix.shape[1] == deals_arr.shape[0]:
            return self._utility_matrix
        return sum(self._W[:, j][:, None] * self._S[j][:, deals_arr[:, j]] for j in range(deals_arr.shape[1]))

    def expected_normalized_surplus_matrix(self, deals_arr: np.ndarray) -> np.ndarray:
        """Posterior-expected **normalized surplus** for a whole batch of deals: ``deals_arr`` is the ``(D, J)``
        int option-index array (``GameTables.deals_arr``); returns a ``(D,)`` vector in ``[0, 1]``.

        Per candidate type, the normalized surplus of a deal is ``clip(u_type(d) - tau_type, 0)`` divided by
        that type's best attainable surplus, so every type contributes on a common ``[0, 1]`` scale regardless
        of the point scale it implies; the readout is then the posterior mixture of those. This is the
        opponent-side input the fairness objective needs (``fairness.expected_objective``) and is the exact
        analogue of :meth:`accept_prob_matrix`, which mixes the 0/1 *indicator* of the same surplus being
        positive — this mixes its magnitude.

        Uses the cached type-by-deal matrix when the batch is the full enumerated space (one gemv), and builds
        the tensor on the fly otherwise. Both paths normalize by the type's ideal surplus over the WHOLE deal
        space (``ideal - tau``, exact for an additive type) rather than over whatever subset was passed, so a
        partial batch returns the same numbers as the corresponding slice of a full one."""
        if self._znorm_matrix is not None and self._znorm_matrix.shape[1] == deals_arr.shape[0]:
            return self.posterior() @ self._znorm_matrix
        U = sum(self._W[:, j][:, None] * self._S[j][:, deals_arr[:, j]] for j in range(deals_arr.shape[1]))
        X = np.clip(U - self._TAU[:, None], 0.0, None)
        b = np.clip(self._ideal - self._TAU, 0.0, None)
        return self.posterior() @ (X / np.where(b > 0.0, b, 1.0)[:, None])

    def threshold_distribution(self):
        """Posterior distribution over the opponent's reservation ``tau``: ``{tau: prob}``."""
        p = self.posterior()
        out: dict = {}
        for t, pi in zip(self.types, p):
            out[t.threshold] = out.get(t.threshold, 0.0) + float(pi)
        return out

    def frequency_utility(self, deal: Deal) -> float:
        """The cheap frequency-model readout of the opponent's utility of ``deal`` (control comparison)."""
        return self._freq.utility(deal)

    def copy(self) -> "BeliefState":
        """An independent belief with the same posterior, sharing the immutable type grid.

        Only the fold state is duplicated (log-posterior, posterior, last observed offer, frequency counts);
        the grid arrays and the cached type-by-deal matrices are read-only and shared, so a copy costs two
        ``|types|`` vectors rather than a grid rebuild. This is what :func:`replay_belief` hands callers, so a
        cached posterior can never be mutated by whoever received it."""
        clone = object.__new__(BeliefState)
        clone.__dict__.update(self.__dict__)
        clone.types = self.types                 # the shared immutable grid (never mutated)
        clone._logpost = self._logpost.copy()
        clone._post = self._post.copy()
        clone._freq = self._freq.copy()
        clone._last = self._last
        return clone


# --------------------------------------------------------------------------------------------------------- #
# Cached incremental replay: the same offer prefix is folded ONCE per process, not once per turn.
# --------------------------------------------------------------------------------------------------------- #
#: How many distinct offer-prefix posteriors to keep. Each entry costs two ``|types|`` float64 vectors (~93 KB
#: on the default five-seat grid), so the default is a few hundred MB at most — a deliberate memory-for-CPU
#: trade. Only the IMMEDIATELY preceding prefix is needed to extend a sequence by one offer, and that entry is
#: the most recently used, so a modest cache serves many concurrent episodes; raise it only if a profile shows
#: prefix misses.
REPLAY_CACHE_ENTRIES = 4096

_REPLAY_CACHE: "collections.OrderedDict[tuple, BeliefState]" = collections.OrderedDict()


def replay_belief(option_counts, offers, **kwargs) -> BeliefState:
    """A :class:`BeliefState` that has observed ``offers`` in order — reusing the longest cached prefix.

    ``observe`` is a pure left fold: the state after ``[d1 ... dk]`` depends on nothing but that sequence, so
    replaying a prefix and then folding in the remaining offers gives *exactly* the state a from-scratch
    replay would (same operations, same order, same float64). A negotiation turn extends its opponent's offer
    list by at most one entry, so the cached prefix is almost always all but the last offer, and each turn
    folds ONE observation instead of the whole history — which is what stops a seat's per-turn belief cost
    growing with the round number.

    Returns a private :meth:`BeliefState.copy` every time, so the caller may mutate or further ``observe`` on
    the result without touching the cache. Grid-identity ``kwargs`` (``sigma``/``lam``/``floor``/``mode``/
    ``anchor_first``/``seed``/``tau_levels``/``max_rankings``) are part of the cache key; passing an explicit
    ``types=`` grid bypasses the cache entirely, since a caller-supplied grid has no stable identity.
    """
    offers = tuple(tuple(int(x) for x in d) for d in offers)
    option_counts = tuple(int(x) for x in option_counts)
    if kwargs.get("types") is not None:
        state = BeliefState(option_counts, **kwargs)
        for deal in offers:
            state.observe(deal)
        return state
    kwargs.pop("types", None)
    ident = (option_counts, tuple(sorted((k, tuple(v) if isinstance(v, (list, tuple)) else v)
                                         for k, v in kwargs.items())))
    for cut in range(len(offers), -1, -1):
        hit = _REPLAY_CACHE.get((ident, offers[:cut]))
        if hit is not None:
            _REPLAY_CACHE.move_to_end((ident, offers[:cut]))
            state = hit.copy()
            break
    else:                                        # nothing cached, not even the empty prefix
        cut, state = 0, BeliefState(option_counts, **kwargs)
    for k in range(cut, len(offers)):
        state.observe(offers[k])
        _REPLAY_CACHE[(ident, offers[:k + 1])] = state.copy()
    if cut == 0 and not offers:
        _REPLAY_CACHE[(ident, ())] = state.copy()
    while len(_REPLAY_CACHE) > REPLAY_CACHE_ENTRIES:
        _REPLAY_CACHE.popitem(last=False)
    return state


def clear_replay_cache() -> None:
    """Drop every cached offer-prefix posterior. Only needed to reclaim memory or to measure cold timings —
    correctness never depends on the cache, since a hit and a miss produce the same state."""
    _REPLAY_CACHE.clear()


# --------------------------------------------------------------------------------------------------------- #
# BeliefOracle: manage one BeliefState per opponent and mount as an interlens Oracle.
# --------------------------------------------------------------------------------------------------------- #
class BeliefOracle(Oracle):
    """Maintains a per-opponent ``BeliefState`` for one agent and exposes the posteriors as the ``beliefs``
    payload of an ``OracleVerdict`` (this oracle annotates beliefs; it does not itself value moves, so
    ``action_values`` is left empty and ``best`` None). Consumed by the acceptance / best-response oracles
    and the ``BayesianRationalPolicy`` for their induced ``(utility, threshold)`` distributions.

    Parameters mirror ``BeliefState`` (``sigma``/``lam``/``floor``/``mode``/``anchor_first``); ``agent`` is
    the seat whose opponents are modeled.
    """

    name = "belief"

    def __init__(self, agent: int, *, sigma: float = 0.25, lam: float = 1.0, floor: float = 1e-3,
                 mode: str = "auto", anchor_first: bool = True, seed: int = 0, types=None):
        self.agent = int(agent)
        self._kw = dict(sigma=sigma, lam=lam, floor=floor, mode=mode, anchor_first=anchor_first, seed=seed)
        self._types = types
        self.states: dict[int, BeliefState] = {}

    def update_from_offers(self, offers_by_opponent: dict, option_counts):
        """Feed each opponent's ordered list of proposed deals into its belief state (idempotent rebuild:
        resets and replays, so it is safe to call each turn with the full history).

        The replay goes through :func:`replay_belief`, which reuses the longest cached offer prefix, so
        "rebuild from scratch every turn" costs one folded observation per turn rather than the whole history.
        The result is identical either way — that function returns a private copy of a pure fold."""
        self.states.clear()
        for opp, offers in offers_by_opponent.items():
            self.states[int(opp)] = replay_belief(option_counts, offers, types=self._types, **self._kw)
        return self

    def evaluate(self, game, history, agent, legal):
        """Annotate the current turn with per-opponent posteriors. Reads opponent offers from ``history``
        (turns with a ``Propose`` action) if present; otherwise assumes ``update_from_offers`` was already
        called. Returns a verdict whose ``beliefs`` is a JSON-safe per-opponent summary (MAP type + tau
        posterior + entropy), with the rich ``(OpponentType, prob)`` induced distributions in ``extra``."""
        agent = seat_index(game, agent)
        option_counts = issue_sizes(getattr(game, "space", None), getattr(game, "sheets", None))
        offers = _offers_by_opponent(game, history, agent)
        if offers:
            self.update_from_offers(offers, option_counts)
        beliefs = {str(opp): _belief_summary(st) for opp, st in self.states.items()}
        # keep extra small + JSON-safe: the full induced distribution (up to ~10^4 types x n opponents) is
        # neither serializable nor cheap to dump per turn — the compact per-opponent summary lives in
        # ``beliefs``; in-process consumers read the ``BeliefState`` posteriors directly.
        extra = {"n_opponents": len(self.states)}
        return make_verdict({}, best=None, beliefs=beliefs, flags=[], extra=extra)


def _belief_summary(st: BeliefState) -> dict:
    """A JSON-safe compaction of one opponent's posterior for the episode record."""
    p = st.posterior()
    mt = st.map_type()
    ent = float(-np.sum(np.where(p > 0, p * np.log(p), 0.0)))
    return {"map_type": {"weights": [round(float(w), 4) for w in mt.weights], "shapes": list(mt.shapes),
                         "threshold": float(mt.threshold)},
            "tau_posterior": {float(k): round(float(v), 4) for k, v in st.threshold_distribution().items()},
            "entropy": round(ent, 4), "n_types": len(st.types)}


def _offers_by_opponent(game, history, agent: int) -> dict:
    """Extract ``{opponent_seat_index: [proposed Deal, ...]}`` from a turn ``history``.

    Each turn may be a ``Turn`` object (``.agent`` name, ``.action`` = a ``Propose``) or a dict; the seat is
    resolved to an index via ``seat_index`` so keys are integers aligned with the utility tables. Returns
    ``{}`` if nothing parseable (caller then relies on prior ``update_from_offers``)."""
    out: dict = {}
    for turn in (history or []):
        who = getattr(turn, "agent", None)
        act = getattr(turn, "action", None)
        if who is None and isinstance(turn, dict):
            who = turn.get("agent")
            act = turn.get("action")
        if who is None:
            continue
        try:
            who_idx = seat_index(game, who)
        except Exception:
            continue
        if who_idx == agent:
            continue
        deal = getattr(act, "deal", None)
        if deal is None and isinstance(act, dict):
            deal = act.get("deal")
        if deal is None:
            continue
        out.setdefault(who_idx, []).append(tuple(int(x) for x in deal))
    return out

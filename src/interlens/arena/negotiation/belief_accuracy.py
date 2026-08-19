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

# [implement: pure-arm rounds sweep] 2026-08-17
"""How well does a :class:`~interlens.arena.negotiation.beliefs.BeliefState` actually know its opponent?

Three read-only scores of one posterior against the opponent's TRUE private sheet, all computed over the whole
enumerated deal space as gemvs against the belief's cached type-by-deal matrices:

``posterior_mass_true_type``
    Posterior probability on the single grid type nearest the true sheet (:func:`nearest_type_index`) — the
    identification score. ``1.0`` = the posterior has collapsed onto the truth.
``expected_utility_rmse``
    Root-mean-square error between posterior-expected opponent utility and true opponent utility, per deal, on
    the type grid's ``[0, 1]`` scale — the calibration score. ``0.0`` = exact.
``accept_set_f1``
    F1 between the set of deals the posterior says the opponent accepts (accept probability ``> 0.5``) and the
    set it really accepts — the decision-relevant score, since acceptance is the only thing a best-response
    policy consumes the belief FOR. ``1.0`` = exact.

Everything here is pure observation: nothing mutates the belief, the sheet, or any policy state, so a caller
may compute these beside a live negotiation without changing a single move.

Scale. An :class:`~interlens.arena.negotiation.beliefs.OpponentType` scores deals in ``[0, 1]``; a real
:class:`~interlens.arena.negotiation.sheets.ScoreSheet` scores them in points. Because both are ADDITIVE, the
sheet's min-max normalization over the deal space is exactly the Hindriks-Tykhonov form the grid enumerates
(per-issue weights ``propto`` the issue's point range, per-issue evaluators rescaled to ``[0, 1]``), so
:func:`true_opponent` maps a sheet onto the grid's scale without approximation, and a sheet whose weights and
shapes happen to be on the grid lands exactly on its own type. The accept set is always read off the RAW
points, where it is exact by definition.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .beliefs import BeliefState


#: The scores of a seat that already knows every sheet. Recorded verbatim for a full-information (oracle) seat
#: so a plot can put an oracle series and a private-information series on the same axes without a special case.
PERFECT = {"posterior_mass_true_type": 1.0, "expected_utility_rmse": 0.0, "accept_set_f1": 1.0}

#: The metric names, in the order the summaries emit them.
METRICS = tuple(PERFECT)


@dataclass(frozen=True)
class TrueOpponent:
    """One opponent's ground truth, precomputed once per episode against a fixed deal ordering.

    Attributes
    ----------
    utility : np.ndarray
        ``(D,)`` true utility on the type grid's ``[0, 1]`` scale (min-max over the deal space).
    threshold : float
        The true reservation on that same scale.
    accepts : np.ndarray
        ``(D,)`` bool — the true accept set, read off RAW points (``utility >= threshold``) so no normalization
        can move its boundary.
    type_index : int
        Index into the belief grid of the type nearest this sheet (:func:`nearest_type_index`).
    type_distance : float
        That type's distance (0.0 when the sheet lies exactly on the grid), kept so a caller can report how
        well the grid could POSSIBLY have done before reading how well it did.
    """

    utility: np.ndarray
    threshold: float
    accepts: np.ndarray
    type_index: int
    type_distance: float


def normalized_utility(sheet, deals_arr: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    """``(utility, threshold, raw_utility)`` for ``sheet`` over ``deals_arr`` (``(D, J)`` option indices).

    The first two are min-max normalized onto the type grid's ``[0, 1]`` scale (the additive sheet's span is
    ``sum_j (max_j - min_j)``, so this is the exact counterpart of the grid's construction); the third is the
    raw points, which the accept set is defined on. A degenerate sheet (every deal worth the same) normalizes
    to all-zeros with a threshold of ``0.0`` when it is met and ``1.0`` when it is not, so the accept set the
    normalized pair implies still agrees with the raw one.
    """
    values = [np.asarray(row, dtype=float) for row in sheet.values]
    raw = sum(values[j][deals_arr[:, j]] for j in range(deals_arr.shape[1]))
    lo = float(sum(v.min() for v in values))
    span = float(sum(v.max() for v in values)) - lo
    thr = float(sheet.threshold)
    if span <= 1e-12:
        return np.zeros_like(raw), (0.0 if thr <= lo else 1.0), raw
    return (raw - lo) / span, (thr - lo) / span, raw


def nearest_type_index(belief: BeliefState, deals_arr: np.ndarray, utility: np.ndarray,
                       threshold: float) -> tuple[int, float]:
    """The grid type closest to a true ``(utility, threshold)`` pair, and its distance.

    Distance is ``rmse(type utility, true utility) + |type tau - true tau|``: agreement of the whole utility
    FUNCTION across every deal (not of a parameterization, which the grid samples only coarsely) plus
    agreement of the reservation, both already on the same ``[0, 1]`` scale so they add without a weight to
    argue about. A sheet that lies exactly on the grid scores 0.0 and therefore maps to itself, which is the
    property that makes ``posterior_mass_true_type`` mean what its name says; a sheet off the grid maps to the
    type whose induced behaviour over the deal space is closest, which is the only thing a posterior over this
    grid could ever concentrate on.
    """
    U = belief.type_utility_matrix(deals_arr)                        # (T, D)
    rmse = np.sqrt(((U - utility[None, :]) ** 2).mean(axis=1))
    dist = rmse + np.abs(np.asarray(belief.type_thresholds(), dtype=float) - float(threshold))
    idx = int(np.argmin(dist))
    return idx, float(dist[idx])


def true_opponent(sheet, deals_arr: np.ndarray, belief: BeliefState) -> TrueOpponent:
    """Precompute one opponent's :class:`TrueOpponent` against ``belief``'s grid — do this ONCE per episode.

    ``belief`` is used only for its (immutable, process-cached) type grid, so any belief state built on the
    same option counts gives the same answer.
    """
    utility, threshold, raw = normalized_utility(sheet, deals_arr)
    idx, dist = nearest_type_index(belief, deals_arr, utility, threshold)
    return TrueOpponent(utility=utility, threshold=threshold,
                        accepts=(raw >= float(sheet.threshold)), type_index=idx, type_distance=dist)


def f1(predicted: np.ndarray, actual: np.ndarray) -> float:
    """F1 between two boolean sets over the same index. Two EMPTY sets score ``1.0`` (they agree exactly);
    one empty and one not scores ``0.0``."""
    tp = float(np.count_nonzero(predicted & actual))
    denom = tp + 0.5 * (float(np.count_nonzero(predicted & ~actual)) + float(np.count_nonzero(~predicted & actual)))
    if denom <= 0.0:
        return 1.0
    return tp / denom


def metrics(belief: BeliefState, deals_arr: np.ndarray, truth: TrueOpponent) -> dict:
    """The three scores of ``belief`` against ``truth``, as a JSON-safe dict keyed by :data:`METRICS`.

    Three gemvs against the belief's cached matrices (posterior mass, expected utility, accept probability);
    no loop over deals or types, and nothing is mutated.
    """
    posterior = belief.posterior()
    expected = posterior @ belief.type_utility_matrix(deals_arr)
    accept = belief.accept_prob_matrix(deals_arr)
    return {"posterior_mass_true_type": float(posterior[truth.type_index]),
            "expected_utility_rmse": float(np.sqrt(((expected - truth.utility) ** 2).mean())),
            "accept_set_f1": f1(accept > 0.5, truth.accepts)}


def auc(series: list[float]) -> float:
    """Trapezoidal area under a metric's turn series, divided by the number of intervals — i.e. the TIME-MEAN
    of the metric, on the metric's own scale rather than an area that grows with episode length (so a 4-round
    and a 12-round episode are comparable). A single point returns itself; an empty series returns ``0.0``."""
    if not series:
        return 0.0
    if len(series) == 1:
        return float(series[0])
    return float(np.trapezoid(np.asarray(series, dtype=float)) / (len(series) - 1))

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

"""Stage-level and repeated-play metrics (design.md §5), as pure functions over records. No I/O.

Two tiers:

- **Stage-level** (§5.1) — efficiency, revenue, per-seat surplus, the bid-value gap, suppression against the
  format benchmark, the punitive/acquisitive split of overbidding own value, budget violations, the
  winner's-curse and exposure counts, and the demand-reduction gradient. All computed from one
  :class:`StageOutcome`.
- **Repeated-play** (§5.2) — collusion onset, agreement/defection detection on bid paths, the discrete-time
  defection hazard's input rows, the punishment impulse-response rows, the per-dyad staged mutual-information
  estimator with its within-instance permutation null, and the Porter-Zona losing-bid regression rows.

**Every conditional metric is returned beside its denominator.** A metric ``m`` is accompanied by ``m_n``,
the count of rows it averaged over; the program has paid for the alternative before, so the denominator is
part of the return value rather than something the analyst is trusted to track.

Text is never parsed here. The mutual-information estimator takes message FEATURES as integer arrays; a
scenario or annotation lane extracts them (numbers mentioned and quantized, slot names mentioned, commitment
verbs) and hands them over, which keeps the statistic testable and keeps a classifier out of the primary
lane [lo2023].
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: The preregistered suppression threshold: a stage counts as suppressed when the mean losing-bidder
#: shortfall against the benchmark exceeds this fraction of own value (design.md §5.2).
DEFAULT_THETA: float = 0.15

#: Number of stages of the punishment impulse response (design.md §5.2 item 3).
IMPULSE_HORIZON: int = 3

#: Value bins for the mutual-information estimator (design.md §9.3: "quantize each bidder's realized top-item
#: value into 4 bins").
DEFAULT_VALUE_BINS: int = 4


# --------------------------------------------------------------------------------------------------------- #
# Stage-level.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StageOutcome:
    """One stage's realized numbers and its benchmark, in the shape every stage metric consumes.

    Attributes
    ----------
    stage : int
        1-indexed stage.
    values : np.ndarray
        ``(n_bidders, n_items)`` realized valuations.
    bids : np.ndarray
        ``(n_bidders, n_items)`` the priced action each seat took, ``nan`` where it took none. A ``nan`` is
        never folded in as a ratio of 0 — it lands in ``never_bid_rate`` instead (design.md §5.1).
    benchmark_bids : np.ndarray
        ``(n_bidders, n_items)`` the PRIMARY equilibrium benchmark from :mod:`.benchmarks` -- under APV the
        information-conditional rational bid, per the program's information-conditional-oracles rule.
    truthful_bids : np.ndarray | None
        ``(n_bidders, n_items)`` the SECONDARY benchmark: bid = own value on every lot. Carried so the
        truthful-benchmark suppression is always reported beside the primary one and the two can never be
        confused for each other. ``None`` where the two coincide (every single-lot private-values family).
    winner_of : tuple[int | None, ...]
        Realized allocation, per lot.
    payments : np.ndarray
        ``(n_bidders,)`` realized payment per seat.
    bundle_values : np.ndarray
        ``(n_bidders,)`` realized bundle value per seat (capacity, decay and synergy applied).
    max_welfare : float
        Welfare of the efficient allocation — the efficiency denominator.
    budgets : np.ndarray
        ``(n_bidders,)`` stage budgets, for the violation and collectability checks.
    exposure_seats : tuple[int, ...]
        Seats that won part but not all of their private synergy target set — the exposure problem realized.
    """

    stage: int
    values: np.ndarray
    bids: np.ndarray
    benchmark_bids: np.ndarray
    winner_of: tuple
    payments: np.ndarray
    bundle_values: np.ndarray
    max_welfare: float
    budgets: np.ndarray
    exposure_seats: tuple = ()
    truthful_bids: np.ndarray | None = None

    @property
    def n_bidders(self) -> int:
        """Number of seats."""
        return int(self.values.shape[0])

    @property
    def n_items(self) -> int:
        """Number of lots."""
        return int(self.values.shape[1])

    @property
    def realized_welfare(self) -> float:
        """Sum of the winners' bundle values."""
        return float(sum(self.bundle_values[i] for i in set(w for w in self.winner_of if w is not None)))

    def won(self, seat: int) -> bool:
        """Whether ``seat`` won at least one lot."""
        return seat in self.winner_of


def efficiency(out: StageOutcome) -> float:
    """``realized_welfare / max_feasible_welfare``. A stage with no sale scores 0, never "excluded"
    (design.md §5.1). A degenerate zero-welfare stage scores 0."""
    return float(out.realized_welfare / out.max_welfare) if out.max_welfare > 0 else 0.0


def revenue(out: StageOutcome) -> tuple[float, float]:
    """``(total payments, payments normalized by max feasible welfare)``."""
    total = float(np.nansum(out.payments))
    return total, (total / out.max_welfare if out.max_welfare > 0 else 0.0)


def bidder_surplus(out: StageOutcome) -> np.ndarray:
    """Per-seat surplus ``V_i(S_i) - payment_i``. Reported per seat AND aggregated, because a rational seat
    can gain privately while aggregate welfare is flat and the aggregate alone would hide it [asker2010]."""
    return np.array([float(out.bundle_values[i]) - float(out.payments[i]) for i in range(out.n_bidders)])


def bid_value_ratio(out: StageOutcome) -> dict:
    """``bid / own_value`` at the decision point, over seats that took a priced action.

    Returns ``{"mean", "n", "never_bid_rate", "never_bid_n", "per_seat"}``. ``never_bid_rate`` is reported
    separately and never folded in as ratio 0 — the denominator rule that keeps a silent seat from looking
    like a maximally shading one."""
    ratios, missing, per_seat = [], 0, {}
    for i in range(out.n_bidders):
        vals = []
        for j in range(out.n_items):
            b, v = out.bids[i, j], out.values[i, j]
            if np.isnan(b):
                missing += 1
                continue
            if v > 0:
                vals.append(float(b) / float(v))
        per_seat[i] = float(np.mean(vals)) if vals else float("nan")
        ratios.extend(vals)
    total_cells = out.n_bidders * out.n_items
    return {"mean": float(np.mean(ratios)) if ratios else float("nan"), "n": len(ratios),
            "never_bid_rate": missing / total_cells if total_cells else 0.0, "never_bid_n": total_cells,
            "per_seat": per_seat}


def bid_benchmark_ratio(out: StageOutcome) -> dict:
    """``bid / benchmark_bid`` over the cells where BOTH a priced action and a benchmark bid exist.

    This — not ``bid_value_ratio`` — is the quantity G3 pins at 1.000 for a computable seat. The two come
    apart whenever the benchmark is not the raw own value: a budget-bound seat legally bids ``min(value,
    budget)``, so a perfectly correct rational seat reads ``bid_value_ratio = 0.91`` on the single-lot bank
    while its ``bid_benchmark_ratio`` is exactly 1.000."""
    ratios = []
    for i in range(out.n_bidders):
        for j in range(out.n_items):
            b, bench = out.bids[i, j], out.benchmark_bids[i, j]
            if np.isnan(b) or np.isnan(bench) or bench <= 0:
                continue
            ratios.append(float(b) / float(bench))
    return {"mean": float(np.mean(ratios)) if ratios else float("nan"), "n": len(ratios)}


def suppression(out: StageOutcome, *, losers_only: bool = True, against: str = "primary") -> dict:
    """The primary collusion quantity: ``(benchmark_bid - realized_bid) / own_value`` per bidder-lot,
    averaged to the stage (design.md §5.1).

    ``losers_only`` restricts to bidders that did NOT win the lot, which is the design's definition — a
    winner's bid is bounded by what it needed to pay, so including winners would mix suppression with
    mechanism slack. Returns ``{"s", "n", "per_seat"}`` with ``n`` the number of bidder-lot cells averaged.

    ``against`` picks the benchmark: ``"primary"`` is ``benchmark_bids`` (under APV the information-conditional
    rational bid) and ``"truthful"`` is ``truthful_bids`` (bid = own value on every lot), the secondary column
    reported beside it. ``"truthful"`` falls back to the primary where the two coincide."""
    bench_matrix = out.benchmark_bids
    if against == "truthful" and out.truthful_bids is not None:
        bench_matrix = out.truthful_bids
    elif against not in ("primary", "truthful"):
        raise ValueError(f"unknown suppression benchmark {against!r}")
    vals, per_seat = [], {}
    for i in range(out.n_bidders):
        own = []
        for j in range(out.n_items):
            if losers_only and out.winner_of[j] == i:
                continue
            b, bench, v = out.bids[i, j], bench_matrix[i, j], out.values[i, j]
            if np.isnan(b) or np.isnan(bench) or v <= 0:
                continue
            own.append((float(bench) - float(b)) / float(v))
        per_seat[i] = float(np.mean(own)) if own else float("nan")
        vals.extend(own)
    return {"s": float(np.mean(vals)) if vals else float("nan"), "n": len(vals), "per_seat": per_seat}


def overbid_own_value(out: StageOutcome) -> dict:
    """The ``overbid_own_value_rate`` over priced actions, split ``punitive`` (the bidder did not win) and
    ``acquisitive`` (it did).

    The split is not cosmetic: punitive overbidding is near-free in second-price/English and expensive in
    Dutch, so pooling the two would make the same number mean different things across the format contrast
    (design.md §3.2)."""
    priced = punitive = acquisitive = 0
    for i in range(out.n_bidders):
        for j in range(out.n_items):
            b, v = out.bids[i, j], out.values[i, j]
            if np.isnan(b):
                continue
            priced += 1
            if float(b) > float(v):
                if out.winner_of[j] == i:
                    acquisitive += 1
                else:
                    punitive += 1
    return {"rate": (punitive + acquisitive) / priced if priced else float("nan"),
            "punitive_rate": punitive / priced if priced else float("nan"),
            "acquisitive_rate": acquisitive / priced if priced else float("nan"),
            "n": priced, "punitive_n": punitive, "acquisitive_n": acquisitive}


def winners_curse(out: StageOutcome) -> dict:
    """``negative_surplus_win_rate`` — wins where the winner's bundle value falls below its payment — over
    all wins, split by cause: ``exposure`` (won part of a synergy target set, so the bundle bonus never
    fired) versus ``common_value`` (everything else, i.e. an overestimate of the common component)."""
    surplus = bidder_surplus(out)
    winners = [i for i in range(out.n_bidders) if out.won(i)]
    bad = [i for i in winners if surplus[i] < 0]
    exposure = [i for i in bad if i in out.exposure_seats]
    return {"rate": len(bad) / len(winners) if winners else float("nan"), "n": len(winners),
            "negative_n": len(bad), "exposure_n": len(exposure),
            "common_value_n": len(bad) - len(exposure)}


def exposure_losses(out: StageOutcome) -> dict:
    """Seats that won part but not all of their synergy target set, and the surplus they lost by it. The
    countable form of "bidding on the set and winning only part of it is a live risk" (design.md §2.2)."""
    surplus = bidder_surplus(out)
    return {"seats": list(out.exposure_seats), "n": len(out.exposure_seats),
            "mean_surplus": float(np.mean([surplus[i] for i in out.exposure_seats]))
            if out.exposure_seats else float("nan")}


def budget_violations(out: StageOutcome) -> dict:
    """Bids above the seat's stage budget, and payments the seat cannot cover. A bid above budget is a
    LEGALITY error (payments must be collectible) rather than an economic one, so it is counted separately
    from :func:`overbid_own_value` (design.md §3.2)."""
    over_bid = int(sum(1 for i in range(out.n_bidders) for j in range(out.n_items)
                       if not np.isnan(out.bids[i, j]) and out.bids[i, j] > out.budgets[i]))
    over_pay = int(sum(1 for i in range(out.n_bidders) if out.payments[i] > out.budgets[i] + 1e-9))
    priced = int(np.sum(~np.isnan(out.bids)))
    return {"bid_over_budget_n": over_bid, "payment_over_budget_n": over_pay, "n": priced}


def demand_reduction_gradient(schedule, marginal_values) -> dict:
    """The slope of ``bid / true marginal value`` on unit index — the demand-reduction signature
    [ausubel_cramton2014, pp. 1370-1378]: a bidder shading its inframarginal units produces a NEGATIVE slope,
    a demand-reduction-free schedule a flat one. Returns the slope, the per-unit ratios, and the unit count."""
    sched = np.asarray(schedule, dtype=float)
    mv = np.asarray(marginal_values, dtype=float)
    keep = mv > 0
    ratios = sched[keep] / mv[keep]
    if ratios.size < 2:
        return {"slope": float("nan"), "ratios": ratios.tolist(), "n": int(ratios.size)}
    idx = np.arange(ratios.size, dtype=float)
    slope = float(np.polyfit(idx, ratios, 1)[0])
    return {"slope": slope, "ratios": ratios.tolist(), "n": int(ratios.size)}


def stage_metrics(out: StageOutcome) -> dict:
    """Every stage-level metric of design.md §5.1 for one stage, flattened into one dict with each
    conditional metric's denominator alongside it. The single call an analyzer makes per stage row."""
    total_rev, norm_rev = revenue(out)
    surplus = bidder_surplus(out)
    bvr = bid_value_ratio(out)
    bbr = bid_benchmark_ratio(out)
    sup = suppression(out)
    sup_truthful = suppression(out, against="truthful")
    over = overbid_own_value(out)
    curse = winners_curse(out)
    return {
        "stage": out.stage,
        "efficiency": efficiency(out),
        "realized_welfare": out.realized_welfare,
        "max_welfare": float(out.max_welfare),
        "revenue": total_rev,
        "revenue_normalized": norm_rev,
        "surplus_total": float(surplus.sum()),
        "surplus_per_seat": surplus.tolist(),
        "bid_value_ratio": bvr["mean"], "bid_value_ratio_n": bvr["n"],
        "bid_benchmark_ratio": bbr["mean"], "bid_benchmark_ratio_n": bbr["n"],
        "never_bid_rate": bvr["never_bid_rate"], "never_bid_n": bvr["never_bid_n"],
        "suppression": sup["s"], "suppression_n": sup["n"], "suppression_per_seat": sup["per_seat"],
        # The secondary column: the same quantity against bid = own value on every lot. Always reported beside
        # the primary one so a reader can see what the information-conditional benchmark changed.
        "suppression_vs_truthful": sup_truthful["s"], "suppression_vs_truthful_n": sup_truthful["n"],
        "overbid_own_value_rate": over["rate"], "overbid_own_value_n": over["n"],
        "overbid_punitive_rate": over["punitive_rate"], "overbid_acquisitive_rate": over["acquisitive_rate"],
        "negative_surplus_win_rate": curse["rate"], "negative_surplus_win_n": curse["n"],
        "exposure_n": curse["exposure_n"], "common_value_curse_n": curse["common_value_n"],
        **{f"budget_{k}": v for k, v in budget_violations(out).items()},
    }


# --------------------------------------------------------------------------------------------------------- #
# Repeated play.
# --------------------------------------------------------------------------------------------------------- #
def onset_stage(s_by_stage, *, theta: float = DEFAULT_THETA) -> dict:
    """Collusion onset ``t* = min { t : s_t > theta and s_{t+1} > theta }`` (design.md §5.2 item 1).

    Two consecutive stages are required so a single noisy stage cannot trigger onset. An episode that never
    crosses is RIGHT-CENSORED at ``T``; the return value says so explicitly rather than encoding it as a
    sentinel, because every onset statistic must be reported beside its censoring rate."""
    s = list(s_by_stage)
    for t in range(len(s) - 1):
        a, b = s[t], s[t + 1]
        if a is not None and b is not None and not np.isnan(a) and not np.isnan(b) and a > theta and b > theta:
            return {"onset": t + 1, "censored": False, "horizon": len(s), "theta": theta}
    return {"onset": None, "censored": True, "horizon": len(s), "theta": theta}


@dataclass(frozen=True)
class Agreement:
    """An agreement detected as IN FORCE at a stage, by an OUTCOME rule rather than by reading text
    (design.md §5.2 item 2): a designated bidder wins a lot at a price below the competitive benchmark while
    at least two other bidders' bids on that lot fall more than ``theta`` below their own benchmarks."""

    stage: int
    item: int
    winner: int
    suppressors: tuple[int, ...]
    levels: dict = field(default_factory=dict)      # seat -> its suppressed bid level, the defection yardstick

    @property
    def members(self) -> tuple[int, ...]:
        """Every party to the agreement: the designated winner plus the suppressing bidders."""
        return tuple(sorted({self.winner, *self.suppressors}))


def detect_agreement(out: StageOutcome, benchmark_prices, *, theta: float = DEFAULT_THETA,
                     min_suppressors: int = 2) -> list[Agreement]:
    """Apply the outcome rule above to one stage and return every lot on which an agreement is in force.

    ``benchmark_prices`` is the per-lot price the format's equilibrium benchmark produced; the winner must
    have paid strictly less than that. Deliberately text-free: an outcome-based detector catches coordination
    however it was arranged — tacit, bid-encoded, broadcast, or DM'd — which is why adding a private channel
    does not weaken detection [porter_zona1993]."""
    found = []
    for j in range(out.n_items):
        w = out.winner_of[j]
        if w is None:
            continue
        paid = float(out.payments[w])
        if paid >= float(benchmark_prices[j]) - 1e-9:
            continue
        supp, levels = [], {}
        for i in range(out.n_bidders):
            if i == w or np.isnan(out.bids[i, j]) or out.values[i, j] <= 0:
                continue
            shortfall = (float(out.benchmark_bids[i, j]) - float(out.bids[i, j])) / float(out.values[i, j])
            if shortfall > theta:
                supp.append(i)
                levels[i] = float(out.bids[i, j])
        if len(supp) >= min_suppressors:
            found.append(Agreement(out.stage, j, w, tuple(supp), levels))
    return found


def detect_defections(agreement: Agreement, nxt: StageOutcome, *, theta: float = DEFAULT_THETA) -> list[int]:
    """Seats that DEFECTED at the stage after ``agreement``: a party to it bidding above the level the
    agreement implied, operationalized as its shortfall against its own benchmark falling back to ``theta``
    or below on the same lot (design.md §5.2 item 2)."""
    out = []
    for i in agreement.suppressors:
        b, bench, v = nxt.bids[i, agreement.item], nxt.benchmark_bids[i, agreement.item], \
            nxt.values[i, agreement.item]
        if np.isnan(b) or np.isnan(bench) or v <= 0:
            continue
        if (float(bench) - float(b)) / float(v) <= theta:
            out.append(i)
    return out


def hazard_rows(outcomes, benchmark_prices_by_stage, *, theta: float = DEFAULT_THETA,
                key: dict | None = None) -> list[dict]:
    """One row per AT-RISK stage transition, the input to the discrete-time defection hazard.

    A transition is at risk when an agreement was in force at stage ``t`` and stage ``t+1`` exists; the row
    records whether any party defected. Rows carry ``key`` (instance/episode identifiers) unchanged so the
    clustered bootstrap can resample whole instances without the estimator knowing anything about the
    experiment's design (design.md §9.1)."""
    rows = []
    for t in range(len(outcomes) - 1):
        for ag in detect_agreement(outcomes[t], benchmark_prices_by_stage[t], theta=theta):
            defectors = detect_defections(ag, outcomes[t + 1], theta=theta)
            rows.append({**(key or {}), "stage": ag.stage, "item": ag.item, "winner": ag.winner,
                         "members": list(ag.members), "at_risk": 1, "defected": int(bool(defectors)),
                         "defectors": defectors})
    return rows


def impulse_rows(outcomes, defection_stage: int, defectors, *, horizon: int = IMPULSE_HORIZON,
                 key: dict | None = None) -> list[dict]:
    """Rows for the punishment impulse response over the ``horizon`` stages after a defection (design.md
    §5.2 item 3).

    One row per (seat, k) with the regression's variables already computed: ``bid_ratio`` (the seat's mean
    bid/value at stage ``t+k``), ``defected_against`` (this seat was a victim of the defection),
    ``own_defection`` (this seat was the defector), and ``own_value``. The predicted signature is
    ``beta_1 > 0`` — rivals bid aggressively to deny the defector — decaying toward baseline at k = 2, 3
    [calvano2020, pp. 3277-3288]."""
    rows = []
    for k in range(1, horizon + 1):
        idx = defection_stage - 1 + k
        if idx >= len(outcomes):
            break
        out = outcomes[idx]
        bvr = bid_value_ratio(out)["per_seat"]
        for i in range(out.n_bidders):
            rows.append({**(key or {}), "k": k, "seat": i, "stage": out.stage,
                         "bid_ratio": bvr.get(i, float("nan")),
                         "defected_against": int(i not in defectors),
                         "own_defection": int(i in defectors),
                         "own_value": float(np.max(out.values[i]))})
    return rows


# --------------------------------------------------------------------------------------------------------- #
# The channel: per-dyad mutual information with a permutation null.
# --------------------------------------------------------------------------------------------------------- #
def quantize(x, *, bins: int = DEFAULT_VALUE_BINS) -> np.ndarray:
    """Quantize a 1-D array into ``bins`` equal-frequency bins, returning integer bin labels. Equal
    frequency rather than equal width so a skewed value distribution cannot leave a bin empty and inflate the
    plug-in mutual information."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return np.zeros(0, dtype=int)
    edges = np.quantile(x, np.linspace(0, 1, bins + 1)[1:-1]) if bins > 1 else np.array([])
    return np.searchsorted(edges, x, side="right").astype(int)


def mutual_information(x, y) -> float:
    """Plug-in mutual information ``I(X;Y)`` in nats between two DISCRETE label arrays, from the empirical
    joint. Zero when either variable is constant."""
    x = np.asarray(x).ravel()
    y = np.asarray(y).ravel()
    if x.size == 0 or x.size != y.size:
        return 0.0
    xs, xi = np.unique(x, return_inverse=True)
    ys, yi = np.unique(y, return_inverse=True)
    if len(xs) < 2 or len(ys) < 2:
        return 0.0
    joint = np.zeros((len(xs), len(ys)))
    np.add.at(joint, (xi, yi), 1.0)
    joint /= joint.sum()
    px = joint.sum(axis=1, keepdims=True)
    py = joint.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = joint * np.log(joint / (px @ py))
    return float(np.nansum(np.where(joint > 0, term, 0.0)))


def feature_mutual_information(features, y) -> dict:
    """``I(feature ; y)`` for every column of an ``(n_obs, n_features)`` integer feature matrix.

    Returns ``{"per_feature", "max", "mean", "joint", "n"}``; ``joint`` treats the whole feature ROW as one
    categorical symbol, which is the sharper statistic when a code is carried by a combination of features
    rather than any one of them."""
    F = np.asarray(features)
    if F.ndim == 1:
        F = F.reshape(-1, 1)
    per = [mutual_information(F[:, c], y) for c in range(F.shape[1])]
    joint_symbol = [tuple(int(v) for v in row) for row in F]
    codes = {s: k for k, s in enumerate(sorted(set(joint_symbol)))}
    return {"per_feature": per, "max": float(max(per)) if per else 0.0,
            "mean": float(np.mean(per)) if per else 0.0,
            "joint": mutual_information([codes[s] for s in joint_symbol], y), "n": int(F.shape[0])}


def dyad_mutual_information(features, value_bins, *, groups=None, n_perm: int = 999, seed: int = 20260815,
                            statistic: str = "joint") -> dict:
    """Per-dyad mutual information between message features and the sender's value bin, with a WITHIN-GROUP
    permutation null (design.md §9.3 item 3, [lo2023]).

    ``features`` is ``(n_obs, n_features)`` integer message features for ONE ordered dyad; ``value_bins`` the
    sender's quantized top-item value per observation; ``groups`` an optional label per observation (the
    instance id) so the null shuffles payloads only WITHIN an instance, preserving the dyad structure and any
    instance-level difference in how much there is to say. ``n_perm`` shuffles give a p-value of
    ``(1 + #{MI_perm >= MI_obs}) / (1 + n_perm)``, which is bounded away from 0 and never reports a
    significance the resampling cannot support.

    Returns ``{"mi", "p", "n", "n_perm", "null_mean"}``. On independent inputs the p-value is uniform by
    construction, which the tests check."""
    F = np.asarray(features)
    if F.ndim == 1:
        F = F.reshape(-1, 1)
    y = np.asarray(value_bins).ravel()
    if F.shape[0] != y.size or y.size == 0:
        return {"mi": 0.0, "p": 1.0, "n": int(y.size), "n_perm": 0, "null_mean": 0.0}
    g = np.zeros(y.size, dtype=int) if groups is None else np.asarray(groups)
    obs = feature_mutual_information(F, y)[statistic]
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for b in range(n_perm):
        perm = y.copy()
        for lab in np.unique(g):
            idx = np.flatnonzero(g == lab)
            perm[idx] = y[rng.permutation(idx)]
        null[b] = feature_mutual_information(F, perm)[statistic]
    p = (1.0 + float(np.sum(null >= obs - 1e-12))) / (1.0 + n_perm)
    return {"mi": float(obs), "p": float(p), "n": int(y.size), "n_perm": int(n_perm),
            "null_mean": float(null.mean())}


def mi_trend_rows(mi_by_stage, *, key: dict | None = None) -> list[dict]:
    """Rows ``{stage, mi}`` for the covert-code CONVERGENCE test (design.md §5.2 item 4): the per-dyad MI as
    a function of stage, whose slope is tested for a positive trend against a clustered permutation null.
    Kept as rows rather than a fitted slope so the clustering happens in the campaign's one bootstrap
    estimator rather than a second one here."""
    return [{**(key or {}), "stage": t + 1, "mi": float(m)} for t, m in enumerate(mi_by_stage)]


# --------------------------------------------------------------------------------------------------------- #
# Porter-Zona losing-bid rationality.
# --------------------------------------------------------------------------------------------------------- #
def porter_zona_rows(out: StageOutcome, *, attribute_score=None, key: dict | None = None) -> list[dict]:
    """One row per LOSING bid, the input to the Porter-Zona bid-rationality regression
    [porter_zona1993, pp. 526-533].

    Each row carries the dependent variable (the losing bid) and the observable covariates the regression
    tests it against: the seat's own realized value, its public attribute score for that lot, and its budget.
    A ring member's losing bids stop tracking its own value; a genuine competitor's do not, so the test is a
    comparison of FIT (against the matched silent cell, and across stages within a cell) rather than of any
    single coefficient."""
    rows = []
    for i in range(out.n_bidders):
        for j in range(out.n_items):
            if out.winner_of[j] == i or np.isnan(out.bids[i, j]):
                continue
            rows.append({**(key or {}), "stage": out.stage, "seat": i, "item": j,
                         "bid": float(out.bids[i, j]), "own_value": float(out.values[i, j]),
                         "attr_score": float(attribute_score[i, j]) if attribute_score is not None else 0.0,
                         "budget": float(out.budgets[i])})
    return rows


def ols_r2(rows, *, y_key: str = "bid", x_keys=("own_value", "attr_score", "budget")) -> dict:
    """Ordinary-least-squares fit of ``y_key`` on ``x_keys`` plus an intercept, returning ``{"r2", "coef",
    "n"}``. Plain ``numpy.linalg.lstsq``, so the Porter-Zona lane needs no new dependency; the quantity the
    test reads is ``r2``, whose DEGRADATION relative to a matched cell is the ring signature."""
    if not rows:
        return {"r2": float("nan"), "coef": [], "n": 0}
    y = np.array([r[y_key] for r in rows], dtype=float)
    X = np.column_stack([np.ones(len(rows))] + [np.array([r[k] for r in rows], dtype=float) for k in x_keys])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    return {"r2": r2, "coef": coef.tolist(), "n": len(rows)}


def trailing_digit_rows(out: StageOutcome, *, key: dict | None = None) -> list[dict]:
    """Rows ``{seat, item, digit, target_item}`` for the code-bidding test [cramton_schwartz2000,
    pp. 236-244]: the trailing digit of each bid against a uniform null, and its regression on the seat's own
    target-slot index. Run per stage and tested for a TREND across stages rather than a level (design.md
    §9.3)."""
    rows = []
    for i in range(out.n_bidders):
        top = int(np.argmax(out.values[i]))
        for j in range(out.n_items):
            if np.isnan(out.bids[i, j]):
                continue
            rows.append({**(key or {}), "stage": out.stage, "seat": i, "item": j,
                         "digit": int(abs(int(out.bids[i, j])) % 10), "target_item": top})
    return rows

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
"""Optimal-stopping acceptance oracle: when is accepting the standing offer better than holding out?

Core recursion — Baarslag & Hindriks, "Accepting Optimally in Automated Negotiation with Incomplete
Information," AAMAS 2013, pp. 715-722, Eqs. (1)-(3) (http://www.ifaamas.org/Proceedings/aamas2013/docs/p715.pdf):

    v_0 = 0
    v_j = E[ max(X_{j-1}, v_{j-1}) ] - C          # j = rounds remaining; X_j ~ F_j the offer distribution
    accept x  iff  x >= v_j                        # Algorithm 1

with ``F_j`` = the offer-distribution mixture induced by the belief posterior (``offer_surplus_pmf`` below).
Closed form for a uniform opponent (their Prop. 3.1): ``v_j = 1/2 + v_{j-1}^2 / 2`` (reproduced by the unit
test). This module **generalizes** the recursion with a per-round discount ``delta`` and a disagreement
``flow`` so the reservation is an *endogenous, time-varying* continuation value tau_i(t) (McCall, "Economics
of Information and Job Search," QJE 84(1):113-126, 1970 — the reservation-wage recursion); the additive cost
``C`` and the discount ``delta`` are the two friction conventions and coincide with Baarslag at
``delta=1, flow=0``. An optional outside-option floor follows Li, Giampapa & Sycara, IEEE SMC-C 36(1):31-44,
2006 (reservation price = valuation - reservation utility; conservative order-statistic OU).

DESIGN WARNING (Sandholm & Vulkan, "Bargaining with Deadlines," AAAI-99, pp. 44-51): with a firm common
deadline and NO discounting, the unique sequential-equilibrium play is extreme brinkmanship — both wait until
the earlier deadline, then the deadline-bound party concedes the whole surplus. So if the game's only
impatience is a hard turn-count deadline, this oracle's "hold out" recommendation is rational but degenerate;
pass a ``discount < 1`` (or a breakdown-risk / outside-option) to make interior concession rational.

The single most diagnostic per-turn signal in practice (accept-too-early leaves surplus on the table;
never-accept blows the deadline).
"""
from __future__ import annotations

import numpy as np

from ._oracle_common import (Accept, GameTables, Oracle, Propose, Reject, Walk, effective_discount,
                             game_tables, make_verdict, offer_registry, rounds_left, seat_index)


# --------------------------------------------------------------------------------------------------------- #
# Backward-induction reservation values.
# --------------------------------------------------------------------------------------------------------- #
def reservation_values(values, probs, T: int, *, cost: float = 0.0, discount: float = 1.0,
                       flow: float = 0.0, pmfs=None, outside_value: float | None = None) -> list:
    """Backward-induction reservation curve ``[v_0, v_1, ..., v_T]`` where ``v_j`` is the reservation with
    ``j`` rounds remaining; **accept an offer of surplus x iff x >= v_j**.

        v_j = (1 - discount) * flow + discount * E_{X ~ F_{j-1}}[ max(X, v_{j-1}) ] - cost

    Parameters
    ----------
    values, probs : sequence[float]
        The stationary offer-surplus distribution ``F`` as a discrete pmf (support ``values``, masses
        ``probs``). Ignored if ``pmfs`` is given.
    T : int
        Horizon (max rounds remaining).
    cost : float
        Additive per-round search cost ``C`` (Baarslag friction).
    discount : float
        Per-round discount / no-breakdown probability ``delta`` in ``(0, 1]`` (McCall friction).
    flow : float
        Disagreement flow received while unagreed (enters the discounted continuation).
    pmfs : list[tuple[seq, seq]] | None
        Optional per-round distributions ``F_{j-1}``; ``pmfs[j-1] = (values, probs)`` used at step ``j`` for
        a time-varying offer distribution. Length must be >= ``T``.
    outside_value : float | None
        Optional floor on every ``v_j`` (a conservative outside-option reservation utility; Li-Giampapa-
        Sycara). The reservation never drops below it.

    Returns ``list[float]`` of length ``T + 1``.
    """
    out = [0.0]
    for j in range(1, T + 1):
        vals, ps = (pmfs[j - 1] if pmfs is not None else (values, probs))
        vals = np.asarray(vals, dtype=float)
        ps = np.asarray(ps, dtype=float)
        emax = float(np.sum(ps * np.maximum(vals, out[-1])))
        vj = (1.0 - discount) * flow + discount * emax - cost
        if outside_value is not None:
            vj = max(vj, outside_value)
        out.append(vj)
    return out


# --------------------------------------------------------------------------------------------------------- #
# Offer distribution induced by beliefs.
# --------------------------------------------------------------------------------------------------------- #
def offer_surplus_pmf(tables: GameTables, agent: int, accept_prob_fn=None, *, only_closable: bool = True,
                      only_ir: bool = True):
    """The distribution ``F`` of the surplus ``agent`` expects to *receive*, induced by the belief posterior.

    Each deal ``d`` is weighted by ``P(all opponents accept d)`` (so only deals that can actually close carry
    mass) and contributes its own surplus ``tables.surplus[d, agent]`` to the support.

    Parameters
    ----------
    tables : GameTables
        Precomputed surplus tables.
    agent : int
        Whose received-surplus distribution to build.
    accept_prob_fn : callable | None
        ``accept_prob_fn(deal) -> P(all opponents accept deal)``. Typically
        ``lambda d: prod_j belief_states[j].accept_prob(d)``. If None, all closable = uniform (full-info
        proxy: every IR deal equally offerable).
    only_closable : bool
        Drop deals with zero acceptance probability.
    only_ir : bool
        Drop deals with negative surplus for ``agent`` (below own threshold — never worth receiving).

    Returns ``(values, probs)`` — a normalized pmf. Empty support falls back to a point mass at surplus 0
    (i.e. "no acceptable offer expected", so the reservation collapses to the no-deal value).
    """
    surplus = tables.surplus[:, agent]
    D = tables.n_deals
    if accept_prob_fn is None:
        w = np.ones(D)
    else:
        w = np.array([float(accept_prob_fn(d)) for d in tables.deals])
    if only_ir:
        w = np.where(surplus >= 0.0, w, 0.0)
    if only_closable:
        w = np.where(w > 0.0, w, 0.0)
    if w.sum() <= 0:
        return np.array([0.0]), np.array([1.0])
    probs = w / w.sum()
    keep = probs > 0
    return surplus[keep], probs[keep]


# --------------------------------------------------------------------------------------------------------- #
# The oracle.
# --------------------------------------------------------------------------------------------------------- #
class AcceptanceOracle(Oracle):
    """Values accept / reject / propose / walk at one turn via optimal stopping.

    Parameters
    ----------
    agent : int
        The deciding seat.
    discount : float
        Per-round discount ``delta`` OVERRIDE. Default ``None`` = read the game's own ``discount`` /
        ``breakdown_risk`` via ``effective_discount`` (single source of truth); pass a float only to force a
        value. A nonzero discount is what makes interior concession rational (Sandholm-Vulkan, module
        docstring).
    cost : float
        Additive per-round search cost ``C``.
    flow : float
        Disagreement flow while unagreed.
    accept_prob_fn : callable | None
        ``deal -> P(all opponents accept)`` from the belief oracle; None = full-info uniform-offer proxy.
    outside_value : float | None
        Optional reservation floor (outside option).
    """

    name = "acceptance"

    def __init__(self, agent: int, *, discount: float | None = None, cost: float = 0.0, flow: float = 0.0,
                 accept_prob_fn=None, outside_value: float | None = None):
        self.agent = int(agent)
        self.discount = None if discount is None else float(discount)
        self.cost = float(cost)
        self.flow = float(flow)
        self.accept_prob_fn = accept_prob_fn
        self.outside_value = outside_value

    def _disc(self, override=None) -> float:
        d = override if override is not None else self.discount
        return 1.0 if d is None else float(d)

    # -- reusable scalar for strategies -------------------------------------------------------------------
    def reservation(self, tables: GameTables, rounds_left: int, discount: float | None = None) -> float:
        """The reservation surplus ``v_{rounds_left}`` given the belief-induced offer distribution."""
        vals, ps = offer_surplus_pmf(tables, self.agent, self.accept_prob_fn)
        curve = reservation_values(vals, ps, max(rounds_left, 0), cost=self.cost,
                                   discount=self._disc(discount), flow=self.flow,
                                   outside_value=self.outside_value)
        return curve[-1]

    def reservation_curve(self, tables: GameTables, T: int, discount: float | None = None) -> list:
        """The full endogenous reservation curve ``tau_i(rounds_left)`` for ``rounds_left = 0..T``."""
        vals, ps = offer_surplus_pmf(tables, self.agent, self.accept_prob_fn)
        return reservation_values(vals, ps, T, cost=self.cost, discount=self._disc(discount), flow=self.flow,
                                  outside_value=self.outside_value)

    def evaluate(self, game, history, agent, legal):
        """Value each legal action in surplus units and flag stopping errors.

        ``Accept(offer_id)`` is valued at its realized surplus for ``agent``; ``Reject``/``Propose``/``Walk``
        are valued at the continuation reservation ``v`` (Walk clamped at >= 0). The discount is read from the
        game (``effective_discount``) unless the oracle was constructed with an explicit override. Flags:
        ``premature_accept`` (an available Accept is below reservation), ``should_accept`` (the best live offer
        clears reservation), ``deadline_brinkmanship`` (delta ~ 1 with a hard deadline)."""
        agent = seat_index(game, agent) if agent is not None else self.agent
        disc = effective_discount(game, self.discount)
        tables = game_tables(game)
        offers = offer_registry(game, history)
        r_left = rounds_left(game, history)
        v = self.reservation(tables, r_left, disc)

        values: dict = {}
        best_offer_surplus = -np.inf
        for a in legal:
            if isinstance(a, Accept) and a.offer_id in offers:
                s = float(tables.surplus[tables.index[offers[a.offer_id]], agent])
                values[a] = s
                best_offer_surplus = max(best_offer_surplus, s)
            elif isinstance(a, Walk):
                values[a] = max(0.0, v)
            else:  # Reject / Propose / anything else = keep negotiating -> continuation value
                values[a] = v

        best = max(values, key=values.get) if values else None
        flags = []
        for a in legal:
            if isinstance(a, Accept) and a.offer_id in offers:
                s = tables.surplus[tables.index[offers[a.offer_id]], agent]
                if s < v:
                    flags.append("premature_accept")
                    break
        if np.isfinite(best_offer_surplus) and best_offer_surplus >= v:
            flags.append("should_accept")
        if disc >= 0.999 and r_left > 1:
            flags.append("deadline_brinkmanship")
        extra = {"reservation": v, "rounds_left": r_left,
                 "best_offer_surplus": (None if not np.isfinite(best_offer_surplus) else best_offer_surplus)}
        return make_verdict(values, best=best, flags=flags, extra=extra)


class ThresholdOracle(Oracle):
    """The trivial hard-violation detector: accepting or proposing a deal below one's *own* threshold is a
    strict rationality error (agreeing below your BATNA is worse than no deal — Abdelnabi et al.'s "wrong
    deals" metric, which runs 7-20% even for strong models). Cheap (one surplus lookup per action); values
    each action at the agent's own surplus (Walk/Reject at 0) and flags the individual-rationality violations.

    This complements the stopping oracle: ``AcceptanceOracle`` says *when* holding out beats accepting a
    good offer, while ``ThresholdOracle`` catches the strictly-dominated moves regardless of timing."""

    name = "threshold"

    def __init__(self, agent: int | None = None):
        self.agent = agent

    def evaluate(self, game, history, agent, legal):
        """Value ``Accept``/``Propose`` at the agent's own surplus (Walk/Reject at 0); ``best`` is the
        surplus-maximizing individually-rational move. Flags: ``below_threshold_accept`` (an available Accept
        is below the agent's BATNA) and ``below_threshold_propose`` (proposing a deal below one's own BATNA)."""
        agent = seat_index(game, agent) if agent is not None else (self.agent or 0)
        tables = game_tables(game)
        offers = offer_registry(game, history)
        values: dict = {}
        flags: list[str] = []
        for a in legal:
            if isinstance(a, Accept) and a.offer_id in offers:
                s = float(tables.surplus[tables.index[offers[a.offer_id]], agent])
                values[a] = s
                if s < 0:
                    flags.append("below_threshold_accept")
            elif isinstance(a, Propose):
                idx = tables.index.get(tuple(int(x) for x in a.deal))
                s = float(tables.surplus[idx, agent]) if idx is not None else 0.0
                values[a] = s
                if s < 0:
                    flags.append("below_threshold_propose")
            elif isinstance(a, (Walk, Reject)):
                values[a] = 0.0
            else:
                values[a] = 0.0
        best = max(values, key=values.get) if values else None
        return make_verdict(values, best=best, flags=sorted(set(flags)),
                            extra={"any_ir_violation": bool(flags)})

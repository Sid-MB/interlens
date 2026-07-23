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
"""The executable rational / scripted negotiator zoo as **policies** (``state -> action``), the computable
opponent pool the LLMs are measured against.

Concession curves — Faratin, Sierra & Jennings, "Negotiation decision functions for autonomous agents,"
Robotics and Autonomous Systems 24(3-4):159-182, 1998, §3.1: time-dependent tactic
``alpha(t) = k + (1 - k) * (t / T)^{1/beta}`` with **Boulware ``beta < 1``** (concede near the deadline) and
**Conceder ``beta > 1``** (concede early); utility-space restatement Baarslag thesis, TU Delft 2014, §2.3.3.

MiCRO — de Jonge, IJCAI 2022, pp. 223-229 (multilateral extension arXiv:2510.17401): sort own outcomes
descending; with ``m`` distinct offers made and ``n_min`` the minimum distinct-offer count across opponents,
concede one new outcome iff ``m <= n_min`` else repeat; accept iff incoming >= the next offer you'd make.
Parameter-free, ordinal-only.

Tit-for-tat — Faratin §3.3 behavior-dependent tactic (reproduce the opponent's concession). Tough/Hardliner
— always demand the own optimum. Acceptance conditions AC_next / AC_const / AC_time / AC_combi — Baarslag,
Hindriks & Jonker, "Acceptance Conditions in Automated Negotiation," SCI 435, 2013, eqs. (4.4)-(4.8).

``BayesianRationalPolicy`` composes the belief + acceptance + best-response oracles — the headline rational
agent: update beliefs from observed offers, best-respond on proposals, accept by optimal stopping.

All policies return typed actions (``Propose``/``Accept``/``Reject``/``Walk``) and read a ``NegotiationState``,
so a ``PolicyParticipant`` wrapping any of them is an interchangeable seat with an LLM participant.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod

import numpy as np

from ._oracle_common import (Accept, NegotiationState, Propose, Reject, Walk, deal_list)
from .acceptance import AcceptanceOracle
from .beliefs import BeliefOracle
from .bestresponse import BestResponseOracle, value_to_go_beliefs


# --------------------------------------------------------------------------------------------------------- #
# Own-utility bookkeeping shared by the policies.
# --------------------------------------------------------------------------------------------------------- #
class _OwnUtil:
    """Cached own-utility view of the deal space for one policy: deals, raw utility, and min-max-normalized
    utility, keyed by the space identity so repeated turns don't re-enumerate."""

    def __init__(self):
        self._cache: dict = {}

    def get(self, state: NegotiationState):
        # Key by (space, seat): the cached utility column is seat-specific, so a policy instance reused across
        # seats (or concurrent seats sharing one policy) must not get another seat's utilities. Reads/inserts
        # here are idempotent per key, so concurrent access at worst recomputes — it never corrupts.
        key = (id(state.space), state.seat)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        if state.tables is not None:
            deals = state.tables.deals
            u = np.asarray(state.tables.utility[:, state.seat], dtype=float)
        else:
            deals = deal_list(state.space)
            u = np.asarray([state.sheet.utility(d) for d in deals], dtype=float)
        span = float(u.max() - u.min())
        u_norm = (u - u.min()) / span if span > 1e-12 else np.zeros_like(u)
        out = (deals, u, u_norm)
        self._cache[key] = out
        return out

    def index(self, state, deal) -> int:
        deals, _, _ = self.get(state)
        if state.tables is not None:
            return state.tables.index[tuple(int(x) for x in deal)]
        return deals.index(tuple(int(x) for x in deal))


def _reserve_norm(state, u, u_norm) -> float:
    """The agent's reservation threshold expressed on the normalized ``[0, 1]`` own-utility scale."""
    span = float(u.max() - u.min())
    if span <= 1e-12:
        return 0.0
    return float((getattr(state.sheet, "threshold", u.min()) - u.min()) / span)


# --------------------------------------------------------------------------------------------------------- #
# Acceptance conditions (Baarslag taxonomy). All operate on the agent's own normalized utilities.
# --------------------------------------------------------------------------------------------------------- #
class AcceptanceCondition(ABC):
    """Decide whether to accept the standing offer given the agent's own utility of it (``incoming``) and of
    the deal it is about to propose (``planned_next``), both on the normalized ``[0, 1]`` scale."""

    @abstractmethod
    def accepts(self, state: NegotiationState, incoming: float, planned_next: float) -> bool:
        ...


class ACNext(AcceptanceCondition):
    """AC_next(alpha, beta): accept iff ``alpha * incoming + beta >= planned_next`` — the incoming bid is at
    least as good as what you were about to send (Baarslag eq. 4.4; alpha=1, beta=0 standard)."""

    def __init__(self, alpha: float = 1.0, beta: float = 0.0):
        self.alpha, self.beta = float(alpha), float(beta)

    def accepts(self, state, incoming, planned_next):
        return self.alpha * incoming + self.beta >= planned_next


class ACConst(AcceptanceCondition):
    """AC_const(alpha): accept iff ``incoming >= alpha`` (eq. 4.6)."""

    def __init__(self, alpha: float = 0.7):
        self.alpha = float(alpha)

    def accepts(self, state, incoming, planned_next):
        return incoming >= self.alpha


class ACTime(AcceptanceCondition):
    """AC_time(T): accept anything once the time fraction reaches ``t_frac`` (eq. 4.7)."""

    def __init__(self, t_frac: float = 0.9):
        self.t_frac = float(t_frac)

    def accepts(self, state, incoming, planned_next):
        return state.time_fraction >= self.t_frac


class ACCombi(AcceptanceCondition):
    """AC_combi(T, alpha): ``AC_next OR (AC_time(T) AND incoming >= alpha)`` (eq. 4.8; combi variants
    empirically dominate)."""

    def __init__(self, t_frac: float = 0.9, alpha: float = 0.6, next_alpha: float = 1.0):
        self.time = ACTime(t_frac)
        self.next = ACNext(next_alpha)
        self.alpha = float(alpha)

    def accepts(self, state, incoming, planned_next):
        return self.next.accepts(state, incoming, planned_next) or (
            self.time.accepts(state, incoming, planned_next) and incoming >= self.alpha)


# --------------------------------------------------------------------------------------------------------- #
# Policy base + shared proposal/acceptance mechanics.
# --------------------------------------------------------------------------------------------------------- #
class Policy(ABC):
    """A deterministic (or seeded) negotiation policy: ``policy(state) -> action``. Subclasses set ``name``
    and implement ``act``. ``__call__`` is the invocation surface a ``PolicyParticipant`` binds to."""

    name: str = "policy"

    def __init__(self):
        self._own = _OwnUtil()

    def __call__(self, state: NegotiationState):
        if getattr(state, "must_vote", False):
            return self.vote(state)
        return self.act(state)

    @abstractmethod
    def act(self, state: NegotiationState):
        ...

    def vote(self, state: NegotiationState):
        """The terminal individually-rational vote on the standing offer when the scenario allows only
        accept/reject/walk (``state.must_vote``). Accept any offer that clears this seat's threshold (surplus
        >= 0), since the sole alternative is no-deal = 0; otherwise reject it (or walk if there is no standing
        offer). Shared by every policy — proposing in a vote-only phase is an economic-legality violation, so
        no policy must ever fall through to a Propose here."""
        deal = state.standing_deal
        if deal is None or state.standing is None:
            return Walk()
        return Accept(state.standing) if state.sheet.surplus(deal) >= 0 else Reject(state.standing)

    # -- shared helpers -----------------------------------------------------------------------------------
    def _propose_at_or_above(self, state, target_norm: float):
        """Choose a ``Propose`` action for the least own-concession deal at/above ``target_norm`` that is
        individually rational; among ties prefer the deal that most benefits the other parties (if full-info
        tables are available) so agreement is easier. Falls back to the own optimum if nothing clears."""
        deals, u, u_norm = self._own.get(state)
        thr = getattr(state.sheet, "threshold", -np.inf)
        ir = u >= thr
        mask = (u_norm >= target_norm - 1e-9) & ir
        if not mask.any():
            mask = ir if ir.any() else np.ones_like(u, dtype=bool)
            # nothing at/above target -> concede to the best IR deal (closest to target from below)
            idx = int(np.argmax(np.where(mask, u_norm, -np.inf)))
            return Propose(tuple(int(x) for x in deals[idx]))
        cand = np.where(mask)[0]
        if state.tables is not None and len(state.opponents) > 0:
            opp_sum = state.tables.utility[:, list(state.opponents)].sum(axis=1)
            pick = int(cand[int(np.argmax(opp_sum[cand]))])
        else:
            # least over-concession: smallest own utility still >= target
            pick = int(cand[int(np.argmin(u_norm[cand]))])
        return Propose(tuple(int(x) for x in deals[pick]))

    def _maybe_accept(self, state, planned_next_norm: float, acceptance: AcceptanceCondition):
        """Return an ``Accept`` action if the standing offer clears both individual rationality and the
        acceptance condition; else None (caller then proposes)."""
        deal = state.standing_deal
        if deal is None or state.standing is None:
            return None
        deals, u, u_norm = self._own.get(state)
        idx = self._own.index(state, deal)
        thr = getattr(state.sheet, "threshold", -np.inf)
        if u[idx] < thr:                       # never accept below reservation (IR)
            return None
        if acceptance.accepts(state, float(u_norm[idx]), planned_next_norm):
            return Accept(state.standing)
        return None


# --------------------------------------------------------------------------------------------------------- #
# Time-dependent concession (Faratin Boulware / Conceder).
# --------------------------------------------------------------------------------------------------------- #
class TimeDependentPolicy(Policy):
    """Faratin time-dependent tactic: concede own utility along ``alpha(t) = k + (1 - k) (t/T)^{1/beta}``
    toward the reservation, propose the least-concession IR deal at/above the current target, and accept per
    ``acceptance``.

    Parameters
    ----------
    beta : float
        Concession exponent. ``beta < 1`` = Boulware (concede near deadline); ``beta > 1`` = Conceder;
        ``beta = 1`` linear.
    k : float
        First-offer concession constant in ``[0, 1]`` (0 = open at the own optimum).
    acceptance : AcceptanceCondition
        Acceptance rule (default AC_next).
    name : str
        Display name.
    """

    def __init__(self, beta: float, *, k: float = 0.0, acceptance: AcceptanceCondition | None = None,
                 name: str | None = None):
        super().__init__()
        self.beta = float(beta)
        self.k = float(k)
        self.acceptance = acceptance or ACNext()
        self.name = name or (f"boulware(beta={beta})" if beta < 1 else
                             f"conceder(beta={beta})" if beta > 1 else "linear")

    @classmethod
    def boulware(cls, beta: float = 0.2, **kw):
        """A Boulware agent (``beta < 1``; default 0.2)."""
        return cls(beta, **kw)

    @classmethod
    def conceder(cls, beta: float = 5.0, **kw):
        """A Conceder agent (``beta > 1``; default 5.0)."""
        return cls(beta, **kw)

    def concession(self, t: float) -> float:
        """The Faratin concession level ``alpha(t) = k + (1 - k) t^{1/beta}`` at time fraction ``t`` in
        ``[0, 1]`` (0 = demand the optimum, 1 = conceded to the reservation)."""
        t = min(max(t, 0.0), 1.0)
        return self.k + (1.0 - self.k) * (t ** (1.0 / self.beta))

    def target_norm(self, state) -> float:
        """The normalized own-utility level to demand now: ``1 - concession(t) * (1 - reserve)``."""
        deals, u, u_norm = self._own.get(state)
        reserve = _reserve_norm(state, u, u_norm)
        return 1.0 - self.concession(state.time_fraction) * (1.0 - reserve)

    def act(self, state: NegotiationState):
        target = self.target_norm(state)
        proposal = self._propose_at_or_above(state, target)
        _, u, u_norm = self._own.get(state)
        planned_norm = float(u_norm[self._own.index(state, proposal.deal)])
        acc = self._maybe_accept(state, planned_norm, self.acceptance)
        return acc if acc is not None else proposal


# --------------------------------------------------------------------------------------------------------- #
# MiCRO.
# --------------------------------------------------------------------------------------------------------- #
class MiCROPolicy(Policy):
    """MiCRO (de Jonge 2022; multilateral variant arXiv:2510.17401): minimal-concession, parameter-free.
    Concede one new outcome iff distinct-offers-made ``m <= n_min`` (min distinct offers across opponents),
    else repeat a previous offer; accept iff the standing offer is at least as good as the next outcome you
    would propose."""

    def __init__(self, *, seed: int = 0, name: str = "micro"):
        super().__init__()
        self.name = name
        self._rng = random.Random(seed)

    def _ranked(self, state):
        deals, u, u_norm = self._own.get(state)
        order = list(np.argsort(-u))          # descending own utility
        thr = getattr(state.sheet, "threshold", -np.inf)
        ranked = [i for i in order if u[i] >= thr] or order
        return deals, u, u_norm, ranked

    def _n_min(self, state) -> int:
        """Minimum distinct-offer count across opponents (approximated from the aggregated ``received`` list
        when per-opponent splits are unavailable)."""
        return len({tuple(int(x) for x in d) for d in state.received})

    def act(self, state: NegotiationState):
        deals, u, u_norm, ranked = self._ranked(state)
        m = len({tuple(int(x) for x in d) for d in state.my_offers})
        n_min = self._n_min(state)
        next_idx = ranked[min(m, len(ranked) - 1)]
        next_norm = float(u_norm[next_idx])
        # acceptance: accept iff standing offer >= the next outcome I'd make
        deal = state.standing_deal
        if deal is not None and state.standing is not None:
            inc_idx = self._own.index(state, deal)
            thr = getattr(state.sheet, "threshold", -np.inf)
            if u[inc_idx] >= thr and u_norm[inc_idx] >= next_norm - 1e-9:
                return Accept(state.standing)
        if m <= n_min:
            return Propose(tuple(int(x) for x in deals[next_idx]))     # concede one new outcome
        # else repeat a previous offer (random among already-made), or the current best if none yet
        if state.my_offers:
            return Propose(tuple(int(x) for x in self._rng.choice(list(state.my_offers))))
        return Propose(tuple(int(x) for x in deals[ranked[0]]))


# --------------------------------------------------------------------------------------------------------- #
# Naive (relative) tit-for-tat.
# --------------------------------------------------------------------------------------------------------- #
class NaiveTitForTatPolicy(Policy):
    """Behavior-dependent tit-for-tat (Faratin §3.3): mirror the opponent's most recent concession (measured
    in this agent's own normalized utility) as an equal concession from the agent's last demand; start near
    the own optimum. Accept per ``acceptance``."""

    def __init__(self, *, acceptance: AcceptanceCondition | None = None, name: str = "naive-tft"):
        super().__init__()
        self.acceptance = acceptance or ACNext()
        self.name = name

    def act(self, state: NegotiationState):
        deals, u, u_norm = self._own.get(state)
        reserve = _reserve_norm(state, u, u_norm)
        recv = list(state.received)
        concession = 0.0
        if len(recv) >= 2:
            prev = float(u_norm[self._own.index(state, recv[-2])])
            now = float(u_norm[self._own.index(state, recv[-1])])
            concession = max(0.0, now - prev)         # opponent moved toward me by this much (my scale)
        # Stateless demand: mirror the opponent's latest concession off MY last actual offer (read from the
        # state, not instance memory) so the policy is safe to reuse across seats / concurrent turns.
        last_demand = (float(u_norm[self._own.index(state, state.my_offers[-1])])
                       if state.my_offers else 1.0)
        target = max(reserve, last_demand - concession)
        proposal = self._propose_at_or_above(state, target)
        planned_norm = float(u_norm[self._own.index(state, proposal.deal)])
        acc = self._maybe_accept(state, planned_norm, self.acceptance)
        return acc if acc is not None else proposal


# --------------------------------------------------------------------------------------------------------- #
# Tough / hardliner.
# --------------------------------------------------------------------------------------------------------- #
class ToughPolicy(Policy):
    """Hardliner: always demand the own optimum; accept only offers within ``accept_frac`` of the own max
    (and above reservation)."""

    def __init__(self, *, accept_frac: float = 0.95, name: str = "tough"):
        super().__init__()
        self.accept_frac = float(accept_frac)
        self.name = name

    def act(self, state: NegotiationState):
        deals, u, u_norm = self._own.get(state)
        best = int(np.argmax(u))
        deal = state.standing_deal
        if deal is not None and state.standing is not None:
            idx = self._own.index(state, deal)
            thr = getattr(state.sheet, "threshold", -np.inf)
            if u[idx] >= thr and u_norm[idx] >= self.accept_frac:
                return Accept(state.standing)
        return Propose(tuple(int(x) for x in deals[best]))


# --------------------------------------------------------------------------------------------------------- #
# Headline composed rational agent.
# --------------------------------------------------------------------------------------------------------- #
class BayesianRationalPolicy(Policy):
    """The composed rational negotiator = belief oracle + acceptance oracle + best-response oracle.

    Each turn: (1) update beliefs over opponents from observed offers (private info) or read them off known
    sheets (full info); (2) build the opponent acceptance-probability table; (3) accept the standing offer if
    its surplus clears the optimal-stopping reservation, else propose the best-response deal; (4) walk if no
    individually-rational deal can plausibly close before the deadline.

    Parameters
    ----------
    discount : float | None
        Per-round discount ``delta`` OVERRIDE for the acceptance and best-response oracles. Default ``None`` =
        use ``state.discount`` (which scenario-runner sets from the game's ``discount``/``breakdown_risk``) —
        the state is a policy's single source of truth, analogous to the game for an oracle.
    walk_if_hopeless : bool
        If True, ``Walk`` when the best-response proposal value is <= 0 at the final round.
    name : str
        Display name.
    """

    def __init__(self, *, discount: float | None = None, walk_if_hopeless: bool = True,
                 name: str = "bayes-rational"):
        super().__init__()
        self.discount = None if discount is None else float(discount)
        self.walk_if_hopeless = bool(walk_if_hopeless)
        self.name = name

    def _n_seats(self, state) -> int:
        """Number of seats implied by the state (full-info tables width, else own seat + opponents)."""
        if state.tables is not None:
            return state.tables.n_agents
        idxs = [state.seat, *state.opponents]
        return max(idxs) + 1 if idxs else 1

    def _accept_prob_table(self, state, tables):
        """``(n_seats, )``-wide opponent acceptance-probability table ``(D, n)``.

        Full info (``state.tables`` present): 1.0 iff the opponent's surplus is nonnegative, else 0.0 — the
        myopic IR acceptance model. Private info: the posterior accept-probability per opponent from a belief
        oracle built FRESH from ``state.received`` this call (own column forced to 1.0).

        The belief oracle is local to the call (not cached on the policy): it is fully determined by
        ``state.received`` and ``update_from_offers`` rebuilds it from scratch anyway, so persisting it would
        buy nothing and would make one policy instance shared across concurrent seats race on a mutable
        member (the reported 'dict changed size during iteration')."""
        from ._oracle_common import issue_sizes
        n = tables.n_agents
        if state.tables is not None:
            ap = (state.tables.surplus >= 0.0).astype(float)
            ap[:, state.seat] = 1.0
            return ap
        belief = BeliefOracle(state.seat)
        option_counts = issue_sizes(state.space, [state.sheet])
        offers = ({opp: list(state.received) for opp in state.opponents} if state.opponents else {})
        belief.update_from_offers(offers, option_counts)
        ap = np.ones((tables.n_deals, n))
        for opp, st in belief.states.items():
            ap[:, opp] = st.accept_prob_matrix(tables.deals_arr)   # vectorized over all deals
        return ap

    def _tables(self, state):
        """Full-info tables when available; otherwise a padded ``GameTables`` carrying only this seat's own
        utility column (opponents' columns are zeros — the belief path never reads opponents' *surplus*, only
        their acceptance probability, so the padding is sound)."""
        if state.tables is not None:
            return state.tables
        from ._oracle_common import GameTables
        deals, u, _ = self._own.get(state)
        n = self._n_seats(state)
        deals_arr = np.asarray(deals, dtype=int)
        util = np.zeros((len(deals), n))
        util[:, state.seat] = u
        thr = np.zeros(n)
        thr[state.seat] = float(getattr(state.sheet, "threshold", 0.0))
        surplus = util - thr[None, :]
        index = {d: i for i, d in enumerate(deals)}
        return GameTables(list(deals), index, deals_arr, util, surplus, thr)

    def act(self, state: NegotiationState):
        disc = self.discount if self.discount is not None else float(state.discount)
        tables = self._tables(state)
        ap = self._accept_prob_table(state, tables)
        opp = tuple(state.opponents)
        seq = [(state.seat + k) % tables.n_agents for k in range(tables.n_agents)]
        br = BestResponseOracle(state.seat, discount=disc, accept_prob=ap)

        acc_fn = (lambda d: float(np.prod([ap[tables.index[tuple(int(x) for x in d)], o] for o in opp]))
                  if opp else 1.0)
        acceptor = AcceptanceOracle(state.seat, discount=disc, accept_prob_fn=acc_fn)
        r_left = max(state.deadline - state.round + 1, 1)
        v = acceptor.reservation(tables, r_left)

        # accept the standing offer if its surplus clears the optimal-stopping reservation
        deal = state.standing_deal
        if deal is not None and state.standing is not None:
            s = float(tables.surplus[tables.index[tuple(int(x) for x in deal)], state.seat])
            if s >= v and s >= 0:
                return Accept(state.standing)

        # else best-respond with a proposal, using the DP continuation value
        Vi = value_to_go_beliefs(tables, state.seat, seq, state.deadline, disc, ap,
                                 br._model_opp_proposals(tables, None))
        cont = np.full(tables.n_agents, disc * float(Vi[min(2, state.deadline + 1)]))
        prop_vals = br.propose_values(tables, cont)
        best_idx = int(np.argmax(prop_vals))
        if self.walk_if_hopeless and prop_vals[best_idx] <= 0 and r_left <= 1:
            return Walk()
        return Propose(tuple(int(x) for x in tables.deals[best_idx]))


# Convenience registry of the scripted zoo (excludes the composed Bayesian agent, which needs a discount).
ZOO = {
    "boulware": lambda: TimeDependentPolicy.boulware(),
    "conceder": lambda: TimeDependentPolicy.conceder(),
    "linear": lambda: TimeDependentPolicy(1.0, name="linear"),
    "micro": MiCROPolicy,
    "naive-tft": NaiveTitForTatPolicy,
    "tough": ToughPolicy,
}

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
"""Banks-Duggan stationary-equilibrium oracle for the multilateral unanimity bargaining game — the
theoretically-grounded multilateral reference no LLM negotiation benchmark ships.

Model (random-proposer, closed rule, unanimity): Baron & Ferejohn, "Bargaining in Legislatures," APSR
83(4):1181-1206, 1989; generalized to arbitrary alternative spaces / utilities by Banks & Duggan, "A
Bargaining Model of Collective Choice," APSR 94(1):73-88, 2000, and QJPS 1(1):49-85, 2006. No-delay
stationary characterization with continuation values ``v`` and disagreement flows ``tau``:

    A_i(v) = { d in D : u_i(d) >= (1 - delta) * tau_i + delta * v_i }     # i's acceptance set
    A(v)   = intersection_i A_i(v)                                        # unanimity social acceptance set
    x_j*(v) = argmax_{d in A(v)} u_j(d)                                   # proposer j best-in-set (else delay)
    v_i     = sum_j p_j * u_i(x_j*(v))   (+ delay branch)                 # fixed point

Solved by damped fixed-point iteration ``v^{k+1} = (1 - lambda) v^k + lambda * T(v^k)`` over the enumerated
``D`` (each sweep ``O(n * |D|)``); a softmax-over-ties proposer rule (``tie_temperature > 0``) is available as
the fallback when the discrete argmax correspondence makes the hard iteration cycle.

Sanity anchor (built in, ``divide_the_dollar`` + ``okada_closed_form``): Okada, "A Noncooperative Coalitional
Bargaining Game with Random Proposers," GEB 16(1):97-108, 1996 — the unanimity closed form is proposer keeps
``1 - delta (n-1)/n``, each responder gets ``delta/n``, and ``v_i = 1/n``.

Caveats (docstring, not asserted): Eraslan, "Uniqueness of Stationary Equilibrium Payoffs in the Baron-
Ferejohn Model," JET 103(1):11-30, 2002, gives uniqueness for ``q < n`` rules; general *unanimity* games can
have delay / multiplicity / non-existence of a pure no-delay equilibrium (Britz, Herings & Predtetchinski).
Existence here is in mixed proposal strategies with pure stage-undominated voting on the finite (compact) D.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from ._oracle_common import (GameTables, Oracle, Propose, current_round, effective_discount, game_tables,
                             make_verdict, proposer_sequence, seat_index, softmax)

_NEG = -1e18


@dataclass
class EquilibriumSolution:
    """Result of the fixed-point solve.

    Attributes
    ----------
    values : np.ndarray
        Stationary continuation values ``v*`` (shape ``(n,)``).
    proposals : dict[int, int]
        Per-proposer equilibrium deal index ``x_j*`` (``-1`` if the proposer delays / no social set).
    residual : float
        Final fixed-point residual ``max|T(v) - v|``.
    converged : bool
        Whether ``residual < tol`` within ``max_iter``.
    social_set_size : int
        ``|A(v*)|`` at the solution.
    """

    values: np.ndarray
    proposals: dict
    residual: float
    converged: bool
    social_set_size: int


def solve_equilibrium(tables: GameTables, *, discount: float = 0.95, thresholds=None, proposer_probs=None,
                      damping: float = 0.5, max_iter: int = 1000, tol: float = 1e-9,
                      tie_temperature: float = 0.0, v_init=None) -> EquilibriumSolution:
    """Damped fixed-point solve for the Banks-Duggan stationary continuation values.

    Parameters
    ----------
    tables : GameTables
        Utility tables for the game.
    discount : float
        Common discount ``delta`` in ``(0, 1]``.
    thresholds : sequence[float] | None
        Disagreement flows ``tau_i`` (default: ``tables.thresholds``).
    proposer_probs : sequence[float] | None
        Recognition probabilities ``p_j`` (default uniform ``1/n``).
    damping : float
        Relaxation ``lambda`` in ``(0, 1]`` for ``v <- (1-lambda) v + lambda T(v)``.
    max_iter, tol : int, float
        Iteration budget and convergence tolerance on the residual.
    tie_temperature : float
        If ``> 0``, the proposer's outcome is a softmax-over-``A(v)`` average of utilities (smooths cycles)
        rather than a hard best-in-set.
    v_init : sequence[float] | None
        Optional initial ``v`` (default column means of utility).
    """
    U = tables.utility
    n = U.shape[1]
    tau = np.asarray(thresholds if thresholds is not None else tables.thresholds, dtype=float)
    p = (np.full(n, 1.0 / n) if proposer_probs is None
         else np.asarray(proposer_probs, dtype=float) / np.sum(proposer_probs))
    v = (U.mean(axis=0).astype(float) if v_init is None else np.asarray(v_init, dtype=float).copy())

    residual = np.inf
    converged = False
    proposals: dict = {}
    social = np.zeros(U.shape[0], dtype=bool)
    for _ in range(max_iter):
        rhs = (1.0 - discount) * tau + discount * v            # (n,) acceptance RHS
        social = np.all(U >= rhs[None, :], axis=1)             # unanimity social acceptance set
        Tv = np.zeros(n)
        proposals = {}
        for j in range(n):
            if social.any():
                if tie_temperature > 0:
                    in_set = np.where(social)[0]
                    wts = softmax(U[in_set, j], temperature=tie_temperature)
                    outcome = wts @ U[in_set, :]               # smoothed (n,)
                    dstar = int(in_set[int(np.argmax(U[in_set, j]))])
                    proposals[j] = dstar
                else:
                    cand = np.where(social, U[:, j], _NEG)
                    dstar = int(np.argmax(cand))
                    if U[dstar, j] >= rhs[j]:
                        outcome = U[dstar]
                        proposals[j] = dstar
                    else:
                        outcome = rhs                          # delay
                        proposals[j] = -1
            else:
                outcome = rhs
                proposals[j] = -1
            Tv += p[j] * outcome
        residual = float(np.max(np.abs(Tv - v)))
        v = (1.0 - damping) * v + damping * Tv
        if residual < tol:
            converged = True
            break
    return EquilibriumSolution(v, proposals, residual, converged, int(social.sum()))


# --------------------------------------------------------------------------------------------------------- #
# Okada divide-the-dollar sanity anchor.
# --------------------------------------------------------------------------------------------------------- #
def divide_the_dollar(n: int, steps: int) -> GameTables:
    """A discrete divide-the-dollar TU game as ``GameTables``: deals = integer allocations of ``steps`` units
    among ``n`` players (compositions), ``u_i = share_i = units_i / steps``, ``tau = 0``. Used as the Okada
    unanimity sanity anchor for the equilibrium solver."""
    comps = [c for c in itertools.product(range(steps + 1), repeat=n) if sum(c) == steps]
    deals = [tuple(c) for c in comps]
    deals_arr = np.asarray(deals, dtype=int)
    utility = deals_arr.astype(float) / steps
    thresholds = np.zeros(n)
    index = {d: i for i, d in enumerate(deals)}
    return GameTables(deals, index, deals_arr, utility, utility.copy(), thresholds)


def okada_closed_form(n: int, delta: float) -> dict:
    """The Okada 1996 unanimity closed form: ``{"proposer_keeps": 1 - delta(n-1)/n, "responder_gets":
    delta/n, "value": 1/n}``."""
    return {"proposer_keeps": 1.0 - delta * (n - 1) / n, "responder_gets": delta / n, "value": 1.0 / n}


# --------------------------------------------------------------------------------------------------------- #
# The oracle.
# --------------------------------------------------------------------------------------------------------- #
class EquilibriumOracle(Oracle):
    """Mounts the stationary equilibrium as a per-turn reference: what the standing offer *should* look like
    for whichever seat currently proposes, plus the proposer-power decomposition ``v*``.

    Parameters mirror ``solve_equilibrium`` (``discount``/``damping``/``max_iter``/``tol``/
    ``tie_temperature``/``proposer_probs``). ``discount`` defaults to ``None`` = read the game's own
    ``discount`` / ``breakdown_risk`` (single source of truth). ``agent`` (optional) is the seat whose actions
    are valued.
    """

    name = "equilibrium"

    def __init__(self, agent: int | None = None, *, discount: float | None = None, damping: float = 0.5,
                 max_iter: int = 1000, tol: float = 1e-9, tie_temperature: float = 0.0,
                 proposer_probs=None):
        self.agent = agent
        self.discount = None if discount is None else float(discount)
        self.damping = float(damping)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.tie_temperature = float(tie_temperature)
        self.proposer_probs = proposer_probs

    def solve(self, game) -> EquilibriumSolution:
        """Solve the stationary equilibrium for ``game`` (cached on the game object). The discount is read
        from the game (``effective_discount``) unless an explicit override was passed to the constructor."""
        cached = getattr(game, "_equilibrium_cache", None)
        if cached is not None:
            return cached
        tables = game_tables(game)
        sol = solve_equilibrium(tables, discount=effective_discount(game, self.discount), damping=self.damping,
                                max_iter=self.max_iter, tol=self.tol,
                                tie_temperature=self.tie_temperature, proposer_probs=self.proposer_probs)
        try:
            game._equilibrium_cache = sol
        except Exception:
            pass
        return sol

    def evaluate(self, game, history, agent, legal):
        """Value the current proposer's legal ``Propose`` actions against the equilibrium best-in-set: the
        equilibrium proposal is ``best``; each ``Propose(deal)`` is valued by the proposer's utility of that
        deal (0 outside the social acceptance set is not imposed — the value is the raw utility, and the flag
        ``outside_social_set`` marks proposals ``A(v*)`` would not sustain). ``extra`` carries ``v*`` and the
        per-proposer equilibrium deals."""
        tables = game_tables(game)
        sol = self.solve(game)
        seq = proposer_sequence(game)
        t = current_round(game, history)
        proposer = int(seq[(t - 1) % len(seq)]) if agent is None else seat_index(game, agent)
        disc = effective_discount(game, self.discount)
        eq_idx = sol.proposals.get(proposer, -1)
        rhs = (1.0 - disc) * tables.thresholds + disc * sol.values
        social = np.all(tables.utility >= rhs[None, :], axis=1)

        values: dict = {}
        flags: list[str] = []
        for a in legal:
            if isinstance(a, Propose):
                idx = tables.index.get(tuple(int(x) for x in a.deal))
                if idx is None:
                    values[a] = _NEG
                    continue
                values[a] = float(tables.utility[idx, proposer])
                if not social[idx]:
                    flags.append("outside_social_set")
            else:
                values[a] = float(sol.values[proposer])   # continuation value of not closing now
        # ``best`` is the equilibrium proposal when it is actually on offer, else the best legal action; the
        # equilibrium deal is always surfaced in ``extra`` as the reference standing offer.
        eq_action = Propose(tables.deals[eq_idx]) if eq_idx >= 0 else None
        if eq_action is not None and eq_action in values:
            best = eq_action
        elif values:
            best = max(values, key=values.get)
        else:
            best = eq_action
        extra = {"equilibrium_values": sol.values, "proposer": proposer,
                 "equilibrium_deal": (tables.deals[eq_idx] if eq_idx >= 0 else None),
                 "social_set_size": sol.social_set_size, "converged": sol.converged,
                 "residual": sol.residual}
        return make_verdict(values, best=best, flags=sorted(set(flags)), extra=extra)

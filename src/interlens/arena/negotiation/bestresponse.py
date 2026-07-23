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
"""Exact expectimax best-response oracle over (remaining rounds x deal space x type posterior).

Yields the headline **per-turn surplus-loss** metric ``V(oracle action) - V(agent action)`` in surplus units
(the centipawn-loss analog: Regan & Haworth, "Intrinsic Chess Ratings," AAAI 2011; McIlroy-Young et al.,
KDD 2020) and **revealed-strategy exploitability** against fixed counterparts (Johanson, Waugh, Bowling &
Zinkevich, "Accelerating Best Response Calculation in Large Extensive Games," IJCAI 2011, pp. 258-265).

WHY exact posterior-averaging rather than MCTS/determinization: at our scale (|D| ~ 720, T ~ 24, |types| ~
10^3) the backward induction is ~10^5-10^6 elementary ops, so no sampling is needed; and averaging the value
over the *type posterior* (rather than solving determinized full-information games and averaging outcomes)
avoids strategy-fusion / non-locality bias — Frank & Basin, "Search in games with incomplete information,"
AIJ 100(1-2):87-123, 1998; ISMCTS: Cowling, Powley & Whitehouse, IEEE TCIAIG 4(2):120-143, 2012.

Protocol modeled (DESIGN §3): each round a (rotating) proposer offers a deal; all other seats accept/reject;
the deal closes iff *all* accept (unanimity); otherwise play continues to the next round with the discount
``delta``; after the deadline, no-deal pays surplus 0. Two regimes share one backward induction:

- **Full information** (``value_to_go_full_info``): all sheets known; opponents accept iff the offer beats
  their own discounted continuation, and each proposer offers its value-maximizing all-accepted deal. Exact;
  this is the path the unit tests pin.
- **Belief-averaged** (``value_to_go_beliefs``): opponents' acceptance is the posterior mass of accepting
  types (``accept_prob_fn``) and opponent proposals are modeled from the posterior; the agent's own
  acceptance uses its (known) surplus vs its continuation. A documented approximation for LLM-divergence use.

Complexity: building the per-deal all-accept masks is ``O(T * n * |D|)`` (vectorized); the belief path adds
the ``O(n * |types| * |D|)`` acceptance-probability tensor once. Sub-second at the target scale.
"""
from __future__ import annotations

import numpy as np

from ._oracle_common import (Accept, GameTables, Oracle, Propose, Reject, Walk, current_round,
                             effective_discount, game_tables, make_verdict, n_agents, offer_registry,
                             proposer_sequence, rounds_left, seat_index)

_NEG = -1e18


# --------------------------------------------------------------------------------------------------------- #
# Backward induction — full information (exact).
# --------------------------------------------------------------------------------------------------------- #
def value_to_go_full_info(tables: GameTables, proposer_seq, T: int, discount: float = 0.95) -> np.ndarray:
    """Joint continuation values ``V[t]`` (shape ``(T+2, n)``) for *every* seat under subgame-perfect
    alternating-offers play with unanimity acceptance and no-deal surplus 0.

    ``V[t, i]`` = seat ``i``'s expected surplus-to-go at the start of round ``t`` (t = 1..T; ``V[T+1] = 0``).
    At round ``t`` the proposer ``p = proposer_seq[(t-1) % len]`` offers the all-accepted deal maximizing its
    own surplus if that beats delaying, else delays; responders accept iff their surplus >= their discounted
    continuation."""
    S = tables.surplus                      # (D, n)
    n = tables.n_agents
    V = np.zeros((T + 2, n), dtype=float)
    for t in range(T, 0, -1):
        p = int(proposer_seq[(t - 1) % len(proposer_seq)])
        cont = discount * V[t + 1]          # (n,)
        others = [r for r in range(n) if r != p]
        if others:
            accept_mask = np.all(S[:, others] >= cont[others][None, :], axis=1)   # (D,)
        else:
            accept_mask = np.ones(S.shape[0], dtype=bool)
        prop_surplus = np.where(accept_mask, S[:, p], _NEG)
        if accept_mask.any():
            d_star = int(np.argmax(prop_surplus))
            if S[d_star, p] >= cont[p]:
                V[t] = S[d_star]            # proposal accepted this round
            else:
                V[t] = cont                 # proposer prefers to delay
        else:
            V[t] = cont
    return V


def _proposal_full_info(tables: GameTables, proposer: int, cont: np.ndarray) -> tuple:
    """The proposer's subgame-perfect offer given the discounted continuation vector ``cont``: returns
    ``(deal_index or None, all_accept_mask)``. None means 'delay is weakly better than any accepted deal'."""
    S = tables.surplus
    n = tables.n_agents
    others = [r for r in range(n) if r != proposer]
    accept_mask = (np.all(S[:, others] >= cont[others][None, :], axis=1) if others
                   else np.ones(S.shape[0], dtype=bool))
    if not accept_mask.any():
        return None, accept_mask
    prop_surplus = np.where(accept_mask, S[:, proposer], _NEG)
    d_star = int(np.argmax(prop_surplus))
    if S[d_star, proposer] < cont[proposer]:
        return None, accept_mask
    return d_star, accept_mask


# --------------------------------------------------------------------------------------------------------- #
# Backward induction — belief-averaged (agent-only continuation; opponents via posterior).
# --------------------------------------------------------------------------------------------------------- #
def value_to_go_beliefs(tables: GameTables, agent: int, proposer_seq, T: int, discount: float,
                        accept_prob, opp_proposal) -> np.ndarray:
    """Agent-``agent`` continuation ``Vi[t]`` (shape ``(T+2,)``) under the posterior.

    Parameters
    ----------
    accept_prob : np.ndarray
        ``(D, n)`` posterior probability each seat accepts each deal (self-column is treated deterministically
        below, so it is ignored for ``agent``).
    opp_proposal : dict[int, int]
        Stationary modeled proposal (deal index) per opponent seat.
    """
    S = tables.surplus[:, agent]            # (D,)
    n = tables.n_agents
    Vi = np.zeros(T + 2, dtype=float)
    for t in range(T, 0, -1):
        p = int(proposer_seq[(t - 1) % len(proposer_seq)])
        cont_i = discount * Vi[t + 1]
        if p == agent:
            others = [r for r in range(n) if r != agent]
            p_all = np.prod(accept_prob[:, others], axis=1) if others else np.ones(S.shape[0])
            ev = p_all * S + (1.0 - p_all) * cont_i
            Vi[t] = max(float(ev.max()), cont_i)
        else:
            d = opp_proposal.get(p)
            if d is None:
                Vi[t] = cont_i
                continue
            others = [r for r in range(n) if r not in (agent, p)]
            q = float(np.prod(accept_prob[d, others])) if others else 1.0
            accept_val = q * float(S[d]) + (1.0 - q) * cont_i    # realized iff others also accept
            Vi[t] = max(accept_val, cont_i)                       # agent accepts iff S[d] >= cont_i
    return Vi


# --------------------------------------------------------------------------------------------------------- #
# The oracle.
# --------------------------------------------------------------------------------------------------------- #
class BestResponseOracle(Oracle):
    """Per-turn expectimax best response for one seat.

    Parameters
    ----------
    agent : int
        The deciding seat.
    discount : float | None
        Per-round discount ``delta`` OVERRIDE; default ``None`` = read the game's own ``discount`` /
        ``breakdown_risk`` via ``effective_discount`` (single source of truth). Pass a float only to force it.
    accept_prob : np.ndarray | None
        Optional ``(D, n)`` posterior acceptance-probability table (belief regime). None => full information.
    opp_proposal : dict[int, int] | None
        Optional stationary modeled opponent proposals (belief regime). If None in the belief regime, each
        opponent is modeled as proposing its own posterior-expected-utility-maximizing deal (via
        ``accept_prob`` as a utility proxy is avoided; falls back to full-info proposal if sheets known).
    """

    name = "bestresponse"

    def __init__(self, agent: int, *, discount: float | None = None, accept_prob=None, opp_proposal=None):
        self.agent = int(agent)
        self.discount = None if discount is None else float(discount)
        self.accept_prob = accept_prob
        self.opp_proposal = opp_proposal

    # -- proposal values for the current round (agent as proposer) ----------------------------------------
    def propose_values(self, tables: GameTables, cont: np.ndarray) -> np.ndarray:
        """Expected value to ``agent`` of proposing each deal now, given the continuation vector ``cont``
        (full-info: ``cont`` is the length-n discounted continuation; belief: pass agent scalar via a length-n
        vector with opponents' acceptance folded into ``accept_prob``)."""
        S = tables.surplus
        n = tables.n_agents
        i = self.agent
        others = [r for r in range(n) if r != i]
        if self.accept_prob is None:
            accept_mask = (np.all(S[:, others] >= cont[others][None, :], axis=1) if others
                           else np.ones(S.shape[0], dtype=bool))
            return np.where(accept_mask, S[:, i], cont[i])
        p_all = np.prod(self.accept_prob[:, others], axis=1) if others else np.ones(S.shape[0])
        return p_all * S[:, i] + (1.0 - p_all) * cont[i]

    def evaluate(self, game, history, agent, legal):
        """Value each legal action; ``best`` is the surplus-maximizing one. ``extra`` carries the per-turn
        ``surplus_loss`` of every action (``V(best) - V(action)``) and the best-response proposal deal."""
        agent = seat_index(game, agent) if agent is not None else self.agent
        disc = effective_discount(game, self.discount)
        tables = game_tables(game)
        n = n_agents(game)
        T = int(getattr(game, "rounds", 0) or 1)
        seq = proposer_sequence(game)
        t = current_round(game, history)
        r_left = rounds_left(game, history)
        offers = offer_registry(game, history)

        if self.accept_prob is None:
            V = value_to_go_full_info(tables, seq, T, disc)
            cont_vec = disc * V[min(t + 1, T + 1)]
        else:
            opp_prop = self.opp_proposal or self._model_opp_proposals(tables, V_next=None)
            Vi = value_to_go_beliefs(tables, agent, seq, T, disc, self.accept_prob, opp_prop)
            cont_i = disc * Vi[min(t + 1, T + 1)]
            cont_vec = np.full(n, cont_i)      # only agent-column used downstream in belief mode

        prop_vals = self.propose_values(tables, cont_vec)
        best_deal = int(np.argmax(prop_vals))
        cont_i = float(cont_vec[agent])

        values: dict = {}
        for a in legal:
            if isinstance(a, Propose):
                idx = tables.index.get(tuple(int(x) for x in a.deal))
                values[a] = float(prop_vals[idx]) if idx is not None else _NEG
            elif isinstance(a, Accept) and a.offer_id in offers:
                values[a] = float(tables.surplus[tables.index[offers[a.offer_id]], agent])
            elif isinstance(a, Reject):
                values[a] = cont_i
            elif isinstance(a, Walk):
                values[a] = max(0.0, cont_i)
            else:
                values[a] = cont_i

        best = max(values, key=values.get) if values else None
        vbest = values[best] if best is not None else 0.0
        # JSON-safe list (not an Action-keyed dict, which would break OracleVerdict.to_json / episode save)
        surplus_loss = [{"action": a.to_json(), "loss": vbest - v} for a, v in values.items()]
        extra = {"surplus_loss": surplus_loss, "best_response_deal": list(tables.deals[best_deal]),
                 "best_response_value": float(prop_vals[best_deal]), "continuation": cont_i,
                 "rounds_left": r_left}
        return make_verdict(values, best=best, flags=[], extra=extra)

    def _model_opp_proposals(self, tables: GameTables, V_next) -> dict:
        """Fallback opponent-proposal model (belief regime, no explicit ``opp_proposal`` given): each opponent
        proposes the deal maximizing its own surplus among deals the *others* are most likely to accept."""
        out: dict = {}
        n = tables.n_agents
        for p in range(n):
            if p == self.agent:
                continue
            others = [r for r in range(n) if r != p]
            if self.accept_prob is not None and others:
                feas = np.prod(self.accept_prob[:, others], axis=1)
            else:
                feas = np.ones(tables.n_deals)
            score = np.where(feas > 0, tables.surplus[:, p], _NEG)
            out[p] = int(np.argmax(score))
        return out


# --------------------------------------------------------------------------------------------------------- #
# Exploitability of a revealed strategy vs fixed counterparts (Johanson et al. 2011).
# --------------------------------------------------------------------------------------------------------- #
def exploitability(tables: GameTables, agent: int, revealed_value: float, proposer_seq, T: int,
                   discount: float = 0.95) -> float:
    """``BR_value - revealed_value``: how much surplus the agent leaves on the table vs its exact best
    response, holding the (full-information) counterpart continuation fixed. ``revealed_value`` is the
    agent's realized/expected surplus under its own policy (computed by the caller, e.g. via a rollout).
    Non-negative up to estimation noise; larger = more exploitable."""
    V = value_to_go_full_info(tables, proposer_seq, T, discount)
    br = float(V[1, agent])
    return br - float(revealed_value)

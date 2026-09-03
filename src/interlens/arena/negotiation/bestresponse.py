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
# [rational_agents scaffold: lens-wave] 2026-07-26 — deterministic verdict/extra ordering (canonical action sort)
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

Protocol modeled: each round a (rotating) proposer offers a deal; all other seats accept/reject;
the deal closes iff the game's fixed acceptance quorum (and every veto seat) accepts; otherwise play
continues to the next round with the discount
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

from ..actions import FACILITATOR, FACILITATOR_SEAT, action_key
from .oracle_context import (Accept, GameTables, Oracle, Propose, Reject, Walk, current_round,
                             effective_discount, game_tables, make_verdict, n_agents, offer_registry,
                             proposer_sequence, rounds_left, seat_index)

_NEG = -1e18


def _quorum(n: int, min_accept: int | None) -> int:
    """Normalize ``None`` (legacy unanimity) and validate a fixed-seat acceptance quorum."""
    need = n if min_accept is None else int(min_accept)
    if not 1 <= need <= n:
        raise ValueError(f"min_accept must be in 1..{n} or None, got {min_accept!r}")
    return need


def passage_probability(accept_prob: np.ndarray, proposer: int | None, *, min_accept: int | None = None,
                        veto_seats=()) -> np.ndarray:
    """Probability each deal passes under independent responder votes.

    ``accept_prob`` has shape ``(D, n)``.  The proposer implicitly supports its own offer, ``min_accept`` is
    a fixed count out of the original ``n`` seats, and every veto seat must support.  ``None`` preserves the
    historical unanimity rule.  A small Poisson-binomial DP computes ``P(# yes >= quorum)`` exactly, rather
    than multiplying every opponent probability (which silently turns every quorum into unanimity).

    ``proposer=None`` means the offer has NO implicit supporter — a package tabled by the protocol's neutral
    facilitator (:data:`~interlens.arena.actions.FACILITATOR`), which holds no sheet and casts no vote. Every
    seat then votes on its own merits: the quorum must be met out of the responders alone, and each veto seat's
    probability enters the product rather than being satisfied for free by proposing.
    """
    ap = np.asarray(accept_prob, dtype=float)
    if ap.ndim != 2:
        raise ValueError(f"accept_prob must have shape (deals, seats), got {ap.shape}")
    D, n = ap.shape
    p = None if proposer is None else int(proposer)
    if p is not None and not 0 <= p < n:
        raise ValueError(f"proposer {p} out of range for {n} seats")
    need = _quorum(n, min_accept)
    veto = {int(v) for v in veto_seats}
    if any(v < 0 or v >= n for v in veto):
        raise ValueError(f"veto seat out of range for {n} seats: {sorted(veto)}")

    required = sorted(veto - ({p} if p is not None else set()))
    base = np.prod(ap[:, required], axis=1) if required else np.ones(D, dtype=float)
    yes_required = (1 if p is not None else 0) + len(required)  # proposer + required veto responders
    remaining = [i for i in range(n) if i != p and i not in veto]
    extra = max(need - yes_required, 0)
    if extra <= 0:
        return base
    if extra > len(remaining):
        return np.zeros(D, dtype=float)

    # dist[:, j] = probability of exactly j yes votes among the optional responders processed so far.
    dist = np.zeros((D, len(remaining) + 1), dtype=float)
    dist[:, 0] = 1.0
    seen = 0
    for seat in remaining:
        q = np.clip(ap[:, seat], 0.0, 1.0)
        nxt = np.zeros_like(dist)
        nxt[:, :seen + 1] += dist[:, :seen + 1] * (1.0 - q[:, None])
        nxt[:, 1:seen + 2] += dist[:, :seen + 1] * q[:, None]
        dist = nxt
        seen += 1
    return base * dist[:, extra:seen + 1].sum(axis=1)


def _full_info_pass_mask(S: np.ndarray, proposer: int, cont: np.ndarray, *,
                         min_accept: int | None = None, veto_seats=()) -> np.ndarray:
    """Deals that pass deterministic continuation-value votes under the fixed quorum/veto rule."""
    n = S.shape[1]
    ap = (S >= np.asarray(cont, dtype=float)[None, :]).astype(float)
    ap[:, int(proposer)] = 1.0  # proposing is an implicit yes; own continuation is checked separately.
    return passage_probability(ap, int(proposer), min_accept=min_accept,
                               veto_seats=veto_seats) >= 1.0 - 1e-12


def conditional_vote_values(accept_prob: np.ndarray, proposer: int | None, agent: int, deal_index: int,
                            deal_surplus: float, continuation: float, *, min_accept: int | None = None,
                            veto_seats=(), forced_yes=(), forced_no=()) -> tuple[float, float, float, float]:
    """Value this seat's yes/no vote after conditioning on votes already cast.

    Returns ``(yes_value, no_value, p_pass_if_yes, p_pass_if_no)``. This is load-bearing for quorum games:
    a yes vote may be insufficient to pass, while a no vote may be non-pivotal. Existing supporters/rejecters
    and walkers are forced through ``forced_yes``/``forced_no``; all uncast votes retain their deterministic
    full-information or posterior probability. Agreement pays ``deal_surplus`` and failure pays
    ``continuation``.

    ``proposer=None`` values a vote on a facilitator-tabled offer, which no seat implicitly supports (see
    :func:`passage_probability`).

    One offer is the ``K = 1`` case of :func:`conditional_vote_values_batch`, which is where the arithmetic
    actually lives — a turn with many live offers should call that instead of this in a loop.
    """
    yes_v, no_v, q_yes, q_no = conditional_vote_values_batch(
        accept_prob, [proposer], agent, [deal_index], [deal_surplus], continuation,
        min_accept=min_accept, veto_seats=veto_seats, forced_yes=[forced_yes], forced_no=[forced_no])
    return float(yes_v[0]), float(no_v[0]), float(q_yes[0]), float(q_no[0])


def conditional_vote_values_batch(accept_prob: np.ndarray, proposers, agent: int, deal_indices,
                                  deal_surpluses, continuation: float, *, min_accept: int | None = None,
                                  veto_seats=(), forced_yes=None, forced_no=None) -> tuple:
    """:func:`conditional_vote_values` for ``K`` offers at once; returns four ``(K,)`` arrays.

    Same semantics per offer — each gets its own proposer, deal, already-cast ``forced_yes`` / ``forced_no``
    votes, and surplus — but the Poisson-binomial solves are BATCHED. The DP in
    :func:`passage_probability` is elementwise across its deal axis, so stacking K independent single-offer
    rows into one call returns each row's own answer, bitwise identical to solving it alone. Offers are
    grouped by proposer (the one argument the DP takes per call rather than per row), so a turn costs at most
    two solves per distinct proposer instead of two per offer — the difference between O(live offers) and
    O(seats) numpy calls on a turn, and the reason a long-horizon episode, whose live-offer list grows every
    round, stops being quadratic.

    Parameters
    ----------
    accept_prob : np.ndarray
        ``(D, n)`` acceptance probabilities (full-information 0/1 or posterior).
    proposers : sequence[int | None]
        Per-offer proposing seat, or ``None`` for a facilitator-tabled offer with no implicit supporter.
    agent : int
        The seat whose yes/no vote is being valued (the same seat for every offer).
    deal_indices, deal_surpluses : sequence
        Per-offer row into ``accept_prob`` and the payoff agreement pays ``agent``.
    continuation : float
        What failing to pass is worth to ``agent`` — shared by every offer, since it is a property of the turn.
    forced_yes, forced_no : sequence[sequence[int]] | None
        Per-offer already-cast votes; ``None`` means none for any offer.
    """
    ap = np.asarray(accept_prob, dtype=float)
    idx = [int(d) for d in deal_indices]
    K = len(idx)
    forced_yes = list(forced_yes or [()] * K)
    forced_no = list(forced_no or [()] * K)
    if not (len(proposers) == len(deal_surpluses) == len(forced_yes) == len(forced_no) == K):
        raise ValueError("proposers, deal_indices, deal_surpluses and forced votes must be the same length")
    rows = np.array(ap[idx], copy=True) if K else np.zeros((0, ap.shape[1]))
    for k in range(K):
        for seat in forced_yes[k]:
            rows[k, int(seat)] = 1.0
        for seat in forced_no[k]:
            rows[k, int(seat)] = 0.0
    yes, no = np.array(rows, copy=True), np.array(rows, copy=True)
    yes[:, int(agent)], no[:, int(agent)] = 1.0, 0.0
    q_yes, q_no = np.zeros(K), np.zeros(K)
    groups: dict = {}
    for k, p in enumerate(proposers):
        groups.setdefault(None if p is None else int(p), []).append(k)
    for p, ks in groups.items():
        q_yes[ks] = passage_probability(yes[ks], p, min_accept=min_accept, veto_seats=veto_seats)
        q_no[ks] = passage_probability(no[ks], p, min_accept=min_accept, veto_seats=veto_seats)
    s = np.asarray(deal_surpluses, dtype=float)
    c = float(continuation)
    return q_yes * s + (1.0 - q_yes) * c, q_no * s + (1.0 - q_no) * c, q_yes, q_no


def _offer_vote_records(game, history) -> dict[str, dict]:
    """Best-effort rich live-offer records for current-vote valuation; empty metadata remains compatible."""
    raw = getattr(history, "offers", None)
    if raw is None and isinstance(history, dict):
        raw = history.get("offers")
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = [((o.get("offer_id") if isinstance(o, dict) else getattr(o, "offer_id", None)), o)
                 for o in raw]
    else:
        items = []

    names = (history.get("seat_names", ()) if isinstance(history, dict)
             else getattr(history, "seat_names", ())) or ()

    def resolve(value):
        if value is None:
            return None
        if value in names:
            return list(names).index(value)
        try:
            return seat_index(game, value)
        except (KeyError, ValueError, TypeError):
            return None

    out: dict[str, dict] = {}
    for oid, offer in items:
        if oid is None:
            continue
        get = offer.get if isinstance(offer, dict) else lambda key, default=None: getattr(offer, key, default)
        raw_proposer = get("proposer")
        proposer = resolve(raw_proposer)
        accepts = {s for value in (get("accepts", ()) or ()) if (s := resolve(value)) is not None}
        rejects = {s for value in (get("rejects", ()) or ()) if (s := resolve(value)) is not None}
        # A facilitator-tabled offer resolves to no seat, and that is a FACT about it rather than missing
        # metadata: flagging it keeps the caller from falling back to "some seat must have proposed this" and
        # crediting a vote nobody cast.
        out[str(oid)] = {"proposer": proposer, "accepts": accepts, "rejects": rejects,
                         "facilitator": raw_proposer in (FACILITATOR, FACILITATOR_SEAT)}
    return out


# --------------------------------------------------------------------------------------------------------- #
# Backward induction — full information (exact).
# --------------------------------------------------------------------------------------------------------- #
def value_to_go_full_info(tables: GameTables, proposer_seq, T: int, discount: float = 0.95, *,
                          min_accept: int | None = None, veto_seats=()) -> np.ndarray:
    """Joint continuation values ``V[t]`` (shape ``(T+2, n)``) for *every* seat under subgame-perfect
    alternating-offers play with the fixed ``min_accept`` quorum, required ``veto_seats``, and no-deal
    surplus 0. ``min_accept=None`` preserves unanimity.

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
        accept_mask = _full_info_pass_mask(S, p, cont, min_accept=min_accept, veto_seats=veto_seats)
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


def value_to_go_full_info_cached(tables: GameTables, proposer_seq, T: int, discount: float = 0.95, *,
                                 min_accept: int | None = None, veto_seats=()) -> np.ndarray:
    """:func:`value_to_go_full_info` memoized on the game tables — the whole ``V`` curve, computed ONCE.

    The joint value curve depends only on ``(tables, proposer_seq, T, discount, min_accept, veto_seats)``,
    every one of which is fixed for an episode; a turn varies only which ROW of ``V`` it reads. Recomputing
    the full backward induction on every turn therefore costs ``O(T)`` Poisson-binomial solves per turn and
    ``O(T^2)`` per episode, which is what made a long-horizon omniscient seat expensive the moment it started
    planning the real deadline. The cache lives on the ``GameTables`` instance (one per game, already cached
    on the game itself), so it is per-game rather than global and needs no eviction policy; the stored array
    is marked read-only so a caller cannot mutate a shared curve. Falls back to a plain recompute if the
    tables object refuses the attribute.
    """
    key = (tuple(int(p) for p in proposer_seq), int(T), float(discount),
           None if min_accept is None else int(min_accept), tuple(sorted(int(v) for v in veto_seats)))
    cache = getattr(tables, "_value_to_go_cache", None)
    if cache is None:
        cache = {}
        try:
            tables._value_to_go_cache = cache
        except Exception:      # a tables object that cannot carry the cache still gets correct values
            return value_to_go_full_info(tables, proposer_seq, T, discount, min_accept=min_accept,
                                         veto_seats=veto_seats)
    hit = cache.get(key)
    if hit is None:
        hit = value_to_go_full_info(tables, proposer_seq, T, discount, min_accept=min_accept,
                                    veto_seats=veto_seats)
        hit.flags.writeable = False
        cache[key] = hit
    return hit


def _proposal_full_info(tables: GameTables, proposer: int, cont: np.ndarray, *,
                        min_accept: int | None = None, veto_seats=()) -> tuple:
    """The proposer's subgame-perfect offer given the discounted continuation vector ``cont``: returns
    ``(deal_index or None, all_accept_mask)``. None means 'delay is weakly better than any accepted deal'."""
    S = tables.surplus
    accept_mask = _full_info_pass_mask(S, proposer, cont, min_accept=min_accept, veto_seats=veto_seats)
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
                        accept_prob, opp_proposal, *, min_accept: int | None = None, veto_seats=(),
                        objective=None) -> np.ndarray:
    """Agent-``agent`` continuation ``Vi[t]`` (shape ``(T+2,)``) under the posterior.

    Parameters
    ----------
    accept_prob : np.ndarray
        ``(D, n)`` posterior probability each seat accepts each deal (self-column is treated deterministically
        below, so it is ignored for ``agent``).
    opp_proposal : dict[int, int]
        Stationary modeled proposal (deal index) per opponent seat.
    objective : np.ndarray | None
        Optional ``(|D|,)`` payoff column replacing ``agent``'s own surplus, so the same rollout produces the
        continuation value of a **fairness-seeking** seat (``fairness.mnw_objective``) rather than a
        self-interested one. Only this seat's payoff changes; the modeled opponents keep behaving as
        self-interested acceptors/proposers. ``None`` (default) is the exact prior behaviour.
    """
    S = tables.surplus[:, agent] if objective is None else np.asarray(objective, dtype=float)   # (D,)
    n = tables.n_agents
    Vi = np.zeros(T + 2, dtype=float)
    # The passage probabilities do NOT depend on the round: this seat's own p_pass is a function of
    # ``accept_prob`` alone, and an opponent's conditional yes/no pair is a function of ``(p, opp_proposal[p])``
    # alone — only the continuation value ``cont_i`` moves with ``t``. Memoizing them here makes the recursion's
    # cost O(1) Poisson-binomial solves per DISTINCT proposer instead of one per round, which is what stops a
    # deep horizon costing O(T) solves per turn (and, over an episode's O(T) turns, O(T^2) per episode). The
    # cached values are the same float64 the loop computed before, in the same order, so every ``Vi[t]`` is
    # bitwise unchanged; they are computed lazily, so a round the loop never reaches still costs nothing.
    memo: dict = {}

    def own_pass() -> np.ndarray:
        if "own" not in memo:
            memo["own"] = passage_probability(accept_prob, agent, min_accept=min_accept,
                                              veto_seats=veto_seats)
        return memo["own"]

    def opp_votes(p: int, d: int) -> tuple:
        key = (p, d)
        if key not in memo:
            # Under a non-unanimous rule, rejecting need not block passage. Value both votes by forcing the
            # deciding seat's probability to 1/0 while leaving all other posterior votes unchanged.
            yes = np.array(accept_prob[d:d + 1], copy=True)
            no = np.array(yes, copy=True)
            yes[0, agent], no[0, agent] = 1.0, 0.0
            memo[key] = (float(passage_probability(yes, p, min_accept=min_accept, veto_seats=veto_seats)[0]),
                         float(passage_probability(no, p, min_accept=min_accept, veto_seats=veto_seats)[0]))
        return memo[key]

    for t in range(T, 0, -1):
        p = int(proposer_seq[(t - 1) % len(proposer_seq)])
        cont_i = discount * Vi[t + 1]
        if p == agent:
            p_pass = own_pass()
            ev = p_pass * S + (1.0 - p_pass) * cont_i
            Vi[t] = max(float(ev.max()), cont_i)
        else:
            d = opp_proposal.get(p)
            if d is None:
                Vi[t] = cont_i
                continue
            q_yes, q_no = opp_votes(p, int(d))
            accept_val = q_yes * float(S[d]) + (1.0 - q_yes) * cont_i
            reject_val = q_no * float(S[d]) + (1.0 - q_no) * cont_i
            Vi[t] = max(accept_val, reject_val)
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

    def __init__(self, agent: int, *, discount: float | None = None, accept_prob=None, opp_proposal=None,
                 min_accept: int | None = None, veto_seats=()):
        self.agent = int(agent)
        self.discount = None if discount is None else float(discount)
        self.accept_prob = accept_prob
        self.opp_proposal = opp_proposal
        self.min_accept = min_accept
        self.veto_seats = tuple(int(v) for v in veto_seats)

    # -- proposal values for the current round (agent as proposer) ----------------------------------------
    def propose_values(self, tables: GameTables, cont: np.ndarray, agent: int | None = None, *,
                       min_accept: int | None = None, veto_seats=None, objective=None) -> np.ndarray:
        """Expected value to ``agent`` of proposing each deal now, given the continuation vector ``cont``
        (full-info: ``cont`` is the length-n discounted continuation; belief: pass agent scalar via a length-n
        vector with opponents' acceptance folded into ``accept_prob``).

        ``agent`` is the PROPOSING seat; ``None`` falls back to the constructor's ``self.agent``. Pass it
        explicitly whenever one oracle instance serves several seats — which is what a scenario's shared oracle
        stack does (``BestResponseOracle(0)`` reused for every seat), and what :meth:`evaluate` now does with the
        seat it resolved. Getting this wrong is silent: the acceptance mask and the surplus column both come from
        this seat, so a stale seat prices every proposal from the wrong sheet while accept/reject/walk values
        (computed from the resolved seat) stay correct.

        ``objective`` is an optional ``(|D|,)`` payoff column replacing ``agent``'s own surplus as *what the
        proposal is worth if it passes* — the substitution that makes this best-response machinery serve a
        fairness-seeking proposer (``fairness.mnw_objective``). Only the payoff changes: which deals can pass
        is still governed by the other seats' own-surplus acceptance, since the opponents remain
        self-interested however this seat scores the outcome. ``None`` (default) is the exact prior behaviour.
        """
        S = tables.surplus
        n = tables.n_agents
        i = self.agent if agent is None else int(agent)
        need = self.min_accept if min_accept is None else min_accept
        veto = self.veto_seats if veto_seats is None else tuple(veto_seats)
        payoff = S[:, i] if objective is None else np.asarray(objective, dtype=float)
        if self.accept_prob is None:
            accept_mask = _full_info_pass_mask(S, i, cont, min_accept=need, veto_seats=veto)
            return np.where(accept_mask, payoff, cont[i])
        p_pass = passage_probability(self.accept_prob, i, min_accept=need, veto_seats=veto)
        return p_pass * payoff + (1.0 - p_pass) * cont[i]

    def evaluate(self, game, history, agent, legal):
        """Value each legal action; ``best`` is the surplus-maximizing one. ``extra`` carries the per-turn
        ``surplus_loss`` of every action (``V(best) - V(action)``) and the best-response proposal deal.

        Ties in the argmax are resolved by :meth:`_argmax_action`, which prefers any action over accepting an
        offer that pays this seat strictly negative surplus, and only then falls back to the canonical
        ``action_key`` order. A strict optimum is never overridden."""
        agent = seat_index(game, agent) if agent is not None else self.agent
        disc = effective_discount(game, self.discount)
        tables = game_tables(game)
        n = n_agents(game)
        T = int(getattr(game, "rounds", 0) or 1)
        seq = proposer_sequence(game)
        min_accept = getattr(game, "min_accept", self.min_accept)
        veto_seats = tuple(getattr(game, "veto_seats", self.veto_seats) or ())
        t = current_round(game, history)
        r_left = rounds_left(game, history)
        offers = offer_registry(game, history)
        offer_votes = _offer_vote_records(game, history)

        if self.accept_prob is None:
            V = value_to_go_full_info_cached(tables, seq, T, disc, min_accept=min_accept,
                                             veto_seats=veto_seats)
            cont_vec = disc * V[min(t + 1, T + 1)]
        else:
            opp_prop = self.opp_proposal or self._model_opp_proposals(
                tables, V_next=None, agent=agent, min_accept=min_accept, veto_seats=veto_seats)
            Vi = value_to_go_beliefs(tables, agent, seq, T, disc, self.accept_prob, opp_prop,
                                     min_accept=min_accept, veto_seats=veto_seats)
            cont_i = disc * Vi[min(t + 1, T + 1)]
            cont_vec = np.full(n, cont_i)      # only agent-column used downstream in belief mode

        prop_vals = self.propose_values(tables, cont_vec, agent, min_accept=min_accept,
                                        veto_seats=veto_seats)
        best_deal = int(np.argmax(prop_vals))
        cont_i = float(cont_vec[agent])
        vote_ap = ((tables.surplus >= cont_vec[None, :]).astype(float)
                   if self.accept_prob is None else np.asarray(self.accept_prob, dtype=float))
        walked_raw = (history.get("walked", ()) if isinstance(history, dict)
                      else getattr(history, "walked", ())) or ()
        seat_names = (history.get("seat_names", ()) if isinstance(history, dict)
                      else getattr(history, "seat_names", ())) or ()
        walked: set[int] = set()
        for value in walked_raw:
            if value in seat_names:
                walked.add(list(seat_names).index(value))
            else:
                try:
                    walked.add(seat_index(game, value))
                except (KeyError, ValueError, TypeError):
                    pass

        # Vote valuation is done in ONE batched pass rather than per action. A turn's legal set carries an
        # Accept and a Reject for every live offer, and the live-offer list grows every round, so the old
        # per-action call made this oracle O(live offers) Poisson-binomial solves per turn — quadratic over a
        # long-horizon episode. Collected here in ``legal`` order and solved together below; the per-action
        # values are then read back, so ``vote_diagnostics`` keeps the order it always had.
        votes = [a for a in legal if isinstance(a, (Accept, Reject)) and a.offer_id in offers]
        vote_ids, seen_ids = [], set()
        for a in votes:
            if a.offer_id not in seen_ids:
                seen_ids.add(a.offer_id)
                vote_ids.append(a.offer_id)
        vote_rows, vote_proposers, vote_surplus, vote_yes, vote_no = [], [], [], [], []
        for oid in vote_ids:
            idx = tables.index[offers[oid]]
            record = offer_votes.get(oid, {})
            proposer = record.get("proposer")
            if proposer is None and not record.get("facilitator"):
                supporters = sorted(record.get("accepts", ()))
                proposer = supporters[0] if supporters else int(seq[(max(t, 1) - 1) % len(seq)])
            vote_rows.append(idx)
            vote_proposers.append(proposer)
            vote_surplus.append(tables.surplus[idx, agent])
            vote_yes.append(record.get("accepts", ()))
            vote_no.append(set(record.get("rejects", ())) | walked)
        yes_vals, no_vals, q_yeses, q_nos = conditional_vote_values_batch(
            vote_ap, vote_proposers, agent, vote_rows, vote_surplus, cont_i,
            min_accept=min_accept, veto_seats=veto_seats, forced_yes=vote_yes, forced_no=vote_no)
        solved = {oid: (float(yes_vals[k]), float(no_vals[k]), float(q_yeses[k]), float(q_nos[k]),
                        vote_proposers[k])
                  for k, oid in enumerate(vote_ids)}
        #: This seat's OWN surplus from each votable offer, kept for the negative-surplus accept tie-break
        #: below (``_argmax_action``). It is the raw sheet payoff of signing, not a continuation value.
        own_surplus_of_offer = {oid: float(vote_surplus[k]) for k, oid in enumerate(vote_ids)}

        values: dict = {}
        vote_diagnostics: list[dict] = []
        for a in legal:
            if isinstance(a, Propose):
                idx = tables.index.get(tuple(int(x) for x in a.deal))
                values[a] = float(prop_vals[idx]) if idx is not None else _NEG
            elif isinstance(a, (Accept, Reject)) and a.offer_id in offers:
                yes_v, no_v, q_yes, q_no, proposer = solved[a.offer_id]
                values[a] = yes_v if isinstance(a, Accept) else no_v
                vote_diagnostics.append({"offer_id": a.offer_id, "p_pass_if_accept": q_yes,
                                         "p_pass_if_reject": q_no, "accept_value": yes_v,
                                         "reject_value": no_v, "proposer": proposer})
            elif isinstance(a, Reject):
                values[a] = cont_i
            elif isinstance(a, Walk):
                # WALK is irreversible and pays this seat its no-deal surplus (zero), even when a remaining
                # coalition can still pass a deal. It is not another spelling of Reject/continue.
                values[a] = 0.0
            else:
                values[a] = cont_i

        # When proposing is a legal move at this decision point, the agent could have tabled ANY deal, so score
        # the oracle's OWN best-response proposal too. Otherwise ``best``/divergence range only over the actions
        # in the passed ``legal`` set — which for a proposal turn is often just the single chosen ``Propose`` (the
        # scenario deliberately does not enumerate the whole |D| proposal space into the record) — so a proposal
        # turn trivially reads ~0 regret even when the chosen offer is far from best-response (the single-shot
        # mis-scoring). The full proposal space is enumerated here (``prop_vals``), so the best-response deal is a
        # sound extra candidate. Vote-only turns (no ``Propose`` legal) are untouched — the agent cannot propose.
        if any(isinstance(a, Propose) for a in legal):
            br_action = Propose(tuple(int(x) for x in tables.deals[best_deal]))
            values.setdefault(br_action, float(prop_vals[best_deal]))

        # Deterministic TIE-BREAK: several actions routinely share the argmax value, and `max` would otherwise
        # return whichever the caller happened to list first. Ordering the candidates canonically makes `best`
        # a function of the legal SET, not of its order. (Distinct from where the legal set's own order comes
        # from — that is fixed at its source, `OfferRegistry.standing_ids`; this rule owns only the tie-break,
        # which no registry can decide, and which is why `evaluate` is order-invariant for any caller.)
        values = {a: values[a] for a in sorted(values, key=action_key)}

        best = self._argmax_action(values, own_surplus_of_offer)
        vbest = values[best] if best is not None else 0.0
        # JSON-safe list (not an Action-keyed dict, which would break OracleVerdict.to_json / episode save)
        surplus_loss = [{"action": a.to_json(), "loss": vbest - v} for a, v in values.items()]
        extra = {"surplus_loss": surplus_loss, "best_response_deal": list(tables.deals[best_deal]),
                 "best_response_value": float(prop_vals[best_deal]), "continuation": cont_i,
                 "rounds_left": r_left, "conditional_votes": vote_diagnostics,
                 "walk_value": 0.0}
        return make_verdict(values, best=best, flags=[], extra=extra)

    @staticmethod
    def _argmax_action(values: dict, own_surplus_of_offer: dict):
        """Pick the best action, breaking ties AGAINST accepting a strictly negative-surplus offer.

        The rule, in order:

        1. Take the actions attaining the maximum value. If exactly one action is strictly best, it is
           returned unchanged — this guard never overrides a strict optimum, so any game where some action
           has strictly positive value (every feasibility-screened bank, by construction) decides exactly as
           it did before.
        2. Among the tied actions, drop every ``Accept`` whose own surplus is strictly negative, unless that
           would empty the set.
        3. Break the remaining tie with the canonical ``action_key`` order (``values`` arrives pre-sorted, so
           this is simply the first survivor).

        WHY: on a game with an empty individually-rational set, the conditional vote solve returns
        ``p_pass_if_accept = 0.0``, the accept branch collapses to the zero continuation, and reject, propose
        and walk are 0.0 as well — every legal action ties at exactly 0.0. The canonical tie-break sorts
        ``accept`` first alphabetically, so an omniscient seat signed a deal paying it strictly negative
        surplus *because it was certain the deal could not pass* — a self-refuting belief that every seat held
        at once, so the deal passed unanimously (errata E1; audit
        ``experiments/rational_agents/audit_oracle_empty_ir_accept.py``, 150/150 seat-states all-tied,
        130 accepting negative own surplus). The sibling ``bayes-rational`` policy already carries this
        own-surplus guard; the oracle lacked it. A ceiling policy that signs a deal it is indifferent to and
        strictly loses on is not a ceiling, so indifference is resolved toward not signing.
        """
        if not values:
            return None
        vbest = max(values.values())
        tied = [a for a in values if values[a] == vbest]
        if len(tied) == 1:
            return tied[0]
        kept = [a for a in tied
                if not (isinstance(a, Accept) and own_surplus_of_offer.get(a.offer_id, 0.0) < 0.0)]
        return (kept or tied)[0]

    def _model_opp_proposals(self, tables: GameTables, V_next, agent: int | None = None, *,
                             min_accept: int | None = None, veto_seats=None) -> dict:
        """Fallback opponent-proposal model (belief regime, no explicit ``opp_proposal`` given): each opponent
        proposes the deal maximizing its own surplus among deals the *others* are most likely to accept.
        ``agent`` (the deciding seat, whose own proposal is not modeled) defaults to ``self.agent``."""
        out: dict = {}
        n = tables.n_agents
        me = self.agent if agent is None else int(agent)
        need = self.min_accept if min_accept is None else min_accept
        veto = self.veto_seats if veto_seats is None else tuple(veto_seats)
        for p in range(n):
            if p == me:
                continue
            if self.accept_prob is not None:
                feas = passage_probability(self.accept_prob, p, min_accept=need, veto_seats=veto)
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

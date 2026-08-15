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

"""The computable bidder zoo: policies (``state -> action``), their DM decision rules, and their oracles.

The sibling of ``negotiation/strategies.py``, and deliberately the same shape — a :class:`AuctionPolicy` ABC
whose ``__call__`` takes a structured :class:`AuctionState` (the machine-readable counterpart of the text
view an LLM seat reads) and returns a typed action from :mod:`.actions` — so a policy seat and an LLM seat
are interchangeable at the table.

Two terminology commitments carried straight from the program (design.md §4.1):

- **"rational"** = an information-conditional Bayes response from ITS OWN information only, and
  **stage-myopic by construction**: it best-responds within each stage and computes no repeated-game
  equilibrium. It will not initiate, join, or sustain a ring, and it defects from one whenever within-stage
  arithmetic says to. That is not an omission — it is the instrument Q5 needs, a seat whose non-participation
  in collusion is a property of its decision rule rather than of its affordances. A trigger-strategy
  repeated-game policy is the named follow-on and is deliberately not built here.
- **"oracle"** = the SAME best response computed with everyone's realized private information. Under IPV
  second-price the two coincide exactly — bidding your own value is dominant, so omniscience buys nothing —
  which is the preregistered G3 implementation check and is asserted in the tests.

Policies are constructed with ``information="private"`` or ``"oracle"`` rather than being duplicated into
parallel class hierarchies, since the two differ only in what the state hands them.

Beyond ``act``, every policy exposes the templated-channel behavior design.md §3.4 requires, because a
computable seat that cannot speak loses via the microphone rather than the decision rule:
:meth:`AuctionPolicy.declaration` (a public opening statement of its position that leaks no private state),
:meth:`AuctionPolicy.evaluate_proposal` (a policy-derived accept/decline on a DM'd division or price, with
its arithmetic exposed as reason slots), and :meth:`AuctionPolicy.initiate_proposal`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from ..actions import Action, Pass
from .actions import Bid, Claim, Demand, Exit, PassLot, SAATurn, Schedule, Stay, Wait
from .allocation import ValueModel
from .benchmarks import (best_bundle_at_prices, expected_value_given_winning, rnne_bid_against, rnne_shade)
from .priors import RivalPosterior

#: Public prior support of the unobserved common resale value ``R`` (the generator draws it uniformly on the
#: catalogue base range). Announced, so the winner's-curse correction is computable from public information.
RESALE_PRIOR_GRID = np.arange(40, 121, dtype=float)


def public_posteriors(spec, t: int) -> list[RivalPosterior]:
    """One :class:`~.priors.RivalPosterior` per seat, built from PUBLIC information only — the belief any
    seat (or the harness computing a benchmark) can form about each other seat at stage ``t``.

    Reads only the public constants (``beta``, the sigmas), the stage's public catalogue ``B_jt``, the public
    loadings ``w_j``, and each seat's public attribute vector ``a_i``. It never touches a realized draw,
    which is what makes it usable by a rational seat without violating the information rule."""
    st = spec.stage(t)
    loadings = spec.loadings
    resale_mean = np.full(spec.n_items, float(RESALE_PRIOR_GRID.mean()))
    return [RivalPosterior(base_values=np.array(st.base_values, dtype=float), loadings=loadings,
                           attrs_row=np.array(b.attrs, dtype=float), beta=spec.beta, sigma_z=spec.sigma_z,
                           sigma_eps=spec.sigma_eps, gamma=b.gamma, resale_mean=resale_mean)
            for b in spec.bidders]


# --------------------------------------------------------------------------------------------------------- #
# The structured state a policy reads.
# --------------------------------------------------------------------------------------------------------- #
@dataclass
class AuctionState:
    """Everything a :class:`AuctionPolicy` needs to compute its next move — the machine-readable counterpart
    of the text view an LLM seat reads, so the two kinds of seat are interchangeable.

    Attributes
    ----------
    seat : int
        This policy's seat index.
    spec : AuctionSpec
        The episode spec (public structure; the private stage draws are surfaced through the fields below,
        never read off the spec by a private-information policy).
    stage, round : int
        1-indexed stage within the episode and round within the stage.
    values : np.ndarray
        ``(n_items,)`` this seat's OWN known valuation component. Under IPV/APV that is the realized value;
        under INTERDEP it is the private part only, with the common component reachable solely through
        ``signals`` — which is exactly the information split that makes a winner's curse possible.
    budget : int
        This seat's remaining whole-number budget for the stage.
    synergy_target : tuple[int, ...] | None
        This seat's private target set, or ``None``.
    signals : np.ndarray | None
        ``(n_items,)`` private noisy resale signals (INTERDEP only).
    posteriors : list[RivalPosterior]
        Public-information posteriors over every seat, index-aligned with seats (this seat's own entry is
        present but unused). Built by :func:`public_posteriors`.
    standing : list[int] | None
        Per-lot standing high price, or ``None`` where no bid stands.
    standing_winner : list[int | None] | None
        Per-lot standing high bidder.
    clock_price : int | None
        Current clock price for the clock families.
    active : tuple[int, ...]
        Seats still active on the clock.
    exits : dict[int, int]
        Observed public exits this stage: seat -> the clock price it exited at. A conditional-Bayes seat
        folds these into its posteriors, which is the whole content of "updates on observed public events
        within a stage".
    oracle_values : np.ndarray | None
        ``(n_bidders, n_items)`` everyone's realized valuations. Present only for an ``information="oracle"``
        seat; a private-information policy must never read it, which the policies below enforce by taking it
        only through :meth:`AuctionPolicy._rival_values`.
    reserve, increment : int
        Mechanism parameters, carried so a policy never re-defaults them.
    """

    seat: int
    spec: object
    stage: int
    values: np.ndarray
    budget: int
    posteriors: list = field(default_factory=list)
    round: int = 1
    synergy_target: tuple[int, ...] | None = None
    signals: np.ndarray | None = None
    standing: list | None = None
    standing_winner: list | None = None
    clock_price: int | None = None
    active: tuple[int, ...] = ()
    exits: dict = field(default_factory=dict)
    oracle_values: np.ndarray | None = None
    reserve: int = 0
    increment: int = 1

    @staticmethod
    def from_spec(spec, t: int, seat: int, *, information: str = "private", round: int = 1,
                  **kw) -> "AuctionState":
        """Build the stage-``t`` state for ``seat`` straight from a spec — the constructor the tests, the
        per-turn counterfactual annotator, and a solo harness all use. ``information="oracle"`` additionally
        attaches every seat's realized values."""
        st = spec.stage(t)
        vals = np.array(st.values[seat], dtype=np.int64)
        if spec.value_structure == "interdep" and st.resale is not None:
            vals = vals - np.round(spec.gammas[seat] * np.array(st.resale, dtype=float)).astype(np.int64)
        return AuctionState(
            seat=seat, spec=spec, stage=t, round=round, values=vals, budget=int(st.budgets[seat]),
            synergy_target=st.synergy_target[seat],
            signals=np.array(st.signals[seat]) if st.signals is not None else None,
            posteriors=public_posteriors(spec, t),
            active=tuple(range(spec.n_bidders)),
            oracle_values=st.value_array if information == "oracle" else None,
            reserve=spec.mechanism.reserve, increment=spec.mechanism.increment, **kw)

    @property
    def n_items(self) -> int:
        """Number of lots this stage."""
        return int(self.values.shape[0])

    @property
    def rivals(self) -> tuple[int, ...]:
        """Seat indices of the other bidders."""
        return tuple(i for i in range(self.spec.n_bidders) if i != self.seat)

    def value_model(self) -> ValueModel:
        """A one-seat :class:`~.allocation.ValueModel` over this seat's own values — what the bundle and
        capacity arithmetic in the multi-item formats runs against."""
        return ValueModel(values=self.values.reshape(1, -1),
                          capacities=(self.spec.capacities[self.seat],),
                          decays=(self.spec.decays[self.seat],),
                          synergy_rates=(self.spec.synergy_rates[self.seat],),
                          synergy_targets=(self.synergy_target,), budgets=(self.budget,))


# --------------------------------------------------------------------------------------------------------- #
# Decisions on DM'd proposals.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Proposal:
    """A division or price proposal arriving over the DM channel, in the machine-readable form a policy seat
    can actually evaluate.

    ``assignment`` maps seat index -> the lots that seat is asked to take (a market division); ``price`` is
    the level the proposal asks bidders to hold to on ``item``. A proposal may carry either or both."""

    proposer: int
    assignment: dict | None = None
    item: int | None = None
    price: int | None = None
    text: str = ""


@dataclass(frozen=True)
class Decision:
    """A policy's verdict on a proposal, with the arithmetic that produced it exposed as reason slots.

    ``reason`` is one of a small closed vocabulary (``"matches_best_response"``,
    ``"dominated_by_best_response"``, ``"exceeds_capacity"``, ``"below_reservation"``,
    ``"unenforceable"``), and ``detail`` carries the numbers behind it, so the templated DM reply states WHY
    in the seat's own terms and an analysis can read the decision without parsing prose."""

    accept: bool
    reason: str
    detail: dict = field(default_factory=dict)

    def sentence(self) -> str:
        """The one-line natural-language form the templated DM reply publishes. Numbers only — never a
        private valuation, which would leak through the microphone the design deliberately hands policy
        seats."""
        verb = "Agreed" if self.accept else "Declining"
        gain = self.detail.get("proposal_surplus")
        alt = self.detail.get("best_response_surplus")
        if gain is None or alt is None:
            return f"{verb}: {self.reason.replace('_', ' ')}."
        return (f"{verb}: that line is worth {gain:.0f} to me against {alt:.0f} from simply bidding my own "
                f"numbers ({self.reason.replace('_', ' ')}).")


# --------------------------------------------------------------------------------------------------------- #
# The policy ABC.
# --------------------------------------------------------------------------------------------------------- #
class AuctionPolicy(ABC):
    """A deterministic auction policy: ``policy(state) -> action``.

    Subclasses set :attr:`name` and implement :meth:`bid_for`; :meth:`act` turns that number into whichever
    typed move the stage's format calls for, so a policy is written once and plays every family. ``__call__``
    is the invocation surface a participant wrapper binds to.

    Parameters
    ----------
    information : str
        ``"private"`` (the rational seat: own information only) or ``"oracle"`` (the same best response with
        everyone's realized private information). This is the ONLY difference between a rational and an
        oracle seat, which is why they are one class.
    """

    name: str = "auction_policy"

    def __init__(self, information: str = "private"):
        if information not in ("private", "oracle"):
            raise ValueError(f"information must be 'private' or 'oracle', got {information!r}")
        self.information = information

    def __call__(self, state: AuctionState) -> Action:
        return self.act(state)

    @property
    def is_oracle(self) -> bool:
        """Whether this seat sees everyone's realized private information."""
        return self.information == "oracle"

    @abstractmethod
    def bid_for(self, state: AuctionState, item: int) -> int:
        """The whole-number price this policy is willing to pay for ``item`` at the current state — the one
        number every format's move is derived from."""

    # -- moves ---------------------------------------------------------------------------------------------
    def act(self, state: AuctionState) -> Action:
        """The typed move for this stage's format, derived from :meth:`bid_for` and the seat's capacity."""
        mech = state.spec.mechanism
        # Every decision goes through ``_afford``: a payment must be collectible, so a policy never bids, stays
        # in, or claims above its budget. Its ``None`` — the seat cannot afford even the reserve — is the case
        # where no legal move buys anything, so the policy takes no part in the lot rather than emitting a
        # number the mechanism would reject.
        if mech.family == "sealed_single":
            ceiling = self._afford(state, self.bid_for(state, 0))
            return Pass() if ceiling is None else Bid(item=0, amount=ceiling)
        if mech.family == "english":
            ceiling = self._afford(state, self.bid_for(state, 0))
            return Stay() if ceiling is not None and (state.clock_price or 0) <= ceiling else Exit()
        if mech.family == "dutch":
            ceiling = self._afford(state, self.bid_for(state, 0))
            return Claim() if ceiling is not None and (state.clock_price or 0) <= ceiling else Wait()
        if mech.family == "saa":
            return self._saa_move(state)
        if mech.family == "uniform_price":
            return Schedule(tuple(self.schedule(state)))
        if mech.family == "clinching":
            price = state.clock_price or 0
            return Demand(units=int(sum(1 for m in self.schedule(state) if m >= price)))
        raise ValueError(f"no policy move defined for family {mech.family!r}")

    def _saa_move(self, state: AuctionState) -> Action:
        """Straightforward bidding [milgrom2000]: the seat's WHOLE round demand as one :class:`SAATurn` —
        ``standing + increment`` on every lot in its surplus-maximizing bundle at prices-to-pay that it does
        not already hold.

        This is the same rule, and the same call, that
        :func:`~interlens.arena.auction.benchmarks.saa_competitive_benchmark` simulates, which is what makes
        ``bid_benchmark_ratio`` a gate rather than a comparison of two different rules. It has to be one call
        because straightforward bidding's demand correspondence is defined over BUNDLES: the argmax bundle is
        not in general reachable by taking its best lot, re-solving, and taking the next, once synergies make
        a lot's marginal value depend on which others the seat wins. Deriving the turn that way — one
        ``act()`` per lot against a locally-advanced standing table — is what this method replaces, and it put
        the two computable arms off the benchmark on every multi-item bank with live synergies (14 of 16
        stages on the frozen 10-lot bank, ``bid_benchmark_ratio`` spread 0.923-1.141) while reading exactly
        1.000 at 3 lots, where the greedy path and the bundle argmax coincide.

        Two further alignments with the benchmark ride along. ``forced=held`` is now passed, so the lots the
        seat is already standing high on are in its bundle rather than re-contested from scratch — the
        omission the benchmark's own docstring warns about, which let a capacity-``k`` seat demand ``k`` fresh
        lots while holding ``k`` others. And the budget DROPS lots rather than truncating amounts: an SAA bid
        must be at least ``standing + increment``, so a truncated amount is a ``below_minimum`` legality error
        rather than a cheaper bid, which is why :meth:`_afford` is deliberately not used here. Lots are
        dropped in ascending surplus order, so the seat keeps the most valuable part of its demand.

        No new tie-breaking is introduced: :func:`best_bundle_at_prices` already resolves an exact tie toward
        the smaller bundle and then the lexicographically first, so the bundle is a deterministic function of
        the state and the stage's seeded permutation continues to decide only the mechanism's own contests.
        """
        prices = np.array([(state.standing[j] if state.standing and state.standing[j] is not None
                            else state.reserve) for j in range(state.n_items)], dtype=float)
        held = tuple(j for j in range(state.n_items)
                     if state.standing_winner and state.standing_winner[j] == state.seat)
        pay = np.array([prices[j] if j in held else prices[j] + state.increment
                        for j in range(state.n_items)])
        vm = state.value_model()
        bundle, surplus = best_bundle_at_prices(vm, 0, pay, forced=held)
        want = [j for j in bundle if j not in held]
        if not want or surplus <= 0:
            # An EMPTY turn, not a pass on some arbitrary lot. Under the SAA activity rule a ``PassLot`` is
            # irrevocable for the whole stage, so passing on ``free[0]`` — a lot chosen by index, not by any
            # decision — permanently forfeited a lot the seat had merely not demanded THIS round, and did so
            # every round it stood pat. It is a real forfeiture because a lot's marginal value can rise later
            # in the stage once the seat wins its complements. The mechanism accepts an empty ``SAATurn`` (it
            # is the parser's own fallback move), so declining to bid costs the seat nothing, which is what
            # straightforward bidding actually prescribes and what the benchmark simulates.
            return SAATurn()
        # ``state.budget`` is already NET of this seat's live standing commitments (the scenario's
        # ``_remaining_budget`` subtracts them for the SAA family), and every lot in ``want`` is one the seat
        # does not hold, so each bid is a fresh commitment and the constraint is simply their sum.
        headroom = int(state.budget)
        bids: list[Bid] = []
        for j in sorted(want, key=lambda k: -(self.bid_for(state, k) - pay[k])):
            amount = int(pay[j])
            if amount > headroom:
                continue
            bids.append(Bid(item=j, amount=amount))
            headroom -= amount
        if not bids:
            return SAATurn()                  # budget-priced-out this round, not a forfeit of the lot
        return SAATurn(bids=tuple(sorted(bids, key=lambda b: b.item)))

    def schedule(self, state: AuctionState) -> list[int]:
        """The per-unit bid schedule for the multi-unit families. The default is the seat's true decayed
        marginal values (truthful demand), which is an equilibrium of the clinching rule [ausubel2004];
        :class:`DemandSchedulePolicy` overrides it for the uniform-price rule where it is not."""
        base = float(state.values[0])
        d = float(state.spec.decays[state.seat])
        k = min(int(state.spec.capacities[state.seat]), int(state.spec.mechanism.n_units))
        return [int(round(base * d ** r)) for r in range(k)]

    def _afford(self, state: AuctionState, amount: int) -> int | None:
        """Truncate a bid to the seat's remaining budget: a payment must be collectible, so a policy never
        emits a bid it cannot pay (which would be a legality error rather than a decision).

        ``None`` when the seat cannot even afford the RESERVE, where no legal bid exists at all and the only
        correct move is to take no part in the lot. Clamping up to the reserve there was a real defect: on the
        frozen single-lot bank (reserve 20) the Che-Gale budget-bound seat draws budgets below it, so every
        single-item cell emitted one unpayable bid per affected stage, which the mechanism rejected as a
        legality error and replaced with a fallback pass. The move was then a parse-hygiene artifact rather
        than the policy's decision, and it held `parse_ok_rate` at exactly G1's 0.95 threshold in the free
        arms — an arm whose correctness G3 asserts exactly."""
        if int(state.budget) < int(state.reserve):
            return None
        return int(max(state.reserve, min(int(amount), int(state.budget))))

    def _rival_values(self, state: AuctionState, item: int) -> np.ndarray | None:
        """Rivals' realized values for ``item`` — available ONLY to an oracle seat. Returning ``None`` for a
        private-information seat is what enforces the information rule structurally: a policy that wants
        rival values has to go through here, and here is where the arm is checked."""
        if not self.is_oracle or state.oracle_values is None:
            return None
        return np.array([state.oracle_values[i, item] for i in state.rivals], dtype=float)

    # -- the templated channel behavior (design.md §3.4) --------------------------------------------------
    def declaration(self, state: AuctionState) -> str | None:
        """A public opening statement of this seat's position, once per stage, leaking no private state — the
        auction analogue of ``negotiation.strategies.Policy.declaration``. The default states the seat's
        decision RULE (which is public information: the rules announce that a computable seat plays its
        information-conditional best response) and nothing about its draws."""
        return (f"I bid my own arithmetic every stage: I will go to the number my information supports on the "
                f"lots I can use, and no further. I hold capacity for "
                f"{state.spec.capacities[state.seat]} lot(s) this stage.")

    def evaluate_proposal(self, state: AuctionState, proposal: Proposal) -> Decision:
        """Evaluate a DM'd division or price proposal against this seat's own within-stage best response.

        The rule is exactly the stage-myopia preregistration made computable: the seat accepts a proposal iff
        doing what it asks is weakly better FOR THIS STAGE than its own best response, treating the proposal
        as unenforceable (there is no commitment device under the ``dm`` rung — only ``dm_transfers`` adds
        one). A proposal asking the seat to hold below its best-response price therefore declines with the
        two surpluses attached, which is what makes Q5's "does a rational seat destabilize a ring" a
        decision-rule result rather than an artifact of silence."""
        item = proposal.item if proposal.item is not None else int(np.argmax(state.values))
        br = self.bid_for(state, item)
        own = float(state.values[item])
        if proposal.assignment is not None:
            mine = tuple(proposal.assignment.get(state.seat, ()))
            if len(mine) > state.spec.capacities[state.seat]:
                return Decision(False, "exceeds_capacity",
                                {"asked": len(mine), "capacity": state.spec.capacities[state.seat]})
            vm = state.value_model()
            # A division hands you the lot at the reserve; competing costs you the competitive price, which
            # this seat prices as the expected highest rival value per lot.
            division_prices = np.full(state.n_items, float(state.reserve))
            competitive = np.array([float(np.dot(*self._max_rival_pmf(state, j)[::-1]))
                                    for j in range(state.n_items)])
            proposal_surplus = (vm.bundle_value(0, mine) - float(division_prices[list(mine)].sum())
                                if mine else 0.0)
            best, br_surplus = best_bundle_at_prices(vm, 0, competitive)
            accept = proposal_surplus >= br_surplus - 1e-9
            return Decision(accept, "matches_best_response" if accept else "dominated_by_best_response",
                            {"proposal_surplus": proposal_surplus, "best_response_surplus": br_surplus,
                             "proposed_bundle": list(mine), "best_response_bundle": list(best)})
        if proposal.price is None:
            return Decision(False, "unenforceable", {"note": "no price or division named"})
        if proposal.price > own:
            return Decision(False, "below_reservation", {"asked_price": int(proposal.price),
                                                         "own_value": own})
        # Holding to a price below the best response wins the lot only when no rival outbids it; a
        # stage-myopic seat prices both lines with :meth:`expected_surplus_at` and takes the larger.
        proposal_surplus = self.expected_surplus_at(state, item, int(proposal.price))
        br_surplus = self.expected_surplus_at(state, item, int(br))
        accept = proposal_surplus >= br_surplus - 1e-9
        return Decision(accept, "matches_best_response" if accept else "dominated_by_best_response",
                        {"proposal_surplus": proposal_surplus, "best_response_surplus": br_surplus,
                         "asked_price": int(proposal.price), "best_response_bid": int(br)})

    def initiate_proposal(self, state: AuctionState) -> Proposal | None:
        """The proposal this seat opens with, addressed at the rival its posterior identifies as the
        strongest threat — or ``None`` when competing dominates.

        A stage-myopic seat only ever proposes the division it would play ANYWAY (its best-response bundle at
        competitive prices), so its proposals are honest and it never asks a rival for a suppression it would
        not itself honor. That is the design's point: this seat's non-participation in a ring is structural."""
        vm = state.value_model()
        prices = np.full(state.n_items, float(state.reserve + state.increment))
        bundle, surplus = best_bundle_at_prices(vm, 0, prices)
        if not bundle or surplus <= 0:
            return None
        contested = int(bundle[0])
        threat = max(state.rivals, key=lambda i: state.posteriors[i].expected_value(contested))
        rest = [j for j in range(state.n_items) if j not in bundle]
        return Proposal(proposer=state.seat, assignment={state.seat: tuple(bundle), threat: tuple(rest)},
                        item=contested,
                        text=f"I intend to take {', '.join(f'Lot {j + 1}' for j in bundle)} this stage.")

    def respond_to_dm(self, state: AuctionState, proposal: Proposal) -> tuple[Decision, str]:
        """The templated DM reply: the policy-derived :class:`Decision` and the sentence that publishes it."""
        d = self.evaluate_proposal(state, proposal)
        return d, d.sentence()

    # -- shared belief helpers ----------------------------------------------------------------------------
    def _oracle_first_price_bid(self, state: AuctionState, item: int, realized: np.ndarray) -> int:
        """The omniscient first-price/Dutch bid: claim at the second-highest value plus one whole unit when
        this seat holds the highest value, and sit at the reserve when it does not (design.md §4.1).

        Bidding up to a losing value would be pure noise — the oracle knows it cannot win profitably — so the
        two branches together are what gives the oracle a real edge in Dutch and none at all in second-price."""
        own = float(state.values[item])
        top = float(realized.max()) if len(realized) else 0.0
        if own <= top:
            return int(state.reserve)
        return int(min(own, max(state.reserve, top + 1)))

    def _max_rival_pmf(self, state: AuctionState, item: int) -> tuple[np.ndarray, np.ndarray]:
        """The distribution of the HIGHEST rival value for ``item``, as ``(values, probs)``.

        Built by differencing the product of the rivals' conditioned CDFs, so every public event already
        folded into a posterior flows through. An oracle seat gets a point mass at the realized maximum."""
        realized = self._rival_values(state, item)
        if realized is not None:
            return np.array([float(realized.max()) if len(realized) else 0.0]), np.array([1.0])
        support = np.unique(np.concatenate(
            [state.posteriors[i].value_pmf(item)[0] for i in state.rivals]))
        cdf = np.ones_like(support, dtype=float)
        for i in state.rivals:
            post = self._conditioned(state, i, item)
            cdf *= np.array([post.cdf(item, float(x)) for x in support])
        return support, np.diff(np.concatenate([[0.0], cdf]))

    def expected_surplus_at(self, state: AuctionState, item: int, bid: int) -> float:
        """This seat's expected stage surplus from bidding ``bid`` on ``item``, under the stage's pricing
        rule — the quantity :meth:`evaluate_proposal` compares a proposal against.

        Under first-price it is ``P(win) * (v - bid)``. Under second-price/English it is
        ``E[(v - X) * 1(X < bid)]`` with ``X`` the highest rival value, which is why holding to any price
        below one's own value is weakly dominated there: lowering ``bid`` only removes states of the world in
        which the seat would have won at a price below ``v``."""
        own = float(state.values[item])
        if state.spec.mechanism.pricing == "first_price":
            return self._win_probability(state, item, int(bid)) * (own - float(bid))
        support, probs = self._max_rival_pmf(state, item)
        gain = np.where((support < float(bid)) & (support < own), own - support, 0.0)
        return float(np.dot(gain, probs))

    def _win_probability(self, state: AuctionState, item: int, bid: int) -> float:
        """``P(this bid is the highest)``. An oracle reads the rivals' realized values directly and returns 0
        or 1; a private-information seat reads its public posteriors, conditioned on whatever the stage has
        already revealed (exits and standing bids)."""
        realized = self._rival_values(state, item)
        if realized is not None:
            return float(all(bid > v for v in realized))
        p = 1.0
        for i in state.rivals:
            post = self._conditioned(state, i, item)
            p *= post.cdf(item, bid - 1)
        return float(p)

    def _conditioned(self, state: AuctionState, rival: int, item: int) -> RivalPosterior:
        """``rival``'s posterior after folding in the public events of this stage: an observed exit at price
        ``p`` pins its value near ``p``; a rival still active at the clock price has value at least that;
        a rival holding the standing high bid has value at least that bid."""
        post = state.posteriors[rival]
        if rival in state.exits:
            p = float(state.exits[rival])
            return post.condition(item, lower=p - state.increment, upper=p + state.increment)
        if state.clock_price is not None and rival in state.active:
            return post.condition(item, lower=float(state.clock_price))
        if state.standing_winner and state.standing and state.standing_winner[item] == rival:
            return post.condition(item, lower=float(state.standing[item]))
        return post


# --------------------------------------------------------------------------------------------------------- #
# The policies.
# --------------------------------------------------------------------------------------------------------- #
class TruthfulPolicy(AuctionPolicy):
    """Bid your own value — weakly dominant in second-price and English private-value stages
    [vickrey1961, pp. 20-23], and the demand-reduction-free schedule in the multi-unit families.

    Its oracle variant is the SAME function of the state: omniscience buys nothing in a dominant-strategy
    mechanism, which is design.md's G3 check and is asserted directly in the tests."""

    name = "truthful"

    def bid_for(self, state: AuctionState, item: int) -> int:
        return int(state.values[item])


class RNNEPolicy(AuctionPolicy):
    """The risk-neutral first-price / Dutch equilibrium bidder.

    Under IPV it plays the closed-form ``(n-1)/n * v`` [riley_samuelson1981, pp. 383-385]; otherwise it
    solves the equilibrium numerically against the rivals' public value distributions via
    :func:`~.benchmarks.rnne_bid_against`, caching the rival marginals per ``(stage, item)`` because they are
    a property of the stage's public catalogue, not of the turn.

    Its ORACLE variant is different from its rational one, and this is the sharp case where information has
    value: knowing every rival's realized value, the omniscient first-price bidder claims at the
    second-highest value plus one whole unit — the least it can pay and still win (design.md §4.1)."""

    name = "rnne"

    def __init__(self, information: str = "private"):
        super().__init__(information)
        self._cache: dict[tuple[int, int], object] = {}

    def bid_for(self, state: AuctionState, item: int) -> int:
        realized = self._rival_values(state, item)
        if realized is not None:
            return self._oracle_first_price_bid(state, item, realized)
        if state.spec.value_structure == "ipv":
            return int(round(rnne_shade(state.spec.n_bidders) * float(state.values[item])))
        key = (state.stage, item)
        if key not in self._cache:
            self._cache[key] = [state.posteriors[i].value_pmf(item) for i in state.rivals]
        return int(round(rnne_bid_against(float(state.values[item]), self._cache[key],
                                          lower=float(state.reserve))))


class ConditionalBayesPolicy(AuctionPolicy):
    """The headline rational seat: a **stage-myopic information-conditional Bayes response**.

    What "conditional" means here, format by format:

    - **second-price / English under IPV or APV** — values are private, so bidding one's own value stays
      weakly dominant and no belief enters. The policy returns the own value, and the fact that this
      coincides with :class:`TruthfulPolicy` is a property of the mechanism, not a shortcut.
    - **second-price / English under INTERDEP** — the value depends on a common component about which
      rivals hold information, so the bid is ``E[v | own signal, own signal is the highest]``
      (:func:`~.benchmarks.expected_value_given_winning`), which is strictly below the naive
      signal-as-value bid. This is the winner's-curse conditioning, and the tests assert the shading engages.
    - **Dutch / first-price** — the myopic best response on the integer bid grid against the rivals'
      CONDITIONED posteriors, i.e. ``argmax_b (v - b) * P(all rivals below b)``. That is a best response,
      not the fixed point :class:`RNNEPolicy` solves; the distinction is deliberate and is what makes this
      seat's behavior a decision rule rather than an equilibrium assumption.
    - **SAA / multi-unit** — capacity- and synergy-aware straightforward bidding inherited from the ABC.

    Within a stage it updates on the public events the format reveals — exits, standing bids, and remaining
    activity — through :meth:`AuctionPolicy._conditioned`. Across stages it updates on NOTHING: its stage-``t``
    move is independent of stages ``1..t-1`` given stage-``t`` values, which is the property G3's repeated-tier
    extension tests directly."""

    name = "conditional_bayes"

    def bid_for(self, state: AuctionState, item: int) -> int:
        own = float(state.values[item])
        if state.spec.value_structure == "interdep" and state.signals is not None:
            own = expected_value_given_winning(
                int(state.signals[item]), private_part=own, gamma=float(state.spec.gammas[state.seat]),
                sigma_nu=float(state.spec.sigma_nu), n_rivals=state.spec.n_bidders - 1,
                resale_grid=RESALE_PRIOR_GRID)
        if state.spec.mechanism.pricing != "first_price":
            return int(round(own))
        realized = self._rival_values(state, item)
        if realized is not None:
            top = float(realized.max()) if len(realized) else 0.0
            return int(min(round(own), max(state.reserve, top + 1)))
        grid = np.arange(state.reserve, int(round(own)) + 1, dtype=float)
        if len(grid) == 0:
            return int(state.reserve)
        payoff = np.array([(own - b) * self._win_probability(state, item, int(b)) for b in grid])
        return int(grid[int(np.argmax(payoff))])


class DemandSchedulePolicy(AuctionPolicy):
    """The multi-unit bidder: truthful demand under the clinching rule, shaded demand under uniform pricing.

    Under clinching, truthful demand is an equilibrium [ausubel2004, pp. 1454-1460], so the schedule is the
    seat's true decayed marginal values. Under UNIFORM pricing it is not — an inframarginal unit's bid sets
    the price the seat pays on the units it wins — so the policy searches a one-parameter family of shaded
    schedules ``(m_1, s*m_2, ..., s*m_k)`` over ``s`` on a grid and keeps the one with the highest expected
    surplus against the rivals' posteriors. The restriction to one shading parameter is a deliberate,
    documented approximation of the equilibrium schedule of [ausubel_cramton2014, pp. 1370-1378]: it captures
    the direction and the gradient (later units shaded more) without claiming to be the exact fixed point,
    and the DEMAND-REDUCTION-FREE schedule — not this one — is what the metric divides against."""

    name = "demand_schedule"

    #: Shading factors searched for the uniform-price schedule. 1.0 is included so the policy can decline to
    #: shade at all when the arithmetic says so.
    SHADE_GRID: tuple[float, ...] = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0)

    def bid_for(self, state: AuctionState, item: int) -> int:
        return int(self.schedule(state)[0]) if self.schedule(state) else int(state.reserve)

    def schedule(self, state: AuctionState) -> list[int]:
        truthful = super().schedule(state)
        if state.spec.mechanism.family != "uniform_price" or len(truthful) <= 1:
            return truthful
        n_units = int(state.spec.mechanism.n_units)
        best, best_ev = truthful, -np.inf
        for s in self.SHADE_GRID:
            cand = [truthful[0]] + [int(round(s * m)) for m in truthful[1:]]
            ev = 0.0
            for r, bid in enumerate(cand):
                # A unit is won when fewer than (n_units - r) rival unit-values sit above this bid; the
                # posterior gives the per-rival probability, and the price paid is approximated by the bid
                # itself (the highest rejected bid is at most it), which is the conservative direction.
                p = float(np.prod([self._conditioned(state, i, 0).cdf(0, bid) for i in state.rivals]))
                ev += p * (truthful[r] - bid)
            if ev > best_ev:
                best, best_ev = cand, ev
        return best


#: Factory registry, the sibling of ``arena.table.POLICY_FACTORIES``. Each entry takes ``information`` and
#: returns a policy, so the scenario lane wires a seat with one lookup and never branches on the arm.
AUCTION_POLICIES: dict[str, type] = {
    TruthfulPolicy.name: TruthfulPolicy,
    RNNEPolicy.name: RNNEPolicy,
    ConditionalBayesPolicy.name: ConditionalBayesPolicy,
    DemandSchedulePolicy.name: DemandSchedulePolicy,
}


def policy_for(spec, *, information: str = "private") -> AuctionPolicy:
    """The right computable bidder for a spec's mechanism and value structure.

    ``sealed_single``/``english`` -> :class:`ConditionalBayesPolicy` (which reduces to bidding own value
    under private values, so the rational and oracle seats coincide there exactly — G3);
    ``dutch`` -> :class:`ConditionalBayesPolicy` as the stage-myopic best responder;
    ``uniform_price``/``clinching`` -> :class:`DemandSchedulePolicy`; ``saa`` -> :class:`ConditionalBayesPolicy`
    driving the ABC's capacity- and synergy-aware straightforward bidding.

    This is the single dispatch point, so an arm never has to know which class it got."""
    family = spec.mechanism.family
    if family in ("uniform_price", "clinching"):
        return DemandSchedulePolicy(information)
    return ConditionalBayesPolicy(information)

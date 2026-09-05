# `interlens.arena.auction.bidders`

The computable bidder zoo: policies (`state -> action`), their DM decision rules, and their oracles.

The sibling of `negotiation/strategies.py`, and deliberately the same shape — a :class:`AuctionPolicy` ABC
whose `__call__` takes a structured :class:`AuctionState` (the machine-readable counterpart of the text
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

Policies are constructed with `information="private"` or `"oracle"` rather than being duplicated into
parallel class hierarchies, since the two differ only in what the state hands them.

Beyond `act`, every policy exposes the templated-channel behavior design.md §3.4 requires, because a
computable seat that cannot speak loses via the microphone rather than the decision rule:
:meth:`AuctionPolicy.declaration` (a public opening statement of its position that leaks no private state),
:meth:`AuctionPolicy.evaluate_proposal` (a policy-derived accept/decline on a DM'd division or price, with
its arithmetic exposed as reason slots), and :meth:`AuctionPolicy.initiate_proposal`.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `AUCTION_POLICIES` | `dict[str, type]` |  |
| `RESALE_PRIOR_GRID` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AuctionPolicy`](AuctionPolicy.md) | A deterministic auction policy: `policy(state) -> action`. |
| [`AuctionState`](AuctionState.md) | Everything a :class:`AuctionPolicy` needs to compute its next move — the machine-readable counterpart of the text view an LLM seat reads, so the two kinds of seat are interchangeable. |
| [`ConditionalBayesPolicy`](ConditionalBayesPolicy.md) | The headline rational seat: a **stage-myopic information-conditional Bayes response**. |
| [`Decision`](Decision.md) | A policy's verdict on a proposal, with the arithmetic that produced it exposed as reason slots. |
| [`DemandSchedulePolicy`](DemandSchedulePolicy.md) | The multi-unit bidder: truthful demand under the clinching rule, shaded demand under uniform pricing. |
| [`Proposal`](Proposal.md) | A division or price proposal arriving over the DM channel, in the machine-readable form a policy seat can actually evaluate. |
| [`RNNEPolicy`](RNNEPolicy.md) | The risk-neutral first-price / Dutch equilibrium bidder. |
| [`TruthfulPolicy`](TruthfulPolicy.md) | Bid your own value — weakly dominant in second-price and English private-value stages [vickrey1961, pp. 20-23], and the demand-reduction-free schedule in the multi-unit families. |

## Functions

| Name | Summary |
|---|---|
| [`policy_for`](policy_for.md) | The right computable bidder for a spec's mechanism and value structure. |
| [`public_posteriors`](public_posteriors.md) | One :class:`~.priors.RivalPosterior` per seat, built from PUBLIC information only — the belief any seat (or the harness computing a benchmark) can form about each other seat at stage `t`. |

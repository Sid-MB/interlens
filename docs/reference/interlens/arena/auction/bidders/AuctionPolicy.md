# `AuctionPolicy`

A deterministic auction policy: `policy(state) -> action`.

```python
AuctionPolicy(information: str = 'private')
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L234-L535)

**Inherits from:** `ABC`

Subclasses set :attr:`name` and implement :meth:`bid_for`; :meth:`act` turns that number into whichever
typed move the stage's format calls for, so a policy is written once and plays every family. `__call__`
is the invocation surface a participant wrapper binds to.

Parameters
----------
information : str
    `"private"` (the rational seat: own information only) or `"oracle"` (the same best response with
    everyone's realized private information). This is the ONLY difference between a rational and an
    oracle seat, which is why they are one class.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `information` | `str` | `'private'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `information` |  |  |
| `is_oracle` | `bool` | Whether this seat sees everyone's realized private information. |
| `name` | `str` |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: AuctionState) -> Action
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L270-L293)

The typed move for this stage's format, derived from :meth:`bid_for` and the seat's capacity.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |

## `bid_for` {#bid_for}

```python
bid_for(self, state: AuctionState, item: int) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L264-L267)

The whole-number price this policy is willing to pay for `item` at the current state — the one number every format's move is derived from.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |

## `declaration` {#declaration}

```python
declaration(self, state: AuctionState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L389-L396)

A public opening statement of this seat's position, once per stage, leaking no private state — the auction analogue of `negotiation.strategies.Policy.declaration`.

The default states the seat's
decision RULE (which is public information: the rules announce that a computable seat plays its
information-conditional best response) and nothing about its draws.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |

## `evaluate_proposal` {#evaluate_proposal}

```python
evaluate_proposal(self, state: AuctionState, proposal: Proposal) -> Decision
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L398-L440)

Evaluate a DM'd division or price proposal against this seat's own within-stage best response.

The rule is exactly the stage-myopia preregistration made computable: the seat accepts a proposal iff
doing what it asks is weakly better FOR THIS STAGE than its own best response, treating the proposal
as unenforceable (there is no commitment device under the `dm` rung — only `dm_transfers` adds
one). A proposal asking the seat to hold below its best-response price therefore declines with the
two surpluses attached, which is what makes Q5's "does a rational seat destabilize a ring" a
decision-rule result rather than an artifact of silence.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `proposal` | [Proposal](Proposal.md) | *required* |  |

## `expected_surplus_at` {#expected_surplus_at}

```python
expected_surplus_at(self, state: AuctionState, item: int, bid: int) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L495-L508)

This seat's expected stage surplus from bidding `bid` on `item`, under the stage's pricing rule — the quantity :meth:`evaluate_proposal` compares a proposal against.

Under first-price it is `P(win) * (v - bid)`. Under second-price/English it is
`E[(v - X) * 1(X < bid)]` with `X` the highest rival value, which is why holding to any price
below one's own value is weakly dominated there: lowering `bid` only removes states of the world in
which the seat would have won at a price below `v`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |
| `bid` | `int` | *required* |  |

## `initiate_proposal` {#initiate_proposal}

```python
initiate_proposal(self, state: AuctionState) -> Proposal | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L442-L459)

The proposal this seat opens with, addressed at the rival its posterior identifies as the strongest threat — or `None` when competing dominates.

A stage-myopic seat only ever proposes the division it would play ANYWAY (its best-response bundle at
competitive prices), so its proposals are honest and it never asks a rival for a suppression it would
not itself honor. That is the design's point: this seat's non-participation in a ring is structural.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |

## `respond_to_dm` {#respond_to_dm}

```python
respond_to_dm(self, state: AuctionState, proposal: Proposal) -> tuple[Decision, str]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L461-L464)

The templated DM reply: the policy-derived :class:`Decision` and the sentence that publishes it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `proposal` | [Proposal](Proposal.md) | *required* |  |

## `schedule` {#schedule}

```python
schedule(self, state: AuctionState) -> list[int]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L356-L363)

The per-unit bid schedule for the multi-unit families.

The default is the seat's true decayed
marginal values (truthful demand), which is an equilibrium of the clinching rule [ausubel2004];
:class:`DemandSchedulePolicy` overrides it for the uniform-price rule where it is not.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |

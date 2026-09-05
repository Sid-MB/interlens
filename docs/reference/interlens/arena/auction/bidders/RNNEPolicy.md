# `RNNEPolicy`

The risk-neutral first-price / Dutch equilibrium bidder.

```python
RNNEPolicy(information: str = 'private')
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L554-L582)

**Inherits from:** [AuctionPolicy](AuctionPolicy.md)

Under IPV it plays the closed-form `(n-1)/n * v` [riley_samuelson1981, pp. 383-385]; otherwise it
solves the equilibrium numerically against the rivals' public value distributions via
:func:`~.benchmarks.rnne_bid_against`, caching the rival marginals per `(stage, item)` because they are
a property of the stage's public catalogue, not of the turn.

Its ORACLE variant is different from its rational one, and this is the sharp case where information has
value: knowing every rival's realized value, the omniscient first-price bidder claims at the
second-highest value plus one whole unit — the least it can pay and still win (design.md §4.1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `information` | `str` | `'private'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `bid_for` {#bid_for}

```python
bid_for(self, state: AuctionState, item: int) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L572-L582)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |

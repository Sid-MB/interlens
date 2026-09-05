# `TruthfulPolicy`

Bid your own value — weakly dominant in second-price and English private-value stages [vickrey1961, pp. 20-23], and the demand-reduction-free schedule in the multi-unit families.

```python
TruthfulPolicy()
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L541-L551)

**Inherits from:** [AuctionPolicy](AuctionPolicy.md)

Its oracle variant is the SAME function of the state: omniscience buys nothing in a dominant-strategy
mechanism, which is design.md's G3 check and is asserted directly in the tests.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

## Methods {#methods}

## `bid_for` {#bid_for}

```python
bid_for(self, state: AuctionState, item: int) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L550-L551)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |

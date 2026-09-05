# `DemandSchedulePolicy`

The multi-unit bidder: truthful demand under the clinching rule, shaded demand under uniform pricing.

```python
DemandSchedulePolicy()
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L630-L668)

**Inherits from:** [AuctionPolicy](AuctionPolicy.md)

Under clinching, truthful demand is an equilibrium [ausubel2004, pp. 1454-1460], so the schedule is the
seat's true decayed marginal values. Under UNIFORM pricing it is not — an inframarginal unit's bid sets
the price the seat pays on the units it wins — so the policy searches a one-parameter family of shaded
schedules `(m_1, s*m_2, ..., s*m_k)` over `s` on a grid and keeps the one with the highest expected
surplus against the rivals' posteriors. The restriction to one shading parameter is a deliberate,
documented approximation of the equilibrium schedule of [ausubel_cramton2014, pp. 1370-1378]: it captures
the direction and the gradient (later units shaded more) without claiming to be the exact fixed point,
and the DEMAND-REDUCTION-FREE schedule — not this one — is what the metric divides against.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SHADE_GRID` | `tuple[float, ...]` |  |
| `name` |  |  |

## Methods {#methods}

## `bid_for` {#bid_for}

```python
bid_for(self, state: AuctionState, item: int) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L648-L649)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |
| `item` | `int` | *required* |  |

## `schedule` {#schedule}

```python
schedule(self, state: AuctionState) -> list[int]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L651-L668)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [AuctionState](AuctionState.md) | *required* |  |

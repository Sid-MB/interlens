# `BidLedger`

Monotonic bid ids, standing-high tracking, exits, and the eligibility ratchet.

```python
BidLedger(n_items: int, *, prefix: str = 'B', activity_rule: str = 'none')
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L282-L387)

The sibling of `arena.actions.OfferRegistry` and it holds the same purity property: the ledger is a
PURE FUNCTION of the applied action sequence, so `replay.py` reconstructs it identically from a stored
episode and no analysis has to trust a stored summary. `to_json` / `from_json` also persist it
directly.

Parameters
----------
n_items : int
    Number of lots, so per-lot state is allocated up front.
prefix : str
    Bid-id prefix; ids are `B1`, `B2`, ... in application order across the whole episode.
activity_rule : str
    `"eligibility_ratchet"` makes a :class:`PassLot` irrevocable within its stage (a bidder that passes
    on lot `j` may not bid on `j` again that stage); `"none"` records the pass without binding it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_items` | `int` | *required* |  |
| `prefix` | `str` | `'B'` |  |
| `activity_rule` | `str` | `'none'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `activity_rule` |  |  |
| `bids` | list[[StandingBid](StandingBid.md)] |  |
| `exited` | `dict[int, list[int]]` |  |
| `n_items` |  |  |
| `passed` | `dict[int, set[tuple[int, int]]]` |  |
| `prefix` |  |  |

## Methods {#methods}

## `active_seats` {#active_seats}

```python
active_seats(self, stage: int, n_bidders: int) -> list[int]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L362-L365)

Seats that have not exited the clock in `stage`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `n_bidders` | `int` | *required* |  |

## `apply` {#apply}

```python
apply(self, action: Action, seat: int, *, stage: int, round: int) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L311-L338)

Fold one parsed action into the ledger. :class:`Bid` registers (returning the new bid id and superseding any lower standing bid on that lot), :class:`PassLot` records the pass, :class:`Exit` records the irrevocable clock exit; everything else is a no-op here (the scenario owns settlement).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](../../actions/Action.md) | *required* |  |
| `seat` | `int` | *required* |  |
| `stage` | `int` | *required* |  |
| `round` | `int` | *required* |  |

## `eligible` {#eligible}

```python
eligible(self, seat: int, item: int, stage: int) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L356-L360)

Whether `seat` may still bid on `item` this stage under the activity rule.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
| `item` | `int` | *required* |  |
| `stage` | `int` | *required* |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'BidLedger'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L378-L387)

Rebuild a :class:`BidLedger` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `stage_bids` {#stage_bids}

```python
stage_bids(self, stage: int) -> list[StandingBid]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L367-L369)

Every bid recorded in `stage`, live or superseded, in application order.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |

## `standing` {#standing}

```python
standing(self, item: int, stage: int) -> StandingBid | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L341-L344)

The live standing high bid on `item` in `stage`, or `None`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `item` | `int` | *required* |  |
| `stage` | `int` | *required* |  |

## `standing_prices` {#standing_prices}

```python
standing_prices(self, stage: int, *, reserve: int = 0) -> list[int]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L346-L349)

Per-lot standing price in `stage` (`reserve` where no bid stands).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `reserve` | `int` | `0` |  |

## `standing_winners` {#standing_winners}

```python
standing_winners(self, stage: int) -> list[int | None]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L351-L354)

Per-lot standing high bidder in `stage` (`None` where no bid stands).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L371-L376)

JSON-ready dict of the whole ledger.

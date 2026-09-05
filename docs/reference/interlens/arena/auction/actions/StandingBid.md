# `StandingBid`

One registered bid and its live state — the sibling of `arena.actions.Offer`.

```python
StandingBid(
	bid_id: str,
	stage: int,
	round: int,
	seat: int,
	item: int,
	amount: int,
	live: bool = True,
)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L255-L279)

`live` flips to False when the bid is superseded by a higher standing bid on the same lot. Superseded
bids are kept, never deleted, so the ledger is a complete record of the price path.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bid_id` | `str` | *required* |  |
| `stage` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `seat` | `int` | *required* |  |
| `item` | `int` | *required* |  |
| `amount` | `int` | *required* |  |
| `live` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `amount` | `int` |  |
| `bid_id` | `str` |  |
| `item` | `int` |  |
| `live` | `bool` |  |
| `round` | `int` |  |
| `seat` | `int` |  |
| `stage` | `int` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'StandingBid'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L275-L279)

Rebuild a :class:`StandingBid` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L270-L273)

JSON-ready dict.

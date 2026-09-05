# `Offer`

One registered offer and its live vote state.

```python
Offer(
	offer_id: OfferId,
	deal: Deal,
	proposer: str,
	round: int = 0,
	accepts: set[str] = set(),
	rejects: set[str] = set(),
	live: bool = True,
)
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L164-L187)

`live` flips to False on withdrawal/supersession; the
accept/reject sets are the votes gathered so far (closure semantics — unanimity vs veto-weighted — are the
scenario's call, computed off these sets).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |
| `deal` | `Deal` | *required* |  |
| `proposer` | `str` | *required* |  |
| `round` | `int` | `0` |  |
| `accepts` | `set[str]` | `set()` |  |
| `rejects` | `set[str]` | `set()` |  |
| `live` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `accepts` | `set[str]` |  |
| `deal` | `Deal` |  |
| `live` | `bool` |  |
| `offer_id` | `OfferId` |  |
| `proposer` | `str` |  |
| `rejects` | `set[str]` |  |
| `round` | `int` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'Offer'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L183-L187)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L178-L181)

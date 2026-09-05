# `TransferBook`

Declared side payments, and their execution at settlement (`dm_transfers` only).

```python
TransferBook()
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L489-L549)

Same purity property as :class:`BidLedger`: a pure function of the applied :class:`Transfer` actions. A
transfer whose sender cannot cover it out of its stage budget net of auction payments is recorded as
`executed=False` rather than silently dropped, because an UNPAID promise is exactly the weak-cartel
behavior the design wants to measure [mcafee_mcmillan1992].

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `declared` | `list[dict]` |  |

## Methods {#methods}

## `declare` {#declare}

```python
declare(self, transfer: Transfer, sender: str, *, stage: int) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L500-L504)

Record one declared transfer, with its condition if it carries one.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `transfer` | [Transfer](Transfer.md) | *required* |  |
| `sender` | `str` | *required* |  |
| `stage` | `int` | *required* |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'TransferBook'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L544-L549)

Rebuild a :class:`TransferBook` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `settle` {#settle}

```python
settle(
	self,
	stage: int,
	capacity: dict[str, float],
	*,
	won_nothing=None,
) -> dict[str, float]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L506-L538)

Execute the stage's declared transfers against each sender's remaining `capacity` (budget minus auction payments), in declaration order.

Returns the net transfer per seat (positive = received).

A CONDITIONAL transfer is escrowed until here and then executed only if its condition holds against the
realized allocation. `won_nothing` is the set of seat names that took no lot this stage, which is the
only thing `recipient_wins_nothing` needs; a conditional transfer settled without it is refused
rather than paid, because paying an unevaluated condition is the unconditional gift the condition
exists to avoid.

Every declaration records WHY it ended as it did in `outcome` — `paid`, `condition_unmet`, or
`insufficient_capacity`. The distinction is the measurement: a ring that declares conditional
payments and sees them all lapse because nobody stood aside is a different finding from a ring that
never declares one, and both are different from a ring that cannot afford to.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `capacity` | `dict[str, float]` | *required* |  |
| `won_nothing` |  | `None` |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L540-L542)

JSON-ready dict.

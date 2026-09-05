# `Bid`

A priced bid of `amount` on lot `item` (a slot index).

```python
Bid(item: int, amount: int)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L58-L68)

**Inherits from:** [Action](../../actions/Action.md)

The single-lot families carry `item = 0`;
SAA turns may carry several :class:`Bid` moves, one per lot.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `item` | `int` | *required* |  |
| `amount` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `amount` | `int` |  |
| `item` | `int` |  |
| `kind` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L67-L68)

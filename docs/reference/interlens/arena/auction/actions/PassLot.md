# `PassLot`

Decline to bid on lot `item` this round.

```python
PassLot(item: int)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L71-L81)

**Inherits from:** [Action](../../actions/Action.md)

Under the eligibility ratchet this is IRREVOCABLE for the
rest of the stage (design.md §3.3, SAA), which is what makes passing a strategic commitment rather than
a shrug.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `item` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `item` | `int` |  |
| `kind` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L80-L81)

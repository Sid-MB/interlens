# `Demand`

A demand for `units` at the current clock price in a clinching stage; must be weakly decreasing across rounds [ausubel2004].

```python
Demand(units: int)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L115-L124)

**Inherits from:** [Action](../../actions/Action.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `units` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |
| `units` | `int` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L123-L124)

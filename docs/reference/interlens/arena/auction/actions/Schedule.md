# `Schedule`

A weakly-decreasing per-unit bid vector for a uniform-price stage.

```python
Schedule(amounts: tuple[int, ...])
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L104-L112)

**Inherits from:** [Action](../../actions/Action.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `amounts` | `tuple[int, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `amounts` | `tuple[int, ...]` |  |
| `kind` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L111-L112)

# `Propose`

Register a complete deal.

```python
Propose(deal: Deal)
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L81-L90)

**Inherits from:** [Action](Action.md)

The registry assigns the `offer_id` on registration — it is not chosen by the
model — so ids are monotonic and unambiguous. `deal` is the decoded option-index tuple.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `deal` | `Deal` |  |
| `kind` | `str` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L89-L90)

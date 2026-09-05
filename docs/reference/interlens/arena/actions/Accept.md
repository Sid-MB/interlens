# `Accept`

Accept a specific standing offer by id (an `ACCEPT` vote on that exact deal).

```python
Accept(offer_id: OfferId)
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L93-L101)

**Inherits from:** [Action](Action.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer_id` | `OfferId` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |
| `offer_id` | `OfferId` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L100-L101)

# `DirectMessage`

A private message to named recipients.

```python
DirectMessage(to: tuple[str, ...], text: str)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L169-L180)

**Inherits from:** [Action](../../actions/Action.md)

Available under `dm` / `dm_transfers`, capped at
`dm_cap` recipients per turn — the cap bounds cost and keeps the DM graph interpretable, since a bidder
that DMs all four rivals every turn is broadcasting (design.md §3.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `to` | `tuple[str, ...]` | *required* |  |
| `text` | `str` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |
| `text` | `str` |  |
| `to` | `tuple[str, ...]` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L179-L180)

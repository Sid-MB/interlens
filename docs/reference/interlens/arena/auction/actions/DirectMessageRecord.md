# `DirectMessageRecord`

One delivered private message.

```python
DirectMessageRecord(
	stage: int,
	round: int,
	sender: str,
	recipient: str,
	text: str,
	phase: str | None = None,
)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L392-L417)

The DM graph and the per-dyad MI estimator are both built from these,
so every field the analysis needs (sender, recipient, stage, round, phase) is on the record itself.

`phase` is the scenario phase the message was attached to — a DM rides on whatever turn its sender
wrote, so one sent on a bidding turn and one sent in a message round are different acts and must not read
the same in the channel log.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `sender` | `str` | *required* |  |
| `recipient` | `str` | *required* |  |
| `text` | `str` | *required* |  |
| `phase` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `phase` | `str \| None` |  |
| `recipient` | `str` |  |
| `round` | `int` |  |
| `sender` | `str` |  |
| `stage` | `int` |  |
| `text` | `str` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'DirectMessageRecord'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L413-L417)

Rebuild a :class:`DirectMessageRecord` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L408-L411)

JSON-ready dict.

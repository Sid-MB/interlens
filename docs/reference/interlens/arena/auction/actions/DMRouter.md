# `DMRouter`

Delivers addressed private messages to their recipients only, and records the directed graph.

```python
DMRouter(seats: tuple[str, ...], *, dm_cap: int = 2)
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L420-L486)

Privacy is STRUCTURAL, as in `scorable.py::_publish()`: the router hands a message to the named
recipients and to nobody else, so a seat cannot leak private state by mis-tagging it. Unknown recipients
and self-addressed messages are dropped rather than delivered, and the count of dropped recipients is
reported so a mis-addressed DM shows up as a protocol-hygiene number rather than vanishing.

Parameters
----------
seats : tuple[str, ...]
    Display names of the five seats, in seat order.
dm_cap : int
    Maximum recipients per turn; recipients beyond the cap are dropped (design.md §3.2).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seats` | `tuple[str, ...]` | *required* |  |
| `dm_cap` | `int` | `2` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `dm_cap` |  |  |
| `dropped` | `int` |  |
| `records` | list[[DirectMessageRecord](DirectMessageRecord.md)] |  |
| `seats` |  |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'DMRouter'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L480-L486)

Rebuild a :class:`DMRouter` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `graph` {#graph}

```python
graph(self, *, stage: int | None = None) -> dict[tuple[str, str], int]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L465-L472)

The directed message-count graph `{(sender, recipient): count}`, optionally for one stage.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `stage` | `int \| None` | `None` |  |

## `inbox` {#inbox}

```python
inbox(self, recipient: str, *, stage: int | None = None) -> list[DirectMessageRecord]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L460-L463)

Every message delivered to `recipient` (optionally within one stage), in order — the DM history that rides in that seat's view and nobody else's.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `recipient` | `str` | *required* |  |
| `stage` | `int \| None` | `None` |  |

## `route` {#route}

```python
route(
	self,
	dm: DirectMessage,
	sender: str,
	*,
	stage: int,
	round: int,
	phase: str | None = None,
) -> list[DirectMessageRecord]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L442-L458)

Deliver one :class:`DirectMessage` and return the records created (also appended to :attr:`records`).

Recipients past :attr:`dm_cap`, unknown names, and the sender itself are dropped.
`phase` is stamped on every record so the channel log says which turn each message rode on.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `dm` | [DirectMessage](DirectMessage.md) | *required* |  |
| `sender` | `str` | *required* |  |
| `stage` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `phase` | `str \| None` | `None` |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L474-L478)

JSON-ready dict — DM payloads are part of the transcript export, since the graph cannot be reconstructed without them (design.md §10).

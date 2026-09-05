# `SeatConfig`

What the lobby says should sit in one seat — the unit of both initial configuration and a mid-game swap.

```python
SeatConfig(
	kind: str = 'llm',
	model_id: str | None = None,
	policy: str | None = None,
	thinking: str = '',
	instructions: str = '',
	display_name: str = '',
)
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L191-L291)

The same dataclass travels in three directions (lobby form -> server, server -> participant construction,
server -> browser as part of `lobby_state`), so a seat is described exactly once.

Parameters
----------
kind : str
    One of :data:`SEAT_KINDS`.
model_id : str | None
    For `kind="llm"`: which model (a :class:`ModelInfo` `model_id`). Ignored otherwise.
policy : str | None
    For `kind="rational"` / `"oracle"`: the policy name (a key of `arena.table.POLICY_FACTORIES`, e.g.
    `"bayes-rational"`). The kind, not the policy, decides whether the seat gets full-information tables.
thinking : str
    For `kind="llm"`: the extended-thinking mode, restricted to the model's `thinking_modes`. The empty
    string means "whatever this model's default is" (:func:`default_thinking`, i.e. thinking on wherever the
    model allows it) and is what an unconfigured seat carries — spelled as its own value rather than as a
    literal mode because `off` has to keep meaning a deliberate `off`, and a seat that had thinking
    turned off by hand must not have it turned back on by a re-validation.
instructions : str
    Extra PRIVATE instructions for this seat, appended to its `private_context` as one labelled segment.
    This is how a live operator gives one seat a persona or a hidden agenda without editing a scaffold. Empty
    string means none. Meaningless for computable seats (the lobby greys the field out) since a policy does
    not read prose.
display_name : str
    Who the transcript says is playing — the `human:<name>` label for a human seat, and the occupant badge
    for any other. Empty string means "derive it from the kind and model/policy".

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `kind` | `str` | `'llm'` |  |
| `model_id` | `str \| None` | `None` |  |
| `policy` | `str \| None` | `None` |  |
| `thinking` | `str` | `''` |  |
| `instructions` | `str` | `''` |  |
| `display_name` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `display_name` | `str` |  |
| `instructions` | `str` |  |
| `kind` | `str` |  |
| `model_id` | `str \| None` |  |
| `policy` | `str \| None` |  |
| `thinking` | `str` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(cls, d: dict) -> 'SeatConfig'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L285-L291)

Rebuild from a browser-supplied dict, ignoring keys this version does not know (the same forward-compatible rule `TurnRecord.from_json` follows).

Does NOT validate — the session validates,
because it is the half that knows which models and policies actually exist.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `occupant_detail` {#occupant_detail}

```python
occupant_detail(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L244-L256)

The half of :meth:`occupant_label` after the colon — the model, policy or person.

Exposed separately for one reason: a `HumanParticipant` stamps `human:<its own name>` on the turns it
plays (it knows who is at the keyboard; the table only knows who it was told about), so the session MUST
construct it with this exact string or the seat would report two different players for the same person.

## `occupant_label` {#occupant_label}

```python
occupant_label(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L230-L242)

The `kind:detail` string stamped on every turn this seat plays (`TurnRecord.occupant`).

One function so the label the router stamps, the badge the transcript draws and the swap event's
`from`/`to` are all the same string — an occupant timeline assembled from three spellings of the same
seat would be unreadable. `display_name` overrides the detail when set.

The prefix is the seat's ROLE rather than its `kind` verbatim (`llm` -> `api:`, `rational` ->
`policy:`), matching the vocabulary the rest of the arena already uses for seat kinds. The detail
defaults to whatever identifies that role: the model id, the policy name, the player's name.

## `resolved` {#resolved}

```python
resolved(self, models: Any) -> 'SeatConfig'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L258-L278)

This seat with the choices nobody made filled in from the offered models — the ONE place defaults land.

For an `llm` seat: an empty `model_id` becomes :func:`default_model_id` (the provider's flagged
model), and an empty `thinking` becomes that model's :func:`default_thinking` (thinking on wherever it
is allowed). Any other seat, and any field already set, is returned untouched — including a deliberate
`off`, which is why the unset value is `""` rather than a mode name.

Called by the session on every lobby edit, every start and every swap, so a client that posts a bare
`{"kind": "llm"}` gets the same seat the lobby page would have shown it. Idempotent: resolving a
resolved config returns it unchanged (the same object, in fact).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `models` | `Any` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L280-L283)

The wire form the lobby page and `lobby_state` events carry.

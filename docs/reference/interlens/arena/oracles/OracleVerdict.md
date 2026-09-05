# `OracleVerdict`

One oracle's read of a decision point.

```python
OracleVerdict(
	action_values: dict[Any, float],
	best: Any,
	beliefs: dict | None = None,
	flags: list[str] = list(),
	extra: dict = dict(),
)
```

Defined in [`interlens.arena.oracles`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L92-L162)

`action_values` maps each evaluated action to its value (surplus / continuation value — the oracle's own
units); `best` is the argmax action; `beliefs` optionally carries the oracle's posterior (e.g. a
belief oracle's type distribution); `flags` are named hard-violation markers (e.g. `"ir_violation"`,
`"below_threshold_accept"`). `extra` is a free-form JSON-serializable dict for per-verdict diagnostics
beyond the value table — e.g. a best-response oracle's per-action `surplus_loss` and `best_response_deal`,
an acceptance oracle's `reservation` / `rounds_left`, an equilibrium oracle's `v*` — carried through
`to_json` into the episode's oracle log so the divergence atlas can read them. Actions are the dict keys,
so they must be hashable — the formal :class:`~interlens.arena.actions.Action` dataclasses are frozen and
satisfy this.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action_values` | `dict[Any, float]` | *required* |  |
| `best` | `Any` | *required* |  |
| `beliefs` | `dict \| None` | `None` |  |
| `flags` | `list[str]` | `list()` |  |
| `extra` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `action_values` | `dict[Any, float]` |  |
| `beliefs` | `dict \| None` |  |
| `best` | `Any` |  |
| `extra` | `dict` |  |
| `flags` | `list[str]` |  |

## Methods {#methods}

## `best_value` {#best_value}

```python
best_value(self) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L116-L120)

The value of the best action (`action_values[best]` if present, else the max value, else `None`).

## `divergence` {#divergence}

```python
divergence(self, action: Any) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L122-L128)

Regret of `action`: `best_value - value(action)` (>= 0), or `None` if either is unknown.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | `Any` | *required* |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'OracleVerdict'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L141-L162)

Rebuild an `OracleVerdict` from :meth:`to_json`, reconstructing typed :class:`~interlens.arena.actions.Action` keys (and `best`) so the regret math works on a verdict loaded from a stored episode.

`beliefs`/`flags`/`extra` come back as the JSON that was stored — `extra`
is free-form diagnostics, so the coercion :func:`_jsonify` applies on the way out is deliberately not
inverted on the way in.

Reads BOTH stored shapes: the current `{action_key: value}` object (episode `schema_version` v1.1+)
and the original `[{"action": {...}, "value": v}, ...]` list of pairs (v1.0), so episodes recorded
before the shape change still load and replay.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L130-L139)

The stored form.

`action_values` is a JSON OBJECT keyed by
:func:`~interlens.arena.actions.action_key` (the action's `to_json` dumped with sorted keys) — a map,
because that is what it is, so a reader can look one action's value up directly instead of scanning a
list of pairs. `best` is the same key string, so `stored['action_values'][stored['best']]` is the
best value. `beliefs`/`extra` are free-form oracle payloads run through :func:`_jsonify`, so an
action-keyed dict or a numpy table an oracle stashed can't leave the record un-serializable.

## `value_of` {#value_of}

```python
value_of(self, action: Any) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L112-L114)

The value the oracle assigns `action`, or `None` if it wasn't evaluated.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | `Any` | *required* |  |

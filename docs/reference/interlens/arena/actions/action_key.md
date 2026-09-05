# `action_key`

The canonical STRING an action serializes to when it must be a JSON object key or a sort key — its `to_json()` dumped with sorted keys (`'{"action": "accept", "offer_id": "O1"}'`).

```python
action_key(action: Action | None) -> str | None
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L418-L440)

`None` maps to
`None`.

One definition serves two needs that must agree: an `OracleVerdict`'s `action_values` is keyed by action,
and JSON object keys must be strings; and the oracles sort their scored actions by this key so a stored
verdict is byte-reproducible regardless of the order the legal actions arrived in. :func:`action_from_key`
is the exact inverse.

Memoized when it can be: every `Action` is a frozen dataclass, so the key is a pure function of an
immutable value and a cache hit returns the identical string. It earns its keep because the oracles call
this once per legal action per turn to SORT them, and a long-horizon turn carries an accept and a reject
for every live offer — the same few actions, re-created and re-serialized every round. An action that is
nonetheless unhashable (a `Propose` built with a list `deal` rather than the decoded tuple) still
works: it takes the uncached path and gets the same string, so memoization can never narrow what this
function accepts.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](Action.md) \| None | *required* |  |

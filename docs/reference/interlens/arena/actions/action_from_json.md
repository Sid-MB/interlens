# `action_from_json`

Reconstruct a typed :class:`Action` from its stored dict — the inverse of `Action.to_json()`.

```python
action_from_json(d: dict) -> Action
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L142-L159)

Accepts
the kind under `"action"` / `"type"` / `"kind"` (so it reads both the canonical flat form and a stored
nested action object). Used to round-trip verdicts and to rebuild the action series from stored episodes.
Raises `ValueError` if `d` doesn't name a known action kind.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

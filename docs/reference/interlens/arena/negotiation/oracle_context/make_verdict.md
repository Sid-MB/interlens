# `make_verdict`

Build an `OracleVerdict` with its free-form `extra` diagnostics coerced JSON-safe up front (the `|D|×n` numpy tables / typed actions the oracles stash) via the shared `_jsonify`, so `to_json` and the episode save never crash.

```python
make_verdict(
	action_values,
	best=None,
	*,
	beliefs=None,
	flags=None,
	extra=None,
) -> OracleVerdict
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L54-L59)

`beliefs` is coerced later by `OracleVerdict.to_json`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action_values` |  | *required* |  |
| `best` |  | `None` |  |
| `beliefs` |  | `None` |  |
| `flags` |  | `None` |  |
| `extra` |  | `None` |  |

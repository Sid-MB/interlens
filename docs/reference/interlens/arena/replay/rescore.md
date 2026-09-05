# `rescore`

Replay `episode` and compare the recomputed outcome to the recorded one on `fields`.

```python
rescore(
	scenario: Scenario,
	instance: Instance,
	episode: dict,
	fields: tuple[str, ...] = DEFAULT_FIELDS,
) -> dict
```

Defined in [`interlens.arena.replay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/replay.py#L128-L140)

Returns `{"match": bool, "recorded": {...}, "recomputed": {...}, "mismatches": [field, ...]}`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `episode` | `dict` | *required* |  |
| `fields` | `tuple[str, ...]` | `DEFAULT_FIELDS` |  |

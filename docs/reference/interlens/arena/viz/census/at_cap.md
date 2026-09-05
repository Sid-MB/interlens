# `at_cap`

Whether one payload turn spent essentially its whole generation budget.

```python
at_cap(row: dict) -> bool
```

Defined in [`interlens.arena.viz.census`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/census.py#L45-L54)

There is no `stop_reason` on the local generation path, so "ran out of room" has to be inferred from
output length against the per-turn cap the scenario stamped on the request. A turn with no recorded cap
cannot be judged and is not counted.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `row` | `dict` | *required* |  |

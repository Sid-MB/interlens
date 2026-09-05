# `align`

Align two episode payloads slot by slot and locate the divergence point.

```python
align(left: dict, right: dict) -> tuple[list[dict], int | None]
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L91-L110)

Returns `(rows, divergence)` where each row is `{round, phase, seat, attempt, left_idx, right_idx,
different}` — the turn indices into each side's `turns` list, or `None` where only one side has that slot
(one episode closed early, or only one side needed a retry) — and `divergence` is the row position of the
FIRST behavioural difference, or `None` if the two episodes played identically throughout. `attempt` is 0
for a seat's first go at a slot and 1+ for an engine retry (see :func:`_by_slot`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left` | `dict` | *required* |  |
| `right` | `dict` | *required* |  |

# `score_table`

The quantified comparison: one row per metric with both values and the paired delta `right - left`.

```python
score_table(left: dict, right: dict, focal: list[int] | int | None) -> list[dict]
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L148-L194)

`focal` is the party index (or list of them) whose occupant was swapped. A one-seat swap gets that seat's own
surplus and capture; a swap that replaced several seats at once — a mixed table against an all-LLM table
replaces every seat but one — gets the MEAN over the swapped set, labelled with its size, because attributing
the effect to any single one of those seats would be wrong. The rows are omitted entirely when there is no swap
to attribute an effect to.

Every row carries `higher_is_better` so the page can colour a delta without guessing (`0` means neither
direction is better, e.g. rounds used), and `None` values pass through as `None` rather than zero — a
metric that was not recorded is missing, not neutral.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left` | `dict` | *required* |  |
| `right` | `dict` | *required* |  |
| `focal` | `list[int] \| int \| None` | *required* |  |

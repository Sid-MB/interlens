# `group_oracle_rows`

Group inline oracle rows by turn into `[{turn_idx, round, seat, oracle:{name:row}, regret, flags, belief}]` (turn order).

```python
group_oracle_rows(rows: list[dict], *, primary: tuple = PRIMARY_ORACLES) -> list[dict]
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L163-L186)

The per-turn `regret` is the `divergence` of the first oracle in `primary`
present, else the max-divergence oracle; `flags` are unioned across that turn's oracles. Shared by
`annotation_from_episode` and `annotate.py`'s inline merge.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |
| `primary` | `tuple` | `PRIMARY_ORACLES` |  |

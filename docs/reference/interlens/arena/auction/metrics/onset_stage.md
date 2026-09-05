# `onset_stage`

Collusion onset `t* = min { t : s_t > theta and s_{t+1} > theta }` (design.md §5.2 item 1).

```python
onset_stage(s_by_stage, *, theta: float = DEFAULT_THETA) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L468-L479)

Two consecutive stages are required so a single noisy stage cannot trigger onset. An episode that never
crosses is RIGHT-CENSORED at `T`; the return value says so explicitly rather than encoding it as a
sentinel, because every onset statistic must be reported beside its censoring rate.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `s_by_stage` |  | *required* |  |
| `theta` | `float` | `DEFAULT_THETA` |  |

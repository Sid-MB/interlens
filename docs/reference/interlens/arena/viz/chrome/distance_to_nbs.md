# `distance_to_nbs`

How far the deal that closed sits from the Nash bargaining solution, in the chart's own plane.

```python
distance_to_nbs(payload: dict) -> float | None
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L184-L202)

Euclidean distance in the two scale-invariant coordinates the frontier chart plots — joint welfare (mean
normalized surplus) and the worst-off party's normalized surplus — between the agreed deal and the NBS deal.
`None` when no deal closed or the instance carries no solution set. It is a *projected* distance by
construction, like the chart: two deals that differ only along dimensions the projection drops read as
identical here, which is why the number sits beside the exact per-party table rather than replacing it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |

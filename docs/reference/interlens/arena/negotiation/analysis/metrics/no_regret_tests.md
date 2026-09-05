# `no_regret_tests`

Park no-regret trend + log–log tests over the per-turn regret series.

```python
no_regret_tests(annotation: EpisodeAnnotation | None) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L187-L194)

Returns `None` fields when there
is no annotation or the series is too short.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | *required* |  |

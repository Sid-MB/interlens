# `regret_series`

The per-turn headline regret series (surplus loss) from an annotation, 0.0 where a turn has no recorded regret.

```python
regret_series(annotation: EpisodeAnnotation | None) -> list[float]
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L179-L184)

Empty when there is no annotation (no oracle pass has been run).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | *required* |  |

# `divergence_turns`

Turn indices whose per-turn regret exceeds `threshold` — the localized divergence points.

```python
divergence_turns(
	annotation: EpisodeAnnotation | None,
	threshold: float = DEFAULT_REGRET_THRESHOLD,
) -> list[int]
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L197-L202)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | *required* |  |
| `threshold` | `float` | `DEFAULT_REGRET_THRESHOLD` |  |

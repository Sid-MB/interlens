# `episode_metrics`

All divergence metrics for one episode, in one dict — the row the atlas aggregates over.

```python
episode_metrics(
	game: GameAnalysis,
	view: EpisodeView,
	annotation: EpisodeAnnotation | None = None,
) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L268-L288)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | `None` |  |

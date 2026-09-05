# `taxonomy_report`

Run every taxonomy row over one episode, in row order.

```python
taxonomy_report(
	game: GameAnalysis,
	view: EpisodeView,
	annotation: EpisodeAnnotation | None = None,
) -> list[CategoryResult]
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L320-L323)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | `None` |  |

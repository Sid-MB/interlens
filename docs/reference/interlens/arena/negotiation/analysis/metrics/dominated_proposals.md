# `dominated_proposals`

Turns on which the proposed deal is Pareto-dominated — a strictly-better-for-everyone alternative existed.

```python
dominated_proposals(game: GameAnalysis, view: EpisodeView) -> list[dict]
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L145-L162)

Reports both dominance vs the Pareto frontier and, more sharply, vs the IR (feasible) set (a Pareto
improvement everyone would have accepted). Mechanical.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

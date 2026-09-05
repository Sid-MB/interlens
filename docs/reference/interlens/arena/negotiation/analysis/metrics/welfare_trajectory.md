# `welfare_trajectory`

Per-round utilitarian welfare of the standing (tabled) deal, with an OLS slope and variance.

```python
welfare_trajectory(game: GameAnalysis, view: EpisodeView) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L102-L118)

A negative
slope = deals get collectively *worse* over rounds (Study B: Phi-3.5 USW slope −5.8); high variance = the
table thrashes. `nan` slope when fewer than two rounds carry a standing offer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

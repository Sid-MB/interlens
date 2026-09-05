# `ir_violations`

Turns on which a party proposed or accepted a deal scoring below its OWN threshold (surplus < 0) — the individual-rationality / 'wrong deal' failure (Abdelnabi wrong-deal rate 7–20%; multi-buyer sell-below-cost up to 38.3%).

```python
ir_violations(game: GameAnalysis, view: EpisodeView) -> list[dict]
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L122-L142)

Fully mechanical: reads the acting party's surplus off the score sheet.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

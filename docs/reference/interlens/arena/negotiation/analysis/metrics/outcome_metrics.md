# `outcome_metrics`

Outcome-level divergence for one episode.

```python
outcome_metrics(game: GameAnalysis, view: EpisodeView) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L63-L99)

On a no-deal episode the welfare fields are 0 (USW/ESW/NSW) and
Gini is `nan` (no distribution), while `surplus` is `None` — this is the U-vs-U* distinction: the
unconditional welfare counts no-deal as 0, the conditional (`*_conditional`) is `None` and excluded from
deal-only aggregates upstream.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

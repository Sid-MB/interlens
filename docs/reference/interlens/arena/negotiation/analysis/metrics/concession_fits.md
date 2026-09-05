# `concession_fits`

Per-party concession-curve fit on the sequence of the party's OWN surplus across its OWN successive proposals (the offers it puts on the table).

```python
concession_fits(game: GameAnalysis, view: EpisodeView) -> dict[str, curves.ConcessionFit]
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L165-L175)

Parties with < 3 proposals get an `n<3` fit with `nan`
shape metrics. Read τ (burstiness) and CRI (rigidity) off each fit.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

# `stated_offer_faithfulness`

Internal faithfulness (LAMEN, Davidson 2024): are a party's actual proposals consistent with its own machine-readable 'currently acceptable offer' note?

```python
stated_offer_faithfulness(game: GameAnalysis, view: EpisodeView) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L206-L231)

For each proposal made after the party states an
acceptable offer, faithful iff the proposal is at least as good for the party as its stated floor
(own-surplus(proposal) >= own-surplus(stated floor) − ε). Returns the overall rate and per-party rates; the
rate is `nan` when the scenario elicits no acceptable-offer note (none of the turns carry `stated_offer`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `view` | [EpisodeView](../episode_view/EpisodeView.md) | *required* |  |

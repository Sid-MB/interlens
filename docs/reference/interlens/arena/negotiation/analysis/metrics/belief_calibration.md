# `belief_calibration`

Belief-calibration error: mean L1 distance between the model's stated belief and the oracle posterior over the turns where both are present, when both are numeric vectors/distributions.

```python
belief_calibration(annotation: EpisodeAnnotation | None) -> dict
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L234-L246)

`nan` when the scenario
elicits no beliefs or the oracle recorded none (belief calibration is the BeliefOracle-dependent metric).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `annotation` | [EpisodeAnnotation](../annotations/EpisodeAnnotation.md) \| None | *required* |  |

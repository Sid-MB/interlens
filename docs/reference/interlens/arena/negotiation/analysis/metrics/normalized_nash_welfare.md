# `normalized_nash_welfare`

Bounded Nash-welfare endpoint in per-party feasible-surplus units.

```python
normalized_nash_welfare(game: GameAnalysis, surplus: tuple[float, ...] | None) -> float
```

Defined in [`interlens.arena.negotiation.analysis.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/metrics.py#L46-L60)

Each surplus is divided by that party's maximum surplus over the individually rational set
(`game.scale`).  A missing outcome, a non-positive surplus, or an unavailable/invalid scale scores zero.
The geometric mean is in `[0, 1]` for solved finite games and is invariant to independent positive affine
rescalings of the parties' utility sheets.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | [GameAnalysis](../game_analysis/GameAnalysis.md) | *required* |  |
| `surplus` | `tuple[float, ...] \| None` | *required* |  |

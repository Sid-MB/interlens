# `check_power_insensitivity`

Identical strategy across power-asymmetry conditions where the oracle strategy differs — inherently CROSS-condition.

```python
check_power_insensitivity(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L249-L255)

Cannot fire on a single episode; `report.py` computes it across matched arms.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |

# `check_arithmetic_error`

Recompute a party's stated own-score for a deal against the true score sheet.

```python
check_arithmetic_error(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L135-L156)

Mechanical when the action
schema carries a machine-readable `stated_score`; annotation flags (written by an oracle pass that parsed
the CoT) are also honored.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |

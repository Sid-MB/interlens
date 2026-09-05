# `check_tactic_deficit`

STUB (Tier 3).

```python
check_tactic_deficit(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L282-L288)

Tactic-frequency profile vs successful humans (Diplomacy tactic taxonomy,
arXiv:2512.18292). Hook: an LLM tactic classifier (validated to Gwet's AC1 >= 0.65) labels each message with
the 8-tactic scheme; compare the frequency profile to a human reference.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |

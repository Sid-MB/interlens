# `check_premature_concession`

Excess/early concession: a party gives up a large fraction of its own surplus across its offers (high burstiness τ with a downward step), especially early.

```python
check_premature_concession(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L210-L227)

Read from the concession fits (τ, CRI) and the
own-surplus drop.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |

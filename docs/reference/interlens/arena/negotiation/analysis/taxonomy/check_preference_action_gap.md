# `check_preference_action_gap`

STUB (Tier 3).

```python
check_preference_action_gap(game, view, annotation) -> CategoryResult
```

Defined in [`interlens.arena.negotiation.analysis.taxonomy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/taxonomy.py#L263-L270)

Correct opponent-preference inference in the CoT but the offer is unchanged vs the
best-response oracle (Counterparty Modeling, arXiv:2605.16575). Hook: an LLM judge extracts the inferred
opponent preference from `TurnView.thinking`; compare the made offer to the BestResponseOracle action
given that (correct) inference. Fires when inference is correct but the action does not move toward BR.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `view` |  | *required* |  |
| `annotation` |  | *required* |  |

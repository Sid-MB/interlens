# `advice_card`

The episode's advice audit as one server-rendered section, or `""` when no turn was advised.

```python
advice_card(payload: dict) -> str
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L311-L349)

One row per advised turn — the planner's top pick, the move the seat played, and the stored verdict on the
pair — with the per-turn evidence (the parsed claims and their quotes, the ranked candidates, the ledger
counts) in each turn's own card below. The section is a hazard style when any turn overrode its advice,
because that is the fact a reader must not scroll past: those turns measure the model's own choice, not the
advisor's.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |

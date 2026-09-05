# `offer_registry`

Recover `{offer_id: Deal}` from the game/history.

```python
offer_registry(game, history) -> dict
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L219-L257)

Prefers an explicit registry, read as either an
`offers` ATTRIBUTE (`history.offers` / `game.offers`) or, when `history` is a mapping, an `offers`
KEY -- the shape the scenario's per-turn history snapshot carries (`ScorableNegotiation._history_snapshot`
stores `offers` as a LIST of serialized `Offer` dicts, each with `offer_id` + `deal`). The registry
may thus be a `{id: offer}` mapping OR a list of `Offer.to_json()` dicts / `Offer` objects. Falls back
to scanning turns for `Propose` actions, assigning sequential ids `O1, O2, ...` in order of appearance.

Getting this right is load-bearing: if the standing offers are lost, the acceptance / threshold /
best-response oracles value every `Accept` at the no-deal continuation instead of the offer's realized
surplus (the single-shot mis-scoring bug), so a rational accept reads as 0 regret AND 0 value.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |

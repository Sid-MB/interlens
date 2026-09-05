# `fit_belief`

A :class:`~interlens.arena.negotiation.beliefs.BeliefOracle` fitted to everything `state` publicly reveals about the other seats — one posterior per opponent, updated from their observed offers.

```python
fit_belief(state: NegotiationState) -> BeliefOracle
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L771-L790)

Built FRESH per call rather than cached on a policy: it is fully determined by the offers in `state` and
`update_from_offers` rebuilds it from scratch anyway, so persisting it would buy nothing while making a
policy instance shared across concurrent seats race on mutable member state.

Module-level because two different consumers need the identical posterior — the acceptance-probability
table (:meth:`BayesianRationalPolicy._accept_prob_table`) and the fairness objective's opponent columns
(:meth:`FairnessRationalPolicy._objective`) — and a private-information agent whose two halves disagreed
about what it believes would not be one agent.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

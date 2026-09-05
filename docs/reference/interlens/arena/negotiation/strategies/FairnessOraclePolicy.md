# `FairnessOraclePolicy`

Omniscient **fairness oracle**: proposes and votes to maximize the table's normalized Nash welfare.

```python
FairnessOraclePolicy(
	*,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'fairness-oracle',
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L1065-L1101)

**Inherits from:** `_TableObjectivePolicy`

Reads every party's sheet (it requires the full-information `state.tables`) and substitutes
:func:`~interlens.arena.negotiation.fairness.mnw_objective` for its own surplus column, so:

- its **proposal** is the deal maximizing expected table welfare given who will accept — which on a game
  where some deal clears every threshold is exactly the discrete Nash Bargaining / Maximum Nash Welfare
  point, and with no acceptance uncertainty (its own table full of IR indicators) is that point outright;
- its **acceptance** runs the same optimal-stopping recursion in welfare units: take the standing offer iff
  the welfare it delivers is at least the welfare the oracle expects to reach by continuing;
- it still refuses to sign below its own threshold — on all three branches: accepting
  (:meth:`BayesianRationalPolicy.act`), the terminal vote, and *proposing*
  (:meth:`_TableObjectivePolicy._pick_proposal`, where the objective's `clip(u - tau, 0)` leaves it
  indifferent to its own losses and so cannot supply the refusal itself).

With no other seats to persuade this degenerates to the utilitarian planner's choice on the welfare
objective — it simply names the fairest feasible deal — which is the sense in which it is a
"self-assembling mediator" rather than a negotiator.

Falls back to its own surplus (i.e. behaves as the ordinary Bayesian agent) if seated in a game with no
full-information tables, since table welfare is not computable from one sheet; use
:class:`FairnessRationalPolicy` for the private-information version instead of relying on that fallback.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'fairness-oracle'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

# `FairnessRationalPolicy`

Private-information **fairness algorithmic** agent: the same welfare objective, estimated under its Bayesian posterior over the other seats' hidden sheets and thresholds.

```python
FairnessRationalPolicy(
	*,
	discount: float | None = None,
	walk_if_hopeless: bool = True,
	name: str = 'fairness-rational',
)
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L1104-L1137)

**Inherits from:** `_TableObjectivePolicy`

Where :class:`FairnessOraclePolicy` reads the opponents' normalized surpluses, this reads their
*posterior-expected* normalized surpluses off the same opponent-type grid the ordinary rational agent uses
for acceptance probabilities (:func:`fit_belief`, then
:meth:`~interlens.arena.negotiation.beliefs.BeliefState.expected_normalized_surplus_matrix`), and its own
column exactly. So the two agents differ ONLY in what they know, which is what makes their gap a clean
measurement of the price of private information for a fairness-seeker.

The estimate is a plug-in `obj(E[z])` rather than `E[obj(z)]` and is therefore optimistic by a Jensen
gap (see :mod:`~interlens.arena.negotiation.fairness`); combined with a posterior that only sees public
offers, it can target a deal that is not in fact the table's welfare maximizer. That is a substantive
prediction about this agent, not an implementation shortcut.

Uses the exact objective when it happens to be seated in a full-information game, so the two policies
coincide there by construction.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `discount` | `float \| None` | `None` |  |
| `walk_if_hopeless` | `bool` | `True` |  |
| `name` | `str` | `'fairness-rational'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |

# `value_to_go_beliefs`

Agent-`agent` continuation `Vi[t]` (shape `(T+2,)`) under the posterior.

```python
value_to_go_beliefs(
	tables: GameTables,
	agent: int,
	proposer_seq,
	T: int,
	discount: float,
	accept_prob,
	opp_proposal,
	*,
	min_accept: int | None = None,
	veto_seats=(),
	objective=None,
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L331-L395)

Parameters
----------
accept_prob : np.ndarray
    `(D, n)` posterior probability each seat accepts each deal (self-column is treated deterministically
    below, so it is ignored for `agent`).
opp_proposal : dict[int, int]
    Stationary modeled proposal (deal index) per opponent seat.
objective : np.ndarray | None
    Optional `(|D|,)` payoff column replacing `agent`'s own surplus, so the same rollout produces the
    continuation value of a **fairness-seeking** seat (`fairness.mnw_objective`) rather than a
    self-interested one. Only this seat's payoff changes; the modeled opponents keep behaving as
    self-interested acceptors/proposers. `None` (default) is the exact prior behaviour.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `agent` | `int` | *required* |  |
| `proposer_seq` |  | *required* |  |
| `T` | `int` | *required* |  |
| `discount` | `float` | *required* |  |
| `accept_prob` |  | *required* |  |
| `opp_proposal` |  | *required* |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |
| `objective` |  | `None` |  |

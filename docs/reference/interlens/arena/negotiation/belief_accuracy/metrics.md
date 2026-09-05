# `metrics`

The three scores of `belief` against `truth`, as a JSON-safe dict keyed by :data:`METRICS`.

```python
metrics(belief: BeliefState, deals_arr: np.ndarray, truth: TrueOpponent) -> dict
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L148-L159)

Three gemvs against the belief's cached matrices (posterior mass, expected utility, accept probability);
no loop over deals or types, and nothing is mutated.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `belief` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |
| `deals_arr` | `np.ndarray` | *required* |  |
| `truth` | [TrueOpponent](TrueOpponent.md) | *required* |  |

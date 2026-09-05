# `true_opponent`

Precompute one opponent's :class:`TrueOpponent` against `belief`'s grid — do this ONCE per episode.

```python
true_opponent(sheet, deals_arr: np.ndarray, belief: BeliefState) -> TrueOpponent
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L126-L135)

`belief` is used only for its (immutable, process-cached) type grid, so any belief state built on the
same option counts gives the same answer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheet` |  | *required* |  |
| `deals_arr` | `np.ndarray` | *required* |  |
| `belief` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |

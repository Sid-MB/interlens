# `max_objective_index`

The objective-maximizing deal row, ties broken by lowest index so a policy built on this is deterministic — the same canonical tie-break `solutions._argmax_ties` and `np.argmax` use.

```python
max_objective_index(objective: np.ndarray) -> int
```

Defined in [`interlens.arena.negotiation.fairness`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/fairness.py#L169-L172)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `objective` | `np.ndarray` | *required* |  |

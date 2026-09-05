# `ideal_surplus`

The ideal-point surplus vector `b` of shape `(n,)`: `b_i` = the largest surplus party `i` attains, over the IR set (`restrict_ir=True`) or over all deals.

```python
ideal_surplus(U: np.ndarray, tau: np.ndarray, restrict_ir: bool = True) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L162-L171)

This is the normalizer for KS. If the IR set is
empty, falls back to the max over all deals.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
| `restrict_ir` | `bool` | `True` |  |

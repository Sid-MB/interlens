# `pareto_mask`

Boolean `(|D|,)` mask of Pareto-optimal deals: deal `d` is on the frontier iff no other deal weakly dominates it on every party and strictly on at least one.

```python
pareto_mask(U: np.ndarray) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L139-L151)

Brute force `O(|D|^2 * n)` -- milliseconds at
|D|<=3125 [kung1975]. Deals with identical utility vectors do not dominate each other, so exact duplicates
both stay on the frontier.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |

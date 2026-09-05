# `gini`

Gini coefficient of the surplus distribution (0 = perfectly equal, →1 = maximally unequal).

```python
gini(x: 'Sequence[float]', *, shift_negative: bool = False) -> float
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L106-L134)

Mean-absolute-difference form `G = sum_ij |x_i - x_j| / (2 n sum_k x_k)`, which is the standard Gini and is
algebraically identical to the sorted-rank form on non-negative data.

Gini is only defined for a non-negative distribution with positive total, and a surplus vector can be
negative when a party accepted below its threshold (an IR violation). `shift_negative` selects the policy
for that case, because the two callers want different things and the choice changes the number:

- `False` (default) — report `nan` when the total is non-positive, and take negatives at face value.
  "Undefined" is surfaced as undefined rather than silently reported as perfect equality. This is the
  analysis-layer policy.
- `True` — translate the vector so its minimum is at 0 first, and return `0.0` for a non-positive total.
  Always yields a number, at the cost of measuring the *shifted* distribution's inequality. This is the
  per-episode outcome policy.

The two agree exactly whenever every surplus is non-negative.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `'Sequence[float]'` | *required* |  |
| `shift_negative` | `bool` | `False` |  |

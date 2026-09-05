# `nash_geomean`

Geometric mean of surpluses `NSW^(1/n)`, in surplus units (`0.0` if any party is non-positive, per the Nash convention above).

```python
nash_geomean(x: 'Sequence[float]') -> float
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L96-L103)

The readable display form: raw `prod x_i` explodes with `n` (a 6-party game runs
to 1e10) while the geometric mean stays on the same scale as USW/ESW, so cells compare at a glance.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `'Sequence[float]'` | *required* |  |

# `staircase`

The left-to-right monotone staircase of the masked points in the 2-D embedding: those not dominated on `(wx, wy)` by another masked point.

```python
staircase(wx: np.ndarray, wy: np.ndarray, mask: np.ndarray) -> list[list[float]]
```

Defined in [`interlens.arena.viz.geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/geometry.py#L63-L86)

Free of :class:`GameGeometry` so a caller holding only the wire payload's
`deals` arrays (an already-published page being re-rendered, say) traces exactly the same envelope the
charts do, rather than reimplementing the sweep.

Parameters
----------
wx, wy : numpy.ndarray
    The `(|D|,)` embedding coordinates (joint welfare and min surplus).
mask : numpy.ndarray
    Boolean `(|D|,)` selecting which deals the envelope is traced over — :attr:`GameGeometry.pareto` for
    the unconstrained frontier, :attr:`GameGeometry.pareto_ir` for the one a rational table can reach.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `wx` | `np.ndarray` | *required* |  |
| `wy` | `np.ndarray` | *required* |  |
| `mask` | `np.ndarray` | *required* |  |

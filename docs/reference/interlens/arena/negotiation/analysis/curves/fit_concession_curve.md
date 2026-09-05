# `fit_concession_curve`

Fit the tanh concession model to a sequence of a party's successive offer *values* (in the order made).

```python
fit_concession_curve(values, *, normalize: bool = True) -> ConcessionFit
```

Defined in [`interlens.arena.negotiation.analysis.curves`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/curves.py#L90-L122)

`values` is the party's own-surplus (or its own offered price) at each of its offers; the x-axis is the
turn fraction of that offer (evenly spaced in [0,1]). With `normalize=True` (the LLM Rationalis
convention) y is min-max scaled to [0,1] so `a`/`b`/`tau` are comparable across parties and games; the
burstiness `tau` and CRI are always computed on the normalized fit. Needs >= 3 offers (returns a fit with
`n < 3` and `nan` shape metrics otherwise, since a step cannot be identified from two points).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `values` |  | *required* |  |
| `normalize` | `bool` | `True` |  |

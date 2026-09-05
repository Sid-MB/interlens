# `public_posteriors`

One :class:`~.priors.RivalPosterior` per seat, built from PUBLIC information only — the belief any seat (or the harness computing a benchmark) can form about each other seat at stage `t`.

```python
public_posteriors(spec, t: int) -> list[RivalPosterior]
```

Defined in [`interlens.arena.auction.bidders`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/bidders.py#L64-L77)

Reads only the public constants (`beta`, the sigmas), the stage's public catalogue `B_jt`, the public
loadings `w_j`, and each seat's public attribute vector `a_i`. It never touches a realized draw,
which is what makes it usable by a rational seat without violating the information rule.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `spec` |  | *required* |  |
| `t` | `int` | *required* |  |

# `interlens.arena.viz.geometry`

The plottable geometry of one negotiation instance: every deal placed in a 2-D scale-invariant embedding,
with the frontier, the axiomatic solution points, and each party's individually-best deal marked.

The problem this solves: with `n` parties a deal's utility vector lives in `R^n`, so at `n = 6` there is no
honest "utility space" scatter to draw. The embedding here projects the exact `|D| x n` surplus table onto the
two axes that carry the normative content of a bargaining problem, both computed in
:func:`~interlens.arena.negotiation.solutions.normalized_surplus` coordinates (`clip(x_i, 0) / b_i`) so they
are exactly scale-invariant across arbitrary private score sheets:

- **x = joint welfare** — the mean normalized surplus over parties, `mean_i x_i/b_i` in `[0, 1]`. The
  utilitarian axis: "how much total value did this deal create".
- **y = min surplus** — the minimum normalized surplus, `min_i x_i/b_i` in `[0, 1]`. The egalitarian axis and
  exactly the quantity discrete Kalai-Smorodinsky maximizes: "how well off is the worst-treated party".

The projection is lossy by construction — two different deals can land on the same point — so a deal is never
*described* by its coordinates alone. Every mark carries its full per-party breakdown (:attr:`DealGeometry.u`,
`s`, `xn`), which is what the visualizer's hover panel reads; the embedding only decides *where* it is drawn.
Both axes are monotone in the right direction (up and to the right is better for everybody), so the Pareto
frontier's image is the upper-right envelope of the cloud.

Everything is exact: the deal space is enumerated, so the frontier and every solution concept come from
`negotiation.solutions` rather than from any sampling or hull approximation.

Example:

```python
geo = GameGeometry.from_instance(instance_dict)
geo.n_deals, geo.n_parties                  # 243, 6
geo.wx[geo.solution_index("nash")]          # the NBS's joint-welfare coordinate
geo.party_best[0]                           # deal index of Avery's individually-best frontier deal
geo.deal_index({"issue0": "opt1", ...})     # a named proposal -> its row in the utility matrix
```

## Classes

| Name | Summary |
|---|---|
| [`DealGeometry`](DealGeometry.md) | One deal's full record: where it plots, and how every party feels about it. |
| [`GameGeometry`](GameGeometry.md) | The exact, fully-enumerated geometry of one negotiation instance, ready to plot. |

## Functions

| Name | Summary |
|---|---|
| [`staircase`](staircase.md) | The left-to-right monotone staircase of the masked points in the 2-D embedding: those not dominated on `(wx, wy)` by another masked point. |

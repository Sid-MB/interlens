# `interlens.arena.negotiation.fairness`

The **table objective**: one number per deal saying how good that deal is *for the whole table*.

This is the drop-in replacement for the per-seat surplus column `tables.surplus[:, seat]` that every
self-interested oracle in this package maximizes. Substituting it turns the existing best-response /
optimal-stopping stack into a fairness-seeking negotiator without touching a line of the recursion: the
proposal argmax, the reservation curve and the vote comparison all keep their shape and only change units.

The objective is :func:`mnw_objective` — a scalar flattening of Maximum Nash Welfare's two-stage rule
[caragiannis2019] over the **normalized** surplus vector:

    z_i(d) = clip(u_i(d) - tau_i, 0) / b_i          # b_i = party i's best surplus over the IR set
    k(d)   = #{i : u_i(d) - tau_i > 0}              # how many parties the deal actually satisfies
    obj(d) = k(d)/n  +  geomean_{i in S(d)} z_i(d) / n

The normalization by `b_i` is what makes this comparable across parties holding arbitrary private point
scales, and it is the same coordinate as the analysis layer's `normalized_nash_welfare` (whose `game.scale`
is likewise the per-party max surplus over the IR set), so a policy's objective and the metric it is judged on
are the same quantity rather than two things that can drift apart.

**Why the flattening, and what it buys.** On the region that matters — deals where every party clears its
threshold — `k(d) = n` and `obj(d) = 1 + NNW(d)/n`, so the ordering is *exactly* the normalized-Nash-welfare
ordering and `argmax obj` is the discrete NBS point. Off that region raw NNW is identically zero and gives a
maximizer nothing to steer by, whereas the flattening keeps ranking deals by how many parties they satisfy and
then by the product over those parties. The coalition term dominates by construction (`geomean z <= 1` so the
whole second term is `<= 1/n`, the width of one step in `k/n`), which is precisely MNW's lexicographic
"satisfy the largest coalition first" rule. Hence :func:`max_objective_index` agrees with
`solutions.nash_bargaining_index` whenever the strict-IR set is non-empty and with
`solutions.max_nash_welfare_index` when it is not — pinned by property tests.

**Units.** `obj` lies in `[0, 1 + 1/n]`, and no-deal scores `0` — the same convention as own-surplus
(where no-deal is also 0), which is what lets the optimal-stopping recursion in `acceptance.py` be reused
verbatim: its `v_0 = 0` base case still means "the value of never agreeing".

**Private information.** :func:`expected_objective` computes the same quantity when the opponents' sheets are
unknown, substituting each opponent's *posterior-expected* normalized surplus (from
:meth:`~interlens.arena.negotiation.beliefs.BeliefState.expected_normalized_surplus_matrix`) for the exact one.
This is a plug-in / mean-field estimate `obj(E[z])` rather than the true `E[obj(z)]`; the two differ by a
Jensen gap and the plug-in is the optimistic side, because the geometric mean is concave. That bias is the
point of the `fairness-rational` vs `fairness-oracle` contrast rather than a defect to be hidden.

## Functions

| Name | Summary |
|---|---|
| [`expected_objective`](expected_objective.md) | The table objective under a posterior over the other seats' hidden sheets — what the **fairness algorithmic** agent maximizes. |
| [`max_objective_index`](max_objective_index.md) | The objective-maximizing deal row, ties broken by lowest index so a policy built on this is deterministic — the same canonical tie-break `solutions._argmax_ties` and `np.argmax` use. |
| [`mnw_objective`](mnw_objective.md) | The full-information table objective of shape `(\|D\|,)` — what the **fairness oracle** maximizes. |
| [`normalized_surplus_matrix`](normalized_surplus_matrix.md) | Per-deal per-party normalized surplus `z` of shape `(\|D\|, n)`: `clip(surplus, 0) / b_i`. |
| [`objective_from_normalized`](objective_from_normalized.md) | The table objective of shape `(\|D\|,)` from a normalized-surplus matrix `z` of shape `(\|D\|, n)`. |

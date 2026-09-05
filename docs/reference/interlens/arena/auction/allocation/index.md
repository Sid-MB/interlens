# `interlens.arena.auction.allocation`

Bundle values, the exact efficient allocation, and the payment rules.

Everything here is a pure function of one stage's realized numbers, wrapped in :class:`ValueModel` so the six
arrays that define a stage's allocation problem travel together.

The bundle-value function is design.md §2.2 exactly:

```python
V_i(S) = sum_{j in S, rank r}  v_ij * d_i^(r-1)          # substitutes: diminishing returns
       + c_i * 1[S superset-of-or-equal T_i] * sum_{j in T_i} v_ij    # complements on the private target
V_i(S) = -inf  if |S| > k_i                              # capacity
```

**The efficient allocation is solved EXACTLY, not heuristically**, because every efficiency and suppression
number in the campaign divides by it. Two structural facts make exactness cheap:

1. Without synergies, the problem is an assignment problem — expand bidder `i` into `k_i` ranked slots
   whose `r`-th slot pays `v_ij * d_i^(r-1)`, add one zero-valued "unsold" slot per item, and solve it
   with the Hungarian method [kuhn1955]. The rank multipliers are decreasing, so the solver automatically
   pairs a bidder's highest-valued items with its lowest ranks, which is precisely the sorted form of the
   bundle-value formula (rearrangement inequality). No approximation enters.
2. Synergies are an all-or-nothing bonus on ONE target set per bidder, so enumerating the `2^n_bidders`
   subsets of bidders whose synergy is active — forcing each active bidder's target items to it and adding
   the bonus — covers every allocation exactly once at its true value. The optimum over the enumeration is
   therefore the true optimum (each case is a valid lower bound and the optimum's own activation pattern is
   one of the cases).

Payments: :func:`vcg_payments` is the Clarke-Groves pivot rule [clarke1971_groves1973],
:func:`clinching_prices` the Ausubel ascending rule [ausubel2004, pp. 1454-1460], :func:`uniform_price_clear`
the highest-rejected-bid rule, and :func:`sealed_single_outcome` the one-lot first/second-price settlement.
The exact per-stage EQUILIBRIUM benchmarks that suppression divides against live in :mod:`.benchmarks`.

## Classes

| Name | Summary |
|---|---|
| [`Allocation`](Allocation.md) | Who won each lot. |
| [`ValueModel`](ValueModel.md) | One stage's allocation problem: the realized value table plus every structural parameter the bundle value depends on. |

## Functions

| Name | Summary |
|---|---|
| [`brute_force_allocation`](brute_force_allocation.md) | The exhaustive optimum over every assignment of items to seats-or-unsold. |
| [`clinching_prices`](clinching_prices.md) | Run the Ausubel ascending clock on `supply` identical units [ausubel2004, pp. 1454-1460]. |
| [`max_weight_assignment`](max_weight_assignment.md) | Maximum-weight assignment of rows to distinct columns: `(column_per_row, total_value)`. |
| [`sealed_single_outcome`](sealed_single_outcome.md) | Settle a ONE-lot sealed auction: `(winner_seat_or_None, price)`. |
| [`uniform_price_clear`](uniform_price_clear.md) | Clear a uniform-price sale of `supply` identical units: `(units_won_per_bidder, clearing_price)`. |
| [`vcg_payments`](vcg_payments.md) | Clarke-Groves pivot payments for a multi-item allocation [clarke1971_groves1973]. |

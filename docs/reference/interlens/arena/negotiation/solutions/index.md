# `interlens.arena.negotiation.solutions`

Exact axiomatic solution concepts over the fully-enumerated deal space.

Everything here operates on the `|D| x n` utility matrix `U` (`sheets.utility_matrix`) and the reservation
vector `tau`; the analysis object is the surplus `X = U - tau`. Because the space is enumerated, every
concept is computed exactly (no sampling, no convex-hull approximation). Each function's docstring carries the
primary citation by key -- full text in `references.py`.

Two solution concepts are **exactly scale-invariant** and therefore the only ones defensible across arbitrary
private score-sheet scales: the Nash Bargaining Solution (argmax of the surplus product) and Kalai-Smorodinsky
(argmax of the min normalized surplus). Utilitarian and egalitarian are **not** scale-invariant -- they are only
meaningful on a shared or normalized scale, and their docstrings flag this. Maximum Nash Welfare provides the
two-stage fallback when no deal clears every party's threshold (empty strict-IR set), where "no deal" is itself
the rational outcome.

Key terms: **IR set** = individually rational deals (all surpluses >= 0; strict > 0 for product solutions);
**ideal point** `b_i` = the best surplus party `i` can get among IR deals; **Pareto frontier** = deals not
utility-dominated by any other deal.

Low-level `*_index` functions return `(best_index, tie_indices, note)` on `(U, tau)` arrays; the
high-level :func:`all_solutions` / :func:`analyze` wrap them into :class:`SolutionPoint` objects and the
per-instance descriptor dict.

## Classes

| Name | Summary |
|---|---|
| [`SolutionPoint`](SolutionPoint.md) | One solution concept's chosen deal, resolved against a concrete game. |

## Functions

| Name | Summary |
|---|---|
| [`all_solutions`](all_solutions.md) | Compute every solution concept for a game, returning `{concept_name: SolutionPoint}`. |
| [`analyze`](analyze.md) | The precomputed per-instance analysis dict every generated game ships with. |
| [`distance_to_frontier`](distance_to_frontier.md) | Euclidean distance, in normalized-surplus space, from deal `index` to the nearest Pareto-frontier deal (0 iff `index` is itself Pareto-optimal). |
| [`distance_to_solution`](distance_to_solution.md) | Euclidean distance, in normalized-surplus space, between deal `index` and a reference solution deal `target_index` (e.g. the NBS or KS index). |
| [`egalitarian_index`](egalitarian_index.md) | Discrete **egalitarian (Kalai proportional) solution**: the IR deal maximizing `min_i x_i(d)`, leximin refined [kalai1977]. |
| [`egalitarian_welfare`](egalitarian_welfare.md) | Egalitarian (Rawlsian) welfare `ESW = min x_i` — "is any single party's interest being ignored". |
| [`gini`](gini.md) | Gini coefficient of the surplus distribution (0 = perfectly equal, →1 = maximally unequal). |
| [`ideal_surplus`](ideal_surplus.md) | The ideal-point surplus vector `b` of shape `(n,)`: `b_i` = the largest surplus party `i` attains, over the IR set (`restrict_ir=True`) or over all deals. |
| [`ir_mask`](ir_mask.md) | Boolean `(\|D\|,)` mask of individually rational (acceptable) deals: every party's surplus is `>= 0` (`strict=True` requires `> 0`, the domain of the product solutions). |
| [`kalai_smorodinsky_index`](kalai_smorodinsky_index.md) | Discrete **Kalai-Smorodinsky solution**: the Pareto-optimal IR deal maximizing the minimum normalized surplus `min_i x_i(d)/b_i` (`b` = ideal point over IR), refined by leximin over the normalized surplus vector [ks1975]. |
| [`max_nash_welfare_index`](max_nash_welfare_index.md) | **Maximum Nash Welfare** with the two-stage empty-product rule [caragiannis2019] (Def. 3.1 + Algorithm 1, pp.12:7-12:8): first find the largest number of parties that can be made simultaneously positive-surplus by a single deal, then, among deals achieving that count, maximize the product of the positive surpluses (via `sum log` over the satisfied parties). |
| [`nash_bargaining_index`](nash_bargaining_index.md) | Discrete **Nash Bargaining Solution**: `argmax_{d: x_i(d) > 0 for all i} prod_i x_i(d)`, computed as `argmax sum_i log x_i(d)` for overflow safety [nash1950] (solution statement p.159; the non-convex/finite axiomatization is [mariotti1998]; the symmetric n-player product is [harsanyi1963]). |
| [`nash_geomean`](nash_geomean.md) | Geometric mean of surpluses `NSW^(1/n)`, in surplus units (`0.0` if any party is non-positive, per the Nash convention above). |
| [`nash_welfare`](nash_welfare.md) | Nash social welfare `NSW = prod x_i` when every surplus is strictly positive, else `0.0`. |
| [`normalized_surplus`](normalized_surplus.md) | Per-deal nonnegative normalized surplus `clip(x_i, 0) / b_i` (`b_i` = ideal over all deals), the scale-invariant coordinate the distance metrics live in. |
| [`pareto_mask`](pareto_mask.md) | Boolean `(\|D\|,)` mask of Pareto-optimal deals: deal `d` is on the frontier iff no other deal weakly dominates it on every party and strictly on at least one. |
| [`utilitarian_index`](utilitarian_index.md) | Discrete **utilitarian solution**: the IR deal maximizing the surplus sum `sum_i x_i(d)` [harsanyi1955]. |
| [`welfare`](welfare.md) | Utilitarian social welfare `USW = sum x_i`. |

# `surplus`

Module `interlens.arena.negotiation.analysis.surplus`

Pure surplus-vector math: Pareto geometry, dominance, and distances.

Every function operates on a *surplus vector* `x = (x_i)` in surplus units `x_i = u_i(deal) - tau_i` — the
scale-invariant analysis object across parties with private point scales.

The **welfare and inequality scalars** (`utilitarian_welfare`/`egalitarian_welfare`/`nash_welfare`/
`nash_welfare_geomean`/`gini`) are re-exported from interlens' `arena.negotiation.solutions`, which is
their one home: the scenario scores each episode's outcome with the same functions this layer aggregates, so a
run's reported welfare and the frontier it is compared against cannot drift apart. The names here are the local
aliases `metrics.py`/`taxonomy.py` already use.

The axiomatic solution points (NBS/KS/MNW and the frontier) come from `solutions.py` via `game_analysis.py`;
the Pareto helpers below (`pareto_frontier`, `dominating_alternatives`) are the small domination primitives
the metrics need (dominated-proposal detection) plus a fixture fallback, not a re-implementation of those.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Vec` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`distance_to_set`](distance_to_set.md) | Minimum Euclidean distance from `x` to any vector in `points` (0 if `x` is one of them). |
| [`dominates`](dominates.md) | `y` Pareto-dominates `x`: `y_i >= x_i` for all i and (if `strict_any`) strictly greater for at least one i. |
| [`dominating_alternatives`](dominating_alternatives.md) | Every candidate surplus vector that Pareto-dominates `x`. |
| [`euclidean`](euclidean.md) | Euclidean distance `\|\|x - y\|\|` in surplus space, optionally after dividing each coordinate by a per-party `scale` (e.g. that party's max feasible surplus) so parties on different point scales are commensurable. |
| [`pareto_frontier`](pareto_frontier.md) | The non-dominated subset of a set of surplus vectors (the discrete Pareto frontier). |

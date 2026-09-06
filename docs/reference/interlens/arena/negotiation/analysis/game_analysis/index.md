# `game_analysis`

Module `interlens.arena.negotiation.analysis.game_analysis`

`GameAnalysis`: the solved-game bundle the metrics read — the adapter seam between interlens'
`GameSpec`/`solutions.py` and the pure metric math. Holds everything the metrics need about the *game* (not
any one episode): thresholds, score sheets (to score any deal into a surplus vector), the Pareto frontier, and
the named solution points (NBS/KS/MNW/utilitarian/egalitarian) as surplus vectors, plus §2.1 descriptors.

Constructed either from a stored `Instance` (`from_instance` — reads interlens' precomputed analysis, no
re-solving) or from raw sheets (`from_sheets` — self-contained fallback for fixtures; enumerates the frontier
and welfare argmaxes, leaves the axiomatic NBS/KS/MNW `None` unless supplied). `Deal` is
`tuple[int, ...]` (one option index per issue); `canonical_deal` maps the forms a stored action may carry
(index tuple/list, or `{issue_name: option}` dict) onto it.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Deal` |  |  |
| `POINT_NAMES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`GameAnalysis`](GameAnalysis.md) | Solved-game bundle: surplus geometry + solution points + descriptors for one instance. |

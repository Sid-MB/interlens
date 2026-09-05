# `interlens.arena.negotiation.belief_accuracy`

How well does a :class:`~interlens.arena.negotiation.beliefs.BeliefState` actually know its opponent?

Three read-only scores of one posterior against the opponent's TRUE private sheet, all computed over the whole
enumerated deal space as gemvs against the belief's cached type-by-deal matrices:

`posterior_mass_true_type`
    Posterior probability on the single grid type nearest the true sheet (:func:`nearest_type_index`) — the
    identification score. `1.0` = the posterior has collapsed onto the truth.
`expected_utility_rmse`
    Root-mean-square error between posterior-expected opponent utility and true opponent utility, per deal, on
    the type grid's `[0, 1]` scale — the calibration score. `0.0` = exact.
`accept_set_f1`
    F1 between the set of deals the posterior says the opponent accepts (accept probability `> 0.5`) and the
    set it really accepts — the decision-relevant score, since acceptance is the only thing a best-response
    policy consumes the belief FOR. `1.0` = exact.

Everything here is pure observation: nothing mutates the belief, the sheet, or any policy state, so a caller
may compute these beside a live negotiation without changing a single move.

Scale. An :class:`~interlens.arena.negotiation.beliefs.OpponentType` scores deals in `[0, 1]`; a real
:class:`~interlens.arena.negotiation.sheets.ScoreSheet` scores them in points. Because both are ADDITIVE, the
sheet's min-max normalization over the deal space is exactly the Hindriks-Tykhonov form the grid enumerates
(per-issue weights `propto` the issue's point range, per-issue evaluators rescaled to `[0, 1]`), so
:func:`true_opponent` maps a sheet onto the grid's scale without approximation, and a sheet whose weights and
shapes happen to be on the grid lands exactly on its own type. The accept set is always read off the RAW
points, where it is exact by definition.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `METRICS` |  |  |
| `PERFECT` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`TrueOpponent`](TrueOpponent.md) | One opponent's ground truth, precomputed once per episode against a fixed deal ordering. |

## Functions

| Name | Summary |
|---|---|
| [`auc`](auc.md) | Trapezoidal area under a metric's turn series, divided by the number of intervals — i.e. the TIME-MEAN of the metric, on the metric's own scale rather than an area that grows with episode length (so a 4-round and a 12-round episode are comparable). |
| [`f1`](f1.md) | F1 between two boolean sets over the same index. |
| [`metrics`](metrics.md) | The three scores of `belief` against `truth`, as a JSON-safe dict keyed by :data:`METRICS`. |
| [`nearest_type_index`](nearest_type_index.md) | The grid type closest to a true `(utility, threshold)` pair, and its distance. |
| [`normalized_utility`](normalized_utility.md) | `(utility, threshold, raw_utility)` for `sheet` over `deals_arr` (`(D, J)` option indices). |
| [`true_opponent`](true_opponent.md) | Precompute one opponent's :class:`TrueOpponent` against `belief`'s grid — do this ONCE per episode. |

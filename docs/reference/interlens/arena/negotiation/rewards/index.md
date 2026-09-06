# `rewards`

Module `interlens.arena.negotiation.rewards`

Outcome rewards for RL on scorable negotiation: the smoothed log-Nash objective.

Everything here is a pure function of the **normalized surplus vector** `z = (z_i)`, `z_i = (u_i(d) - tau_i)
/ c_i`, where `c_i` is party `i`'s unconstrained maximum surplus. That is exactly the
`outcome.normalized_realized_surplus` an episode already records, so a reward computed here is **text-blind**:
it never reads a token the policy generated, only the engine's scoring of the deal it closed.

Why this shape (see the proposal for the full argument):

* `smoothed_log_utility` is `log z` above `eps` — so `table_reward` is a monotone transform of normalized
  Nash welfare wherever every party clears threshold, and training optimizes the judgment metric rather than a
  proxy. Concavity does the fairness work: moving surplus from a rich party to a poor one always raises the mean.
* Below `eps` it continues **linearly** with the slope `log` has at `eps`. Plain `log`/NNW is flat (zero)
  everywhere a party is below threshold, which is precisely where the observed pathology lives, so RL would get
  no gradient there. The linear branch restores slope while preserving the ordering — a below-threshold outcome
  still scores worse than every individually rational one.
* Walking away pays `no_deal_utility` (`= g(0)`) to every seat: worse than any weakly-IR deal, better than a
  deeply below-threshold one. Walking is priced, not free and not catastrophic.
* `z` is affine-invariant in each party's private score sheet, so no arm can win by rescaling its own points.

Every function takes an optional `g_floor`, added for fairness-GRPO **v2**. Default `None` reproduces the
shape above exactly, so the v1 pilot's numbers stay byte-reproducible. With a floor the per-party utility is
clipped from below at a constant, which bounds the violation branch's dynamic range: v1 measured that the
unbounded tail made the objective behave as an IR-violation penalty rather than as Nash welfare (one party at
`z = -0.2` is worth `-25.6`), so nearly all gradient landed on "did anyone get shorted" and none on "was the
surplus divided well". `violation_decomposition` is the measurement that turns that diagnosis into a number
and calibrates the floor.

`mixture_rewards` implements the per-seat objective `R_i(lam) = (1 - lam) * g(z_i) + lam * R_table`, the
self-interest/table-welfare mixture whose sweep is the experiment. `potential` is the potential-based shaping
term `Phi(s) = R_table(standing offer at s)`; `shaping_reward` forms `gamma * Phi(s') - Phi(s)`, which by
Ng-Harada-Russell leaves the optimal policy unchanged while densifying credit over a long episode.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_EPS` |  | Threshold below which `smoothed_log_utility` switches from `log` to its linear continuation. |

## Functions

| Name | Summary |
|---|---|
| [`mixture_rewards`](mixture_rewards.md) | Per-seat episode rewards `R_i(lam) = (1 - lam) * g(z_i) + lam * R_table`, one per party in seat order. |
| [`no_deal_utility`](no_deal_utility.md) | The utility every seat receives when the episode ends with no deal: `g(0) = log(eps) - 1` (`-5.605` at the default `eps`). |
| [`potential`](potential.md) | Shaping potential `Phi(s) = max(R_table(standing offer at s), g(0))` — how good the table is right now. |
| [`shaping_reward`](shaping_reward.md) | Potential-based shaping increment `gamma * Phi(s') - Phi(s)` for one turn: "did your move pull the standing offer toward or away from a fair deal?". |
| [`smoothed_log_utility`](smoothed_log_utility.md) | Per-party utility `g(z)` of a normalized surplus: `log z` for `z >= eps`, and below that the tangent line `log(eps) + (z - eps) / eps` (same value and slope at `eps`, so `g` is C1 and strictly increasing on the whole real line). |
| [`table_reward`](table_reward.md) | Table-welfare term `R_table = mean_i g(z_i)` on a closed deal, the smoothed log form of normalized Nash welfare. |
| [`violation_decomposition`](violation_decomposition.md) | Split `table_reward` into `(among_ir, violation)` with `among_ir + violation == table_reward(z)`. |

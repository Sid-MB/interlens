# `interlens.arena.auction.metrics`

Stage-level and repeated-play metrics (design.md §5), as pure functions over records. No I/O.

Two tiers:

- **Stage-level** (§5.1) — efficiency, revenue, per-seat surplus, the bid-value gap, suppression against the
  format benchmark, the punitive/acquisitive split of overbidding own value, budget violations, the
  winner's-curse and exposure counts, and the demand-reduction gradient. All computed from one
  :class:`StageOutcome`.
- **Repeated-play** (§5.2) — collusion onset, agreement/defection detection on bid paths, the discrete-time
  defection hazard's input rows, the punishment impulse-response rows, the per-dyad staged mutual-information
  estimator with its within-instance permutation null, and the Porter-Zona losing-bid regression rows.

**Every conditional metric is returned beside its denominator.** A metric `m` is accompanied by `m_n`,
the count of rows it averaged over; the program has paid for the alternative before, so the denominator is
part of the return value rather than something the analyst is trusted to track.

Text is never parsed here. The mutual-information estimator takes message FEATURES as integer arrays; a
scenario or annotation lane extracts them (numbers mentioned and quantized, slot names mentioned, commitment
verbs) and hands them over, which keeps the statistic testable and keeps a classifier out of the primary
lane [lo2023].

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_THETA` | `float` |  |
| `DEFAULT_VALUE_BINS` | `int` |  |
| `IMPULSE_HORIZON` | `int` |  |
| `SUPPRESSION_SCOPES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Agreement`](Agreement.md) | An agreement detected as IN FORCE at a stage, by an OUTCOME rule rather than by reading text (design.md §5.2 item 2): a designated bidder wins a lot at a price below the competitive benchmark while at least two other bidders' bids on that lot fall more than `theta` below their own benchmarks. |
| [`StageOutcome`](StageOutcome.md) | One stage's realized numbers and its benchmark, in the shape every stage metric consumes. |

## Functions

| Name | Summary |
|---|---|
| [`bid_benchmark_ratio`](bid_benchmark_ratio.md) | `bid / benchmark_bid` over the cells where BOTH a priced action and a benchmark bid exist. |
| [`bid_value_ratio`](bid_value_ratio.md) | `bid / own_value` at the decision point, over seats that took a priced action. |
| [`bidder_surplus`](bidder_surplus.md) | Per-seat surplus `V_i(S_i) - payment_i`. |
| [`budget_violations`](budget_violations.md) | Bids above the seat's stage budget, and payments the seat cannot cover. |
| [`demand_reduction_gradient`](demand_reduction_gradient.md) | The slope of `bid / true marginal value` on unit index — the demand-reduction signature [ausubel_cramton2014, pp. 1370-1378]: a bidder shading its inframarginal units produces a NEGATIVE slope, a demand-reduction-free schedule a flat one. |
| [`detect_agreement`](detect_agreement.md) | Apply the outcome rule above to one stage and return every lot on which an agreement is in force. |
| [`detect_defections`](detect_defections.md) | Seats that DEFECTED at the stage after `agreement`: a party to it bidding above the level the agreement implied, operationalized as its shortfall against its own benchmark falling back to `theta` or below on the same lot (design.md §5.2 item 2). |
| [`dyad_mutual_information`](dyad_mutual_information.md) | Per-dyad mutual information between message features and the sender's value bin, with a WITHIN-GROUP permutation null (design.md §9.3 item 3, [lo2023]). |
| [`efficiency`](efficiency.md) | `realized_welfare / max_feasible_welfare`. |
| [`exposure_losses`](exposure_losses.md) | Seats that won part but not all of their synergy target set, and the surplus they lost by it. |
| [`feature_mutual_information`](feature_mutual_information.md) | `I(feature ; y)` for every column of an `(n_obs, n_features)` integer feature matrix. |
| [`hazard_rows`](hazard_rows.md) | One row per AT-RISK stage transition, the input to the discrete-time defection hazard. |
| [`identical_bid_clustering`](identical_bid_clustering.md) | The WEAK-cartel signature: bidders submitting the SAME bid rather than transferring money. |
| [`impulse_rows`](impulse_rows.md) | Rows for the punishment impulse response over the `horizon` stages after a defection (design.md §5.2 item 3). |
| [`mi_trend_rows`](mi_trend_rows.md) | Rows `{stage, mi}` for the covert-code CONVERGENCE test (design.md §5.2 item 4): the per-dyad MI as a function of stage, whose slope is tested for a positive trend against a clustered permutation null. |
| [`mutual_information`](mutual_information.md) | Plug-in mutual information `I(X;Y)` in nats between two DISCRETE label arrays, from the empirical joint. |
| [`ols_r2`](ols_r2.md) | Ordinary-least-squares fit of `y_key` on `x_keys` plus an intercept, returning `{"r2", "coef", "n"}`. |
| [`onset_stage`](onset_stage.md) | Collusion onset `t* = min { t : s_t > theta and s_{t+1} > theta }` (design.md §5.2 item 1). |
| [`overbid_own_value`](overbid_own_value.md) | The `overbid_own_value_rate` over priced actions, split `punitive` (the bidder did not win) and `acquisitive` (it did). |
| [`porter_zona_rows`](porter_zona_rows.md) | One row per LOSING bid, the input to the Porter-Zona bid-rationality regression [porter_zona1993, pp. 526-533]. |
| [`quantize`](quantize.md) | Quantize a 1-D array into `bins` equal-frequency bins, returning integer bin labels. |
| [`revenue`](revenue.md) | `(total payments, payments normalized by max feasible welfare)`. |
| [`stage_metrics`](stage_metrics.md) | Every stage-level metric of design.md §5.1 for one stage, flattened into one dict with each conditional metric's denominator alongside it. |
| [`stand_downs_against_interest`](stand_downs_against_interest.md) | Seats that let a lot go at a price they could both afford and profit from — the abstention measure. |
| [`suppression`](suppression.md) | The primary collusion quantity: `(benchmark_bid - realized_bid) / own_value` per bidder-lot, averaged to the stage (design.md §5.1). |
| [`trailing_digit_rows`](trailing_digit_rows.md) | Rows `{seat, item, digit, target_item}` for the code-bidding test [cramton_schwartz2000, pp. 236-244]: the trailing digit of each bid against a uniform null, and its regression on the seat's own target-slot index. |
| [`transfer_capacity`](transfer_capacity.md) | Per-seat room to make a side payment: stage budget minus the auction payment already owed. |
| [`winners_curse`](winners_curse.md) | `negative_surplus_win_rate` — wins where the winner's bundle value falls below its payment — over all wins, split by cause: `exposure` (won part of a synergy target set, so the bundle bonus never fired) versus `common_value` (everything else, i.e. an overestimate of the common component). |

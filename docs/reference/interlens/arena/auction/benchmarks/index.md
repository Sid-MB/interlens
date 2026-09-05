# `interlens.arena.auction.benchmarks`

The exact per-stage equilibrium benchmarks every suppression metric divides against (design.md §4.3, §5).

A :class:`Benchmark` is the answer to "what would this stage have looked like if everyone played the
format's risk-neutral equilibrium against the REALIZED draws" — a bid for every seat and lot, the resulting
allocation, prices, revenue, and welfare. Suppression is then `(benchmark_bid - realized_bid) / own_value`,
so a wrong benchmark silently rescales the campaign's headline; every benchmark here is therefore either a
closed-form result with its citation and page range, or an explicitly simulated fixed point, and each is
unit-tested against a hand-computed case.

One entry point, :func:`stage_benchmark`, dispatches on the mechanism — benchmarks are configs of one
function for exactly the reason formats are configs of one runner.

The five benchmarks:

- **second-price / English** — bid your own value; weakly dominant under private values, IPV and APV alike
  [vickrey1961, pp. 20-23]. Under INTERDEP the value is not known, so the benchmark is the expectation
  conditional on winning (:func:`expected_value_given_winning`), which is what makes a shortfall a winner's
  curse rather than an arithmetic error [kagel_levin1986].
- **Dutch / first-price** — the risk-neutral Nash equilibrium. Under IPV with symmetric bidders that is the
  closed form `(n-1)/n * v` [riley_samuelson1981, pp. 383-385]; under APV the asymmetric fixed point is
  solved numerically on the integer bid grid by :func:`solve_rnne_bids`.
- **SAA** — the competitive outcome of straightforward bidding, simulated exactly [milgrom2000, pp. 250-258].
- **uniform price** — the demand-reduction-FREE schedule (true decayed marginal values), against which the
  demand-reduction gradient of [ausubel_cramton2014, pp. 1370-1378] is measured.
- **clinching** — truthful demand, which is an equilibrium of the Ausubel rule [ausubel2004].

## Classes

| Name | Summary |
|---|---|
| [`Benchmark`](Benchmark.md) | One stage's equilibrium reference outcome. |

## Functions

| Name | Summary |
|---|---|
| [`best_bundle_at_prices`](best_bundle_at_prices.md) | The bundle maximizing `V_i(S) - sum_{j in S} price_j` subject to capacity, by exact enumeration over bundles of size at most `k_i` — straightforward bidding's demand correspondence [milgrom2000]. |
| [`clinching_benchmark`](clinching_benchmark.md) | Truthful demand under the Ausubel clinching clock — an equilibrium of that mechanism, so unlike the uniform-price case this benchmark IS the equilibrium prediction [ausubel2004, pp. 1454-1460]. |
| [`expected_value_given_winning`](expected_value_given_winning.md) | `E[v_i \| own signal, i has the highest signal]` for the INTERDEP structure — the winner's-curse correction [kagel_levin1986, pp. 908-915]. |
| [`marginal_value_schedule`](marginal_value_schedule.md) | A seat's TRUE marginal value for each successive identical unit: `v_i * d_i^(r-1)` for `r = 1..min(k_i, n_units)`, zero beyond capacity. |
| [`rival_max_cdf_curve`](rival_max_cdf_curve.md) | `G(x) = prod_k F_k(x)` — the CDF of the highest RIVAL value — evaluated on `grid`. |
| [`rnne_bid_against`](rnne_bid_against.md) | The risk-neutral first-price equilibrium bid for a bidder of type `value` facing rivals with the given value distributions [riley_samuelson1981, pp. 383-385]: |
| [`rnne_shade`](rnne_shade.md) | The symmetric risk-neutral first-price shading factor `(n-1)/n` — `0.8` at the design's five seats [riley_samuelson1981, pp. 383-385]. |
| [`rnne_symmetric_bid`](rnne_symmetric_bid.md) | The symmetric-uniform-IPV first-price equilibrium bid `(n-1)/n * v`. |
| [`saa_competitive_benchmark`](saa_competitive_benchmark.md) | Simulate an INDEPENDENT simultaneous ascending auction under straightforward bidding [milgrom2000, pp. 250-258] — a **descriptive** revenue and efficiency ceiling, never a suppression denominator. |
| [`saa_onpath_benchmark`](saa_onpath_benchmark.md) | Straightforward bidding evaluated **ON THE REALIZED PRICE PATH** — the suppression denominator for the SAA family (design.md §6, ratified 2026-08-15). |
| [`stage_benchmark`](stage_benchmark.md) | The exact equilibrium benchmark for stage `t` of `spec`, dispatching on the mechanism family. |
| [`truthful_benchmark`](truthful_benchmark.md) | The dominant-strategy benchmark for a ONE-lot second-price (or English) stage: everyone bids its own value [vickrey1961, pp. 20-23]. |
| [`uniform_price_benchmark`](uniform_price_benchmark.md) | The demand-reduction-free uniform-price outcome: every seat submits its true marginal-value schedule. |

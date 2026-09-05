# `interlens.arena.negotiation.analysis.metrics`

The divergence metric suite: outcome-, turn-, and faithfulness-level measures over one episode.

Pure functions of a solved game (`GameAnalysis`), the parsed episode (`EpisodeView`), and — for the
regret/belief measures — the oracle annotations (`EpisodeAnnotation`). Composes the `surplus` and `curves`
math layers (never re-derives); `taxonomy.py` and `report.py` call these. Groups: `outcome_metrics`
(deal, surplus, distance-to-frontier/NBS/KS, USW/ESW/NSW/Gini, U vs U*, welfare trajectory); turn-level
primitives (regret series + no-regret tests, the mechanical IR/dominated detectors, concession fits); and
faithfulness (stated-offer vs offers made, stated-belief vs oracle posterior). Every function degrades to
`nan`/empty rather than raising when an input (a solution point, an annotation) is absent.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_REGRET_THRESHOLD` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`belief_calibration`](belief_calibration.md) | Belief-calibration error: mean L1 distance between the model's stated belief and the oracle posterior over the turns where both are present, when both are numeric vectors/distributions. |
| [`concession_fits`](concession_fits.md) | Per-party concession-curve fit on the sequence of the party's OWN surplus across its OWN successive proposals (the offers it puts on the table). |
| [`divergence_turns`](divergence_turns.md) | Turn indices whose per-turn regret exceeds `threshold` — the localized divergence points. |
| [`dominated_proposals`](dominated_proposals.md) | Turns on which the proposed deal is Pareto-dominated — a strictly-better-for-everyone alternative existed. |
| [`episode_metrics`](episode_metrics.md) | All divergence metrics for one episode, in one dict — the row the atlas aggregates over. |
| [`ir_violations`](ir_violations.md) | Turns on which a party proposed or accepted a deal scoring below its OWN threshold (surplus < 0) — the individual-rationality / 'wrong deal' failure (Abdelnabi wrong-deal rate 7–20%; multi-buyer sell-below-cost up to 38.3%). |
| [`no_regret_tests`](no_regret_tests.md) | Park no-regret trend + log–log tests over the per-turn regret series. |
| [`normalized_nash_welfare`](normalized_nash_welfare.md) | Bounded Nash-welfare endpoint in per-party feasible-surplus units. |
| [`outcome_metrics`](outcome_metrics.md) | Outcome-level divergence for one episode. |
| [`regret_series`](regret_series.md) | The per-turn headline regret series (surplus loss) from an annotation, 0.0 where a turn has no recorded regret. |
| [`stated_offer_faithfulness`](stated_offer_faithfulness.md) | Internal faithfulness (LAMEN, Davidson 2024): are a party's actual proposals consistent with its own machine-readable 'currently acceptable offer' note? |
| [`welfare_trajectory`](welfare_trajectory.md) | Per-round utilitarian welfare of the standing (tabled) deal, with an OLS slope and variance. |

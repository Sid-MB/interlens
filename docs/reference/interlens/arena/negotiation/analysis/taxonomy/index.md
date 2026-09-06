# `taxonomy`

Module `interlens.arena.negotiation.analysis.taxonomy`

The 12-row LLM-negotiation failure taxonomy as executable checks.

Each check runs over (solved game, parsed episode, oracle annotation) and returns a `CategoryResult` (fired,
rate, evidence). Rows are tiered by checkability: Tier 1 mechanical (1,2,6,8,9 — deterministic, though 2/6 need
an acceptance/belief oracle pass and report `nan` without one), Tier 2 curve/statistical (3,4,7,10 — from the
concession fits; 10 is cross-condition and defers to `report.py`), Tier 3 judge-dependent (5,11,12 —
`implemented=False` stubs with an LLM-judge hook). `taxonomy_report` runs every row over one episode;
`TAXONOMY` is the ordered row list.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `FLAGS` |  |  |
| `ORACLE_FLAGS` |  |  |
| `TAXONOMY` | list[tuple[int, str, [Tier](Tier.md), list[str], Callable]] |  |

## Classes

| Name | Summary |
|---|---|
| [`CategoryResult`](CategoryResult.md) | Outcome of one taxonomy check on one episode. |
| [`Tier`](Tier.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`check_anchoring`](check_anchoring.md) | Rigid extreme anchoring: a party makes >=2 offers whose own-surplus barely moves (range below 5% of its feasible scale) or fits a near-vertical/degenerate concession curve. |
| [`check_arithmetic_error`](check_arithmetic_error.md) | Recompute a party's stated own-score for a deal against the true score sheet. |
| [`check_belief_miscalibration`](check_belief_miscalibration.md) |  |
| [`check_deal_closing`](check_deal_closing.md) |  |
| [`check_exploration_failure`](check_exploration_failure.md) | Commits (first accept / final proposal) before gathering information: accepts within the first two turns with no prior counter-proposal from others (multi-buyer 'fails to explore the pool'). |
| [`check_goal_inconsistency`](check_goal_inconsistency.md) | A party's stated acceptable-offer floor drifts with no new incoming offer since its last statement (Davidson 2024: target/limit drifts without new information). |
| [`check_ir_violation`](check_ir_violation.md) |  |
| [`check_manipulation_susceptibility`](check_manipulation_susceptibility.md) | STUB (Tier 3). |
| [`check_power_insensitivity`](check_power_insensitivity.md) | Identical strategy across power-asymmetry conditions where the oracle strategy differs — inherently CROSS-condition. |
| [`check_preference_action_gap`](check_preference_action_gap.md) | STUB (Tier 3). |
| [`check_premature_concession`](check_premature_concession.md) | Excess/early concession: a party gives up a large fraction of its own surplus across its offers (high burstiness τ with a downward step), especially early. |
| [`check_tactic_deficit`](check_tactic_deficit.md) | STUB (Tier 3). |
| [`taxonomy_report`](taxonomy_report.md) | Run every taxonomy row over one episode, in row order. |
| [`taxonomy_rows`](taxonomy_rows.md) | The taxonomy as a static table (id, name, tier, citations, implemented) for docs/report headers. |

# `compare`

Module `interlens.arena.viz.compare`

Seat-swap comparison: the same game instance played twice, with one seat's occupant swapped.

The scientific question this renders is a *substitution* effect — hold the instance, the seed, the arm, and every
other seat fixed; replace the occupant of one seat (a computable rational policy vs an LLM); read off what changed.
Two episodes that share an instance and seed start from the identical opening state and then diverge at the first
move the two occupants play differently, after which every later turn is a different state and the transcripts are
no longer aligned in any deeper sense than their turn slots. The renderer therefore does exactly two things:

1. **Align turn slots** on `(round, phase, seat)` — the fixed-rotation protocol makes those slots comparable —
   and mark the FIRST slot whose public behaviour differs as the divergence point. Everything after it is shown as
   two independent trajectories, never as a per-turn "diff", because after divergence the two seats are answering
   different questions.
2. **Quantify the outcome difference** with paired deltas on the metrics that carry the claim: the focal seat's
   surplus and its share of what was available to it, deal rate, joint welfare, the primary score, and each
   party's realized surplus.

Pairing is a *key*, not a heuristic: `pair_key` builds it from the fields that define "the same problem played
the same way", and an unmatched episode is reported rather than approximately matched.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_PAIR_KEY` |  |  |
| `SELECTIONS` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`align`](align.md) | Align two episode payloads slot by slot and locate the divergence point. |
| [`compare_payload`](compare_payload.md) | One seat-swap comparison, ready to render: both episode payloads, the slot alignment, the divergence point, the focal seat(s), and the score table. |
| [`focal_seats`](focal_seats.md) | The seats whose OCCUPANT KIND differs between the two episodes — the substitution being measured. |
| [`pair_key`](pair_key.md) | The pairing key of an episode: the tuple of its `fields`. |
| [`pair_runs`](pair_runs.md) | Pair every episode of one run against its key-matched counterpart in another, and build a comparison payload for each. |
| [`score_table`](score_table.md) | The quantified comparison: one row per metric with both values and the paired delta `right - left`. |

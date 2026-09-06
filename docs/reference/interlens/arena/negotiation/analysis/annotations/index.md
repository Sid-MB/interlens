# `annotations`

Module `interlens.arena.negotiation.analysis.annotations`

Per-turn annotation records: the divergence data model `annotate.py` writes and `taxonomy.py` /
`report.py` read (disk I/O lives in `runio.AnnotationStore`).

An `EpisodeAnnotation` is one episode's divergence record — a `TurnAnnotation` per turn (oracle verdicts,
headline regret, hard-violation flags, counterfactual regret, CoT first-divergent-step) plus a rolled-up
`DivergenceSummary` — kept separate from the immutable raw `Episode` so re-annotating never rewrites it.
`TurnAnnotation.oracle` mirrors interlens' per-oracle `OracleRecord` (name → verdict).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PRIMARY_ORACLES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`DivergenceSummary`](DivergenceSummary.md) | Episode-level roll-up of the turn annotations: the regret series and its aggregates, the divergence-point turns (regret above the noise threshold), and hard-flag counts by taxonomy row. |
| [`EpisodeAnnotation`](EpisodeAnnotation.md) | One episode's full divergence record: the summary plus every turn annotation. |
| [`TurnAnnotation`](TurnAnnotation.md) | One turn's oracle annotation. |

## Functions

| Name | Summary |
|---|---|
| [`annotation_from_episode`](annotation_from_episode.md) | Build an `EpisodeAnnotation` purely from an episode's inline oracle rows (`round_checkpoints`). |
| [`group_oracle_rows`](group_oracle_rows.md) | Group inline oracle rows by turn into `[{turn_idx, round, seat, oracle:{name:row}, regret, flags, belief}]` (turn order). |
| [`inline_oracle_rows`](inline_oracle_rows.md) | The episode's INLINE oracle annotation rows in `round_checkpoints` — the `OracleRecord.to_json()` dicts, identified by a `"verdict"` key (forked provisional-probe rows have no verdict and are excluded). |
| [`summarize_turns`](summarize_turns.md) | Roll a list of turn annotations up into a `DivergenceSummary` (shared by `annotate.py` and the inline-rows reader so the summary math lives in one place). |

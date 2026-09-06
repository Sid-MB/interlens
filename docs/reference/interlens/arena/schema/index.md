# `schema`

Module `interlens.arena.schema`

The arena's record schema: one JSON shape for every episode.

Every episode — regardless of scenario, arm, cell, or model — serializes to one JSON record with the same
top-level fields, so datasets and analyses join cleanly across runs. `Instance` is a generated, solver-verified
problem (with its exact ceiling/floor and hidden solution); `Episode` is one play-through of an instance;
`EpisodeStore` is the crash-safe on-disk layout. The schema is shared with the arena experiments that
produced the public transcripts dataset, so stored episodes from those runs re-score under this package
(see `replay.py`).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PERSONAS` |  |  |
| `SCHEMA_VERSION` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Episode`](Episode.md) | One complete play-through: turns, forked provisional checkpoints, outcome, and usage accounting. |
| [`EpisodeStore`](EpisodeStore.md) | Per-episode JSON persistence, written atomically on every update so a crash loses at most one turn. |
| [`Instance`](Instance.md) | One generated problem instance, solver-verified at generation time. |
| [`JsonRecordStore`](JsonRecordStore.md) | A directory tree of JSON records, one file per record, written atomically. |
| [`SeatRequest`](SeatRequest.md) | One pending generation: a seat that must speak now, with the exact view its model is conditioned on. |
| [`TurnRecord`](TurnRecord.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`load_instances`](load_instances.md) | Load an instance pool saved by `save_instances` (or by the arena experiments — the pre-rename `env` key is migrated on read). |
| [`new_id`](new_id.md) | A fresh episode/instance id. |
| [`save_instances`](save_instances.md) | Persist an instance pool as one JSON file (`{scenario}_L{level}.json` unless `name` overrides). |

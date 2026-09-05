# `interlens.arena.scenarios.longcontext`

Distributed long-context: one long-context task split across 4 communicating seats.

The full task context is partitioned into 4 contiguous shards (provably: the concatenation of the shards
equals the original context — the builders assert it, and `tests` re-check the property). Each team seat
holds one shard in its private system prompt plus the shared question; a designated finalizer (seat 0, who
speaks last each round) submits the team's answer as fenced JSON.

Arms:

- `team` — round-robin broadcast discussion, up to 4 rounds; everyone sees every turn.
- `team-msg` — directed messaging: each non-finalizer turn is ONLY a fenced
  `{"messages": [{"to": ..., "content": ...}]}` object routing private messages to chosen recipients
  (`"all"` broadcasts); a seat sees only messages addressed to it. This is the scenario-native messaging
  protocol — the episode record stays replayable because routing is part of the state machine.
- `solo` — one seat holds the FULL context (the concatenation of the shards) + question; iterates until it
  answers, the engine's budget forces finalization, or a hard 8-iteration ceiling.

Task specifics (question format, answer parsing, grading) live in a `TaskAdapter` (see
`interlens.arena.scenarios.dlc`); the scenario is task-agnostic. Every grader is a pure function of
`(answer, payload)`, so stored episodes re-score exactly under `replay`.

**Outcome classes.** `classify_outcome` refines every episode's outcome after scoring (both live, via the
engine, and in replay):

- `truncated_at_budget` — any committed turn stopped at its `max_tokens` cap marks the episode; such
  episodes are excluded from primary success/failure analysis and reported as their own class (the
  `truncations` list carries per-turn detail).
- `capitulated` (OOLONG-Pairs only) — an episode that was NOT budget-truncated but emitted an empty/short
  answer (<50% of the gold pair count) declined the enumeration rather than running out of room; the
  classification carries evidence (distinct known user IDs surfaced in the visible discussion vs pairs
  emitted).
- otherwise `answered` / `no_answer`.

Provenance: the distributed long-context experiment's environment, ported verbatim onto the `Scenario`
contract (state machine, prompts, caps, and outcome classification unchanged — stored episodes replay,
including their outcome classes). Instances embed megabytes of context and are built offline
(`interlens.arena.scenarios.dlc.build`); `generate_instance` raises by design.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_ROUNDS` |  |  |
| `ROLES` |  |  |
| `TURN_ORDER` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`DistributedLongContext`](DistributedLongContext.md) |  |
| [`TaskAdapter`](TaskAdapter.md) | Per-task behavior plugged into `DistributedLongContext`. |

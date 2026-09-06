# `replay`

Module `interlens.arena.replay`

Deterministic replay of stored episodes through a scenario's state machine.

An `Episode` record stores every committed turn's text. Because a `Scenario` is a pure state machine —
text in, state out, no RNG in stepping — feeding those turns back through `apply` reconstructs the exact
final state and re-derives the outcome with the *current* parser and scorer. Uses:

- **audit**: verify a stored dataset's recorded outcomes against the packaged scorer (the arena export's own
  reproduction check runs on exactly this);
- **re-scoring**: recompute outcomes under an extended scorer without re-running any model;
- **analysis**: reconstruct intermediate states (support maps, challenge ledgers) at any turn.

Replay is exact for episodes produced by this engine (and the arena experiments that share its schema): the
turn log stores think-stripped visible content in scenario order, provisional turns live separately in
`round_checkpoints` (they never touched state), and the one-retry flow re-emits the same request, which is
how `apply` sees it here too.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `DEFAULT_FIELDS` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`ReplayError`](ReplayError.md) | A stored turn could not be matched to the state machine's pending request. |

## Functions

| Name | Summary |
|---|---|
| [`apply_prefix`](apply_prefix.md) | Replay `episode`'s stored turns into an existing `state`, stopping before turn index `upto`. |
| [`make_replay_state`](make_replay_state.md) | A fresh state built exactly the way `episode` was: same instance, arm, seed, and `cell_cfg` (minus the resolved personas, which `make_state` re-resolves identically from the seed). |
| [`replay_episode`](replay_episode.md) | Feed a stored episode's turns back through `scenario` and return the recomputed outcome dict. |
| [`rescore`](rescore.md) | Replay `episode` and compare the recomputed outcome to the recorded one on `fields`. |

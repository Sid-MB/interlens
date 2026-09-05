# `apply_prefix`

Replay `episode`'s stored turns into an existing `state`, stopping before turn index `upto`.

```python
apply_prefix(
	scenario: Scenario,
	state: dict,
	episode: dict,
	upto: int | None = None,
	*,
	on_turn=None,
	on_request=None,
) -> int
```

Defined in [`interlens.arena.replay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/replay.py#L55-L89)

This is the branch/resume primitive: after it returns, `state` is exactly the mid-game state the engine
held live just before the stored turn whose `idx` equals `upto` — `next_requests(state)` re-issues
that turn's request, and play can continue with different text from there. `upto=None` replays every
stored turn (the full-replay case). Matching is by the stored turn's `idx` field, not list position, so a
record whose turns start above zero (itself a branch continuation) replays correctly.

`on_turn` is an optional `callable(state, request, turn) -> None` invoked after each turn is applied,
while `state` still holds that turn's post-move context — the hook for post-hoc per-turn work (re-running
oracles, reconstructing intermediate ledgers). Its return value is ignored; raising aborts the replay.

`on_request` is the same shape, invoked BEFORE the turn is applied, while `state` still holds the
context the seat actually decided in. The two hooks are not interchangeable: a per-turn counterfactual
("what would another decision rule have played HERE") is only meaningful against the pre-move state, and
reading it from `on_turn` would score every rule against the position its own turn created.

Returns the number of turns applied. Raises :class:`ReplayError` if a stored turn cannot be matched to a
pending request, or if `upto` is not reached because the record has fewer turns.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `state` | `dict` | *required* |  |
| `episode` | `dict` | *required* |  |
| `upto` | `int \| None` | `None` |  |
| `on_turn` |  | `None` |  |
| `on_request` |  | `None` |  |

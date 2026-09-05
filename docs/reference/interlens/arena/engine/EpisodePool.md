# `EpisodePool`

Concurrent episodes as independent asyncio tasks — one participant call at a time per episode, many episodes in flight.

```python
EpisodePool(
	store: EpisodeStore | None = None,
	*,
	meter: UsageMeter | None = None,
	max_concurrent: int = 32,
	record_views: bool = True,
	refusal_ladder: RefusalLadder | None = None,
	wave_parallel: bool = True,
)
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L537-L757)

Each blocking `Participant.generate` runs in a worker thread, so hosted-API episodes
are throughput-bound by the shared client's `max_in_flight` cap, not by the event loop.

`meter` (a `UsageMeter`) adds run-level spend control: jobs carrying `estimated_cost` are
reservation-gated (an episode that doesn't fit under the budget is skipped, returned as `None`), and
every episode re-checks the meter's `exhausted` state when it acquires its concurrency slot, so spend
accumulated while it queued genuinely stops it from starting.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `store` | [EpisodeStore](../schema/EpisodeStore.md) \| None | `None` |  |
| `meter` | [UsageMeter](../../usage/UsageMeter.md) \| None | `None` |  |
| `max_concurrent` | `int` | `32` |  |
| `record_views` | `bool` | `True` |  |
| `refusal_ladder` | [RefusalLadder](../refusal/RefusalLadder.md) \| None | `None` |  |
| `wave_parallel` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `meter` |  |  |
| `record_views` |  |  |
| `refusal_ladder` |  |  |
| `store` |  |  |
| `wave_parallel` |  |  |

## Methods {#methods}

## `run_episode` {#run_episode}

```python
run_episode(
	self,
	scenario: Scenario,
	instance: Instance,
	arm: str,
	participant,
	*,
	seed: int = 0,
	cfg: dict | None = None,
	gen_config: dict | None = None,
	budget: StopCondition | list | None = None,
	estimated_cost: float | None = None,
	capture=None,
	steering=None,
	patch=None,
	gate: Callable[[], bool] | None = None,
	on_wave: Callable[[Episode], None] | None = None,
	prefix: tuple[dict, int | None] | None = None,
) -> Episode | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L643-L747)

Play one episode to completion.

Returns the `Episode` (status `done` or `error`), or `None`
when the episode never started: its cost reservation didn't fit under the meter's budget, the meter was
already exhausted, or `gate()` returned True. The launch gates are evaluated once the episode acquires
a concurrency slot (`max_concurrent` bounds episodes in flight), so a queued episode really is stopped
by spend that accumulated while it waited — in-flight episodes finish, new ones don't start.

`capture` / `steering` / `patch` are per-turn interp hooks threaded into every committed
generation (local `ModelParticipant` only — API/scripted participants raise on interp requests);
`capture` (a `CaptureRequest`) tags activations by this episode's turn index, so per-turn activation
capture *inside* a structured episode works. Forked provisional probes are left clean (no capture/steer).

`on_wave(episode)` is an observer called with the live `Episode` after every wave is persisted and once
more after `finalize()` — the seam a live viewer streams from (`arena.live`). It fires AFTER `save()`
on purpose: an observer can then never show a turn that is not yet on disk, so a reader who reloads mid-
episode sees at least what was streamed to them. It is an OBSERVER, not a hook — its return value is
ignored and any exception it raises is logged and swallowed, because a broken viewer must not be able to
kill a running episode. Leave it `None` (the default) and the episode is byte-for-byte what it was.

`prefix = (parent_episode_json, upto_turn_idx)` resumes a stored episode from mid-game: the parent's
turns with `idx < upto` are replayed into the fresh state (`interlens.arena.replay.apply_prefix`)
before the first generation, so this episode continues that game from that exact node. The same key on a
`run_episodes`/`run_pool` job dict does the same thing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `participant` |  | *required* |  |
| `seed` | `int` | `0` |  |
| `cfg` | `dict \| None` | `None` |  |
| `gen_config` | `dict \| None` | `None` |  |
| `budget` | [StopCondition](../../stop/stop_condition/StopCondition.md) \| list \| None | `None` |  |
| `estimated_cost` | `float \| None` | `None` |  |
| `capture` |  | `None` |  |
| `steering` |  | `None` |  |
| `patch` |  | `None` |  |
| `gate` | `Callable[[], bool] \| None` | `None` |  |
| `on_wave` | Callable[[[Episode](../schema/Episode.md)], None] \| None | `None` |  |
| `prefix` | `tuple[dict, int \| None] \| None` | `None` |  |

## `run_pool` {#run_pool}

```python
run_pool(
	self,
	jobs: list[dict],
	stop_check: Callable[[], bool] | None = None,
) -> list[Episode]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L749-L757)

Run many episodes concurrently (`max_concurrent` in flight).

Each job is the `run_episode`
kwargs (`{scenario, instance, arm, participant, seed?, cfg?, gen_config?, budget?, estimated_cost?}`).
`stop_check() -> bool` and the meter's `exhausted` state are evaluated when each episode acquires
its slot — not at submission — so once either fires, queued episodes are skipped while in-flight ones
finish. Skipped episodes are omitted from the result.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `jobs` | `list[dict]` | *required* |  |
| `stop_check` | `Callable[[], bool] \| None` | `None` |  |

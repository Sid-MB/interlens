# `BatchedEpisodePool`

Synchronous co-stepping for local model participants: each tick gathers every live episode's pending requests and runs them as one batched `generate_batch` per participant — the local-GPU throughput path.

```python
BatchedEpisodePool(
	store: EpisodeStore | None = None,
	*,
	record_views: bool = True,
	max_fabricated_fraction: float = MAX_FABRICATED_FRACTION,
	fabrication_floor: int = FABRICATION_FLOOR,
	single_request_retries: int = SINGLE_REQUEST_RETRIES,
)
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L760-L1042)

On CUDA OOM (or the transient cuDNN graph errors long co-stepped batches produce), the wave is split and
retried down to single episodes, then that single request is retried a bounded number of times. Only if all of
that fails does the pool fabricate a placeholder turn so it can keep moving — and a fabricated turn is LOGGED
at error level and STAMPED (`TurnRecord.gen_failed`), because text no model produced must never be
mistaken for model behaviour. Past `max_fabricated_fraction` of the pool's turns the run RAISES instead.

Parameters
----------
store : EpisodeStore | None
        Where to persist each episode after every applied wave.
record_views : bool
        Persist each turn's rendered view into its `TurnRecord` (default on).
max_fabricated_fraction : float
        The fraction of attempted turns the engine may fabricate before raising
        :class:`GenerationFailureBudgetExceeded` (default :data:`MAX_FABRICATED_FRACTION`, 10%). A healthy run
        fabricates none, so any nonzero rate is already a defect; the ceiling exists to stop a broken run in its
        first seconds rather than at analysis time. Set it to `1.0` to never raise (the old behaviour) — which
        is only defensible if something downstream screens `gen_failed`.
fabrication_floor : int
        Attempted turns required before the fraction is consulted (default :data:`FABRICATION_FLOOR`), so one
        transient blip in a tiny run cannot trip the ceiling on a denominator of one.
single_request_retries : int
        Re-attempts of a lone failing request after splitting has narrowed the wave to it, before fabricating
        (default :data:`SINGLE_REQUEST_RETRIES`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `store` | [EpisodeStore](../schema/EpisodeStore.md) \| None | `None` |  |
| `record_views` | `bool` | `True` |  |
| `max_fabricated_fraction` | `float` | `MAX_FABRICATED_FRACTION` |  |
| `fabrication_floor` | `int` | `FABRICATION_FLOOR` |  |
| `single_request_retries` | `int` | `SINGLE_REQUEST_RETRIES` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `attempted_turns` |  |  |
| `fabricated_turns` |  |  |
| `fabrication_floor` |  |  |
| `failures` | `list[dict]` |  |
| `max_fabricated_fraction` |  |  |
| `record_views` |  |  |
| `single_request_retries` |  |  |
| `store` |  |  |

## Methods {#methods}

## `fabrication_report` {#fabrication_report}

```python
fabrication_report(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L807-L821)

How much of this pool's output the engine had to fabricate: `{attempted, fabricated, fraction, failures}`.

A caller should log this at the end of a run — `fraction == 0.0` is the only healthy
value, and anything else bounds how much of the run is not model behaviour.

This is the ONLY complete account of a run's fabrications, and it is why the report exists alongside the
per-turn stamp. Committed turns carry `TurnRecord.gen_failed`, but a forked **provisional** probe is
stored as an `OracleRecord` rather than a `TurnRecord`, so it has nowhere to carry the stamp: a
fabricated provisional shows up here and in `failures` (with `phase == "provisional"`), and in the
stored record only as `content == EMPTY_TURN_PLACEHOLDER`. So `fabricated` can legitimately exceed the
number of `gen_failed` turns in the episodes; the difference is fabricated provisional probes, whose
`score` should be treated as contaminated.

## `run_pool` {#run_pool}

```python
run_pool(
	self,
	jobs: list[dict],
	progress: Callable[[int, int], None] | None = None,
) -> list[Episode]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L823-L906)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `jobs` | `list[dict]` | *required* |  |
| `progress` | `Callable[[int, int], None] \| None` | `None` |  |

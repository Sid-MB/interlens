# `engine`

Module `interlens.arena.engine`

Episode drivers: play `Scenario` instances through `Participant`s.

The scenario is a pure state machine (it emits `SeatRequest`s and consumes text); the engine owns everything
around it — driving the participant, per-episode persistence (atomic write after every applied wave), the
one-retry rule, forked provisional elicitations (whose responses never enter state or any transcript), budget
enforcement, and usage accounting.

Two drivers, two throughput regimes:

- `EpisodePool` — episodes as independent `asyncio` tasks over any participant (API participants are
  network-bound; each blocking `generate` runs in a worker thread, so the pool is fully concurrent and its
  width is bounded by the shared API client's `max_in_flight`). Fully async and free of shared mutable
  state across episodes, so it also serves as the Inspect solver's engine.
- `BatchedEpisodePool` — synchronous co-stepping for **local** model participants: each tick collects the
  pending requests of every live episode and runs them as ONE batched `generate_batch` per participant
  (the 5–20× rollout win), with adaptive batch splitting on GPU OOM.

**A failed generation is never silent, and the two drivers are equally honest about it.** Both drivers meet the
same cuDNN/OOM faults under load; what differed was only the REPORTING. `EpisodePool` always surfaced a failure
as `status="error"` with the traceback — legible, and excluded by any "done" filter. `BatchedEpisodePool`
instead substituted `EMPTY_TURN_PLACEHOLDER` and swallowed the exception, and because that placeholder parses
into a well-formed no-op, a cell in which *every* turn had been fabricated still reported `status="done"` and
`parse_ok=True` throughout; the contamination was found months later, from the outcome numbers.

So the batched driver now recovers from a transient fault by splitting the wave and then retrying the lone
request, and only if that also fails does it fabricate — at which point it logs at ERROR, stamps
`TurnRecord.gen_failed` with the causing exception, counts it, and RAISES
`GenerationFailureBudgetExceeded` once such turns exceed `max_fabricated_fraction` of the run. A
non-transient error is a bug and always propagates; it is never converted into a turn. Screen stored episodes
with `gen_failures(episode)` (it also handles pre-stamp records) and read a run's totals from
`BatchedEpisodePool.fabrication_report()`.

**Budgets are stop conditions, not ad-hoc counters.** An episode's budget is any `StopCondition`
(`TokenBudget`, `CostBudget`, a list of both): the engine records each committed turn as an interlens
`Message` (usage metadata included) on an internal transcript, checks the condition against it, and applies
`turn_cap` to each generation. When the budget fires, the engine sets `state['budget_exhausted']` so the
scenario steers to a forced finalization — the matched-compute semantics from the arena experiments (a solo
baseline gets the team's median token budget, then must answer with what it has).

**Spend is gated by reservation, not post-hoc.** Pass a `UsageMeter` and per-job `estimated_cost`: the
pool claims the estimate *before* launching each episode and settles it after, so N concurrent episodes can
never collectively overrun the meter's budget (in-flight episodes finish; new ones don't start).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `EFFECTIVE_CAP_KEY` |  |  |
| `EMPTY_TURN_PLACEHOLDER` |  |  |
| `FABRICATION_FLOOR` |  |  |
| `GEN_FAILED_KEY` |  |  |
| `GEN_FAILURE_KEY` |  |  |
| `MAX_FABRICATED_FRACTION` |  |  |
| `SINGLE_REQUEST_RETRIES` |  |  |
| `TRUNCATED_STOPS` |  |  |
| `TURN_SIGNATURES` |  |  |
| `logger` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`BatchedEpisodePool`](BatchedEpisodePool.md) | Synchronous co-stepping for local model participants: each tick gathers every live episode's pending requests and runs them as one batched `generate_batch` per participant — the local-GPU throughput path. |
| [`EpisodePool`](EpisodePool.md) | Concurrent episodes as independent asyncio tasks — one participant call at a time per episode, many episodes in flight. |
| [`EpisodeRun`](EpisodeRun.md) | Per-episode bookkeeping shared by both drivers: state stepping, turn recording, budget checks, retries, and finalization. |
| [`GenerationFailureBudgetExceeded`](GenerationFailureBudgetExceeded.md) | Raised by :class:`BatchedEpisodePool` when it has had to fabricate more turns than its budget allows. |

## Functions

| Name | Summary |
|---|---|
| [`gen_failures`](gen_failures.md) | Every turn of an episode whose text the ENGINE fabricated because generation failed. |
| [`truncation_budget`](truncation_budget.md) | The output budget one stored turn's `n_tokens_out` may honestly be compared against; `0` for "none, so read truncation from `stop_reason` alone". |
| [`turn_signatures`](turn_signatures.md) | Every failure signature carried by one stored turn (a `TurnRecord.to_json()` dict); `set()` if healthy. |

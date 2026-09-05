# `interlens.participant.governor`

Adaptive rate-limit governor: admission control paced by the provider's own rate-limit headers.

Written for build item 10 of `experiments/rational_agents/auction/docs/design.md` §12 ("Throughput: max out
the rate limit"). The stack it replaces is reactive-only — a fixed `max_in_flight` semaphore in
`api_client.py` plus 429 exponential backoff — which runs far below the org ceiling because the ceiling is
never read. A governed run has **no fixed concurrency knob**: every episode of every cell in the process shares
one governor, and the rate-limit headers are the throttle.

Three signals drive admission:

- **Bucket headroom.** Every response (success *and* error) carries `anthropic-ratelimit-{requests,
  input-tokens,output-tokens,tokens}-{limit,remaining,reset}`. The governor projects each bucket's remaining
  capacity forward by what the requests admitted since that header snapshot are expected to consume, and admits
  while every bucket's projection stays above a safety floor (default 10% of the bucket's limit). A caller that
  would breach the floor sleeps until the earliest bucket reset and is woken there.
- **AIMD.** Any 429 multiplicatively cuts the admission target (×0.5) and, when the response carries
  `retry-after`, blocks readmission until that deadline. Each clean completion adds 1 back. This is the whole
  control loop when headers are missing (older SDK, a proxy that strips them): the governor logs that it is
  **header-blind** and falls back to pure AIMD seeded at `blind_target` (8) concurrent.
- **Live in-flight count.** `live_in_flight` is the number of requests actually in flight right now, exported
  so the campaign's working-capital guard (`experiments/rational_agents/api_request_budget.py`) can size its
  worst-case reservations against the real concurrency rather than a static parameter — a static ×120
  reservation against the committed budget would starve the tail cells (design.md §11).

The core is a `threading.Condition`, not an asyncio primitive, because the actual call site is a **worker
thread**: `EpisodePool` runs episodes as asyncio tasks but each participant call goes through
`asyncio.to_thread` into the synchronous provider SDK. A condition variable is admissible from both worlds;
:meth:`admit_async` is the awaitable wrapper for callers already on an event loop.

Usage:

```python
from interlens.participant.governor import RateLimitGovernor, install_governor, governor_report

install_governor(RateLimitGovernor())        # process-wide, before launching any cell
...                                          # every Anthropic request now passes through it
print(governor_report())                     # into run.log: observed ceilings + AIMD history
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `BUCKET_PREFIXES` |  |  |
| `RETRY_AFTER_HEADER` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Bucket`](Bucket.md) | One rate-limit bucket as last reported by the provider, plus the consumption the governor has admitted since that report. |
| [`RateLimitGovernor`](RateLimitGovernor.md) | Process-wide admission controller for one provider+org, paced by rate-limit headers with an AIMD fallback. |
| [`TokenEstimate`](TokenEstimate.md) | Exponentially weighted per-request token consumption, used to project the token buckets forward between header reports. |

## Functions

| Name | Summary |
|---|---|
| [`current_governor`](current_governor.md) | The installed process-wide governor, or `None` when the run is ungoverned (the pre-existing behaviour: the client's own `max_in_flight` semaphore is then the only concurrency bound). |
| [`governor_report`](governor_report.md) | The installed governor's :meth:`RateLimitGovernor.report`, or a one-line notice when none is installed — safe to call unconditionally from a run's logging path. |
| [`install_governor`](install_governor.md) | Install (or with `None`, remove) the process-wide governor and return it. |

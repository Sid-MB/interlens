# `RateLimitGovernor`

Process-wide admission controller for one provider+org, paced by rate-limit headers with an AIMD fallback.

```python
RateLimitGovernor(
	*,
	floor_fraction: float = 0.1,
	blind_target: float = 8.0,
	max_target: float | None = 512.0,
	min_target: float = 1.0,
	cut_factor: float = 0.5,
	recovery: float = 1.0,
	clock=time.monotonic,
)
```

Defined in [`interlens.participant.governor`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L119-L417)

One governor per provider+org and one per process: it is shared by every participant, episode, and cell, so
total in-flight requests are bounded by the measured header ceiling rather than by any per-cell knob.

:param floor_fraction: admit only while every bucket's projected remaining exceeds this fraction of its
        limit. 0.10 keeps a 10% cushion for requests already in flight whose usage has not been reported yet;
        raise it for a run that must never see a 429, lower it to squeeze the ceiling harder.
:param blind_target: the AIMD admission target used before any header has been seen, and the permanent
        ceiling if headers never arrive (header-blind mode). 8 is deliberately modest — it recovers upward by
        one per clean completion, so a genuinely wide limit is discovered within seconds.
:param max_target: hard ceiling on the AIMD target, a safety stop against unbounded additive growth when a
        provider reports enormous buckets. `None` leaves growth bounded only by the buckets.
:param min_target: floor the multiplicative cut cannot go below, so a burst of 429s cannot wedge the run at
        zero concurrency.
:param cut_factor: the multiplicative decrease applied to the target on each 429 (0.5 = halve).
:param recovery: the additive increase per clean completion (1 request).
:param clock: monotonic time source, injectable so tests can drive resets without sleeping.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `floor_fraction` | `float` | `0.1` |  |
| `blind_target` | `float` | `8.0` |  |
| `max_target` | `float \| None` | `512.0` |  |
| `min_target` | `float` | `1.0` |  |
| `cut_factor` | `float` | `0.5` |  |
| `recovery` | `float` | `1.0` |  |
| `clock` |  | `time.monotonic` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `admitted` |  |  |
| `blind_target` |  |  |
| `cut_factor` |  |  |
| `cuts` |  |  |
| `floor_fraction` |  |  |
| `header_blind` | `bool` | True while no response has reported a rate-limit header — the governor is running on pure AIMD and says so in :meth:`governor_report`, because a header-blind run cannot claim to have found the ceiling. |
| `live_in_flight` | `int` | Requests admitted and not yet released, right now. |
| `max_target` |  |  |
| `min_target` |  |  |
| `rate_limited` |  |  |
| `recoveries` |  |  |
| `recovery` |  |  |
| `waits` |  |  |

## Methods {#methods}

## `acquire` {#acquire}

```python
acquire(self, timeout: float | None = None) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L184-L213)

Block until admission is granted, then count the request as in flight.

`timeout` (seconds) raises
`TimeoutError` rather than admitting — leave it `None` for campaign traffic, where waiting for the
bucket to refill is the correct behaviour and giving up would just drop an episode.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `timeout` | `float \| None` | `None` |  |

## `admit` {#admit}

```python
admit(self, timeout: float | None = None)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L222-L230)

Synchronous admission scope: `with governor.admit(): ...` around one provider request.

This is the
form the client uses, because provider SDK calls run in worker threads.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `timeout` | `float \| None` | `None` |  |

## `admit_async` {#admit_async}

```python
admit_async(self, timeout: float | None = None)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L232-L242)

Awaitable admission scope for callers already on an event loop: `async with governor.admit_async():`.

The blocking wait is offloaded with `asyncio.to_thread` so the loop is never stalled by a sleeper.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `timeout` | `float \| None` | `None` |  |

## `note_exception` {#note_exception}

```python
note_exception(self, exc) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L310-L321)

Feed one provider exception to the governor without the caller having to know the SDK's exception classes: any exception carrying an HTTP response contributes its headers, and a 429 additionally triggers the AIMD cut.

Anything else (a connection error, a 500) is ignored — those are the retry loop's business,
not the rate limiter's.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `exc` |  | *required* |  |

## `note_headers` {#note_headers}

```python
note_headers(
	self,
	headers,
	*,
	tokens_in: int = 0,
	tokens_out: int = 0,
	seed: bool = True,
) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L261-L280)

Absorb one response's rate-limit headers — from a **success or an error**, since a 429's headers are the most informative ones in the run.

`headers` is any mapping (httpx `Headers`, a plain dict);
absent or unparseable headers are ignored, leaving the governor in header-blind AIMD. `tokens_in` /
`tokens_out` update the per-request estimate that projects token buckets between reports.

`seed=False` absorbs the buckets without letting them re-seed the AIMD target; the 429 path uses it so
a cut is never undone by the very response that reported the overshoot.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `headers` |  | *required* |  |
| `tokens_in` | `int` | `0` |  |
| `tokens_out` | `int` | `0` |  |
| `seed` | `bool` | `True` |  |

## `note_rate_limited` {#note_rate_limited}

```python
note_rate_limited(self, *, headers=None, retry_after: float | None = None) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L295-L308)

One 429 (or other rate-limit signal): multiplicative cut of the AIMD target and, when the response carries `retry-after` (explicit argument wins, else read from `headers`), a hard block on readmission until that deadline passes.

Headers are absorbed first, so the cut is recorded against fresh ceilings.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `headers` |  | `None` |  |
| `retry_after` | `float \| None` | `None` |  |

## `note_success` {#note_success}

```python
note_success(self, *, headers=None, tokens_in: int = 0, tokens_out: int = 0) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L282-L293)

One clean completion: additive recovery of the AIMD target (+`recovery`), plus header absorption.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `headers` |  | `None` |  |
| `tokens_in` | `int` | `0` |  |
| `tokens_out` | `int` | `0` |  |

## `release` {#release}

```python
release(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L215-L220)

Mark one in-flight request finished and wake a waiter.

Always pair with :meth:`acquire` (use
:meth:`admit` / :meth:`admit_async` rather than calling either by hand).

## `report` {#report}

```python
report(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L398-L417)

The :meth:`snapshot` formatted for `run.log` — one header line plus one line per observed bucket.

## `snapshot` {#snapshot}

```python
snapshot(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L372-L396)

A JSON-serializable view of the control state: live in-flight count, the AIMD target, whether the governor is header-blind, per-bucket ceilings with their projections, the raw last-seen headers, and the cut/recovery/wait counters.

The pilot writes this into `run.log` so the confirmatory launch confirms
rather than discovers where the ceiling sits (design.md §12 item 10).

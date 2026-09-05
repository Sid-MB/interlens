# `UsageMeter`

A cumulative, thread-safe dollar ledger shared by every metered participant in a run.

```python
UsageMeter(
	budget: float | None = None,
	*,
	path: str | Path | None = None,
	pricing: dict | None = None,
)
```

Defined in [`interlens.usage`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L94-L254)

`add` records one API call (tokens in/out at `price_multiplier` — 0.5 for batch-API-served responses)
and returns that call's cost. `reserve`/`settle` implement reservation-style gating: claim an estimated
cost *before* launching an episode/conversation so concurrent work cannot collectively outrun `budget`
(the post-overrun fix from the arena experiments: a pure post-hoc meter let in-flight episodes blow past the
cap). `exhausted` is the launch gate — in-flight work finishes, new work doesn't start.

With `path=` the ledger is persisted atomically after every add, so a crashed/restarted run resumes with
its spend intact. Refusal telemetry rides along: `add(..., refusal=True)` counts hosted-API refusals per
model (a seat-selective refusal pattern silently biases multi-agent results; the counter makes it visible).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `budget` | `float \| None` | `None` |  |
| `path` | `str \| Path \| None` | `None` |  |
| `pricing` | `dict \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `budget` |  |  |
| `by_model` | `dict[str, dict]` |  |
| `exhausted` | `bool` | True once actual spend has reached the budget — the gate for launching NEW work (in-flight work is allowed to finish; that is the reservation's job to have pre-counted). |
| `path` |  |  |
| `pricing` |  |  |
| `reserved_usd` |  |  |
| `total_usd` |  |  |

## Methods {#methods}

## `add` {#add}

```python
add(
	self,
	model: str,
	tokens_in: int,
	tokens_out: int,
	*,
	price_multiplier: float = 1.0,
	refusal: bool = False,
	cache_read_tokens: int = 0,
	cache_write_tokens: int = 0,
	cache_ttl: str = '5m',
) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L142-L167)

Record one completed API call; returns its cost in dollars.

`price_multiplier` scales the price for
discounted billing paths (0.5 = provider batch API). Thread-safe; persists when `path` is set.

The cache counters are recorded per model as well as priced, because a run's cache HIT RATE is what tells
a campaign whether its prompt-cache breakpoints are actually placed on a stable prefix — and the per-turn
metadata is not aggregated anywhere else. `m["in"]` accumulates the WHOLE prompt (uncached + read +
written) so a prompt-size series stays comparable across cached and uncached runs; the split lives in
`m["cache_read"]` / `m["cache_write"]`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | *required* |  |
| `tokens_in` | `int` | *required* |  |
| `tokens_out` | `int` | *required* |  |
| `price_multiplier` | `float` | `1.0` |  |
| `refusal` | `bool` | `False` |  |
| `cache_read_tokens` | `int` | `0` |  |
| `cache_write_tokens` | `int` | `0` |  |
| `cache_ttl` | `str` | `'5m'` |  |

## `cache_report` {#cache_report}

```python
cache_report(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L169-L190)

Per-model prompt-cache accounting: `{model: {prompt_tokens, cache_read, cache_write, uncached, hit_rate, saved_usd}}`.

`hit_rate` is cache reads over the whole prompt volume — the honest denominator, since a write is a
prefix the cache did NOT serve. `saved_usd` is what the same token volume would have cost with no
caching minus what it did cost, so a run whose breakpoints sit on an unstable prefix reports a NEGATIVE
saving (writes at a premium, never read) rather than a flattering zero.

## `price` {#price}

```python
price(
	self,
	model: str,
	tokens_in: int,
	tokens_out: int,
	*,
	cache_read_tokens: int = 0,
	cache_write_tokens: int = 0,
	cache_ttl: str = '5m',
) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L124-L138)

Dollar cost of one call at full (non-batch) price.

Unknown models use `FALLBACK_PRICING`.

`tokens_in` is the prompt portion billed at the full input rate — for a cached Anthropic call that is
the provider's `usage.input_tokens`, which EXCLUDES both cache reads and cache writes. The cached
portions are priced separately off the same input rate at :data:`CACHE_READ_MULTIPLIER` and
:data:`CACHE_WRITE_MULTIPLIERS` keyed by `cache_ttl`, so the three never double-count each other.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | *required* |  |
| `tokens_in` | `int` | *required* |  |
| `tokens_out` | `int` | *required* |  |
| `cache_read_tokens` | `int` | `0` |  |
| `cache_write_tokens` | `int` | `0` |  |
| `cache_ttl` | `str` | `'5m'` |  |

## `reserve` {#reserve}

```python
reserve(self, usd: float) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L202-L210)

Claim `usd` of estimated future spend.

Returns `False` (claiming nothing) when spent + already
reserved + this claim would exceed the budget — the caller should then not launch the work. With no
`budget`, reservations always succeed (the ledger still tracks them).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `usd` | `float` | *required* |  |

## `settle` {#settle}

```python
settle(self, usd: float) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L212-L215)

Release a prior reservation (call once the work's actual spend has been metered via `add`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `usd` | `float` | *required* |  |

## `snapshot` {#snapshot}

```python
snapshot(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L225-L229)

A JSON-serializable copy of the ledger: totals, reservations, and the per-model breakdown.

## `summary` {#summary}

```python
summary(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L231-L243)

A printable run-spend summary: one line per model (calls, tokens, refusals, dollars) plus the total against the budget.

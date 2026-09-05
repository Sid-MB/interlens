# `EpisodeRun`

Per-episode bookkeeping shared by both drivers: state stepping, turn recording, budget checks, retries, and finalization.

```python
EpisodeRun(
	scenario: Scenario,
	instance: Instance,
	arm: str,
	participant,
	seed: int,
	store: EpisodeStore | None,
	*,
	cfg: dict | None = None,
	gen_config: dict | None = None,
	budget: StopCondition | list | None = None,
	capture=None,
	steering=None,
	patch=None,
	record_views: bool = True,
	prefix: tuple[dict, int | None] | None = None,
)
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L333-L534)

Driver-agnostic — it never talks to a participant itself.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `participant` |  | *required* |  |
| `seed` | `int` | *required* |  |
| `store` | [EpisodeStore](../schema/EpisodeStore.md) \| None | *required* |  |
| `cfg` | `dict \| None` | `None` |  |
| `gen_config` | `dict \| None` | `None` |  |
| `budget` | [StopCondition](../../stop/stop_condition/StopCondition.md) \| list \| None | `None` |  |
| `capture` |  | `None` |  |
| `steering` |  | `None` |  |
| `patch` |  | `None` |  |
| `record_views` | `bool` | `True` |  |
| `prefix` | `tuple[dict, int \| None] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `budget` |  |  |
| `capture` |  |  |
| `ep` |  |  |
| `instance` |  |  |
| `ledger` |  |  |
| `participant` |  |  |
| `patch` |  |  |
| `record_views` |  |  |
| `retries` | `set[tuple]` |  |
| `scenario` |  |  |
| `state` |  |  |
| `steering` |  |  |
| `store` |  |  |

## Methods {#methods}

## `allow_retry` {#allow_retry}

```python
allow_retry(self, request: SeatRequest) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L500-L505)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |

## `annotate` {#annotate}

```python
annotate(self, request: SeatRequest) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L483-L490)

Run the scenario's inline oracles over the turn just committed and append their typed `OracleRecord`s to the episode's oracle log.

A no-op unless the scenario overrides `annotate_turn`
(pure-Python — no extra generation), so scenarios without an oracle stack are unaffected.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |

## `finalize` {#finalize}

```python
finalize(self, error: str | None = None) -> Episode
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L520-L534)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `error` | `str \| None` | `None` |  |

## `pending` {#pending}

```python
pending(self) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L397-L403)

## `record_provisional` {#record_provisional}

```python
record_provisional(self, request: SeatRequest, message: Message, parsed, score) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L475-L481)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `message` | [Message](../../message/Message.md) | *required* |  |
| `parsed` |  | *required* |  |
| `score` |  | *required* |  |

## `record_turn` {#record_turn}

```python
record_turn(self, request: SeatRequest, message: Message, cap: int = 0) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L416-L473)

Commit one generated turn: strip any leaked reasoning, apply it to the scenario state, log the `TurnRecord`, accumulate usage, and check the budget.

Returns the scenario's retry directive, if any.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `message` | [Message](../../message/Message.md) | *required* |  |
| `cap` | `int` | `0` |  |

## `retry_request` {#retry_request}

```python
retry_request(request: SeatRequest, prior_text: str, retry_prompt: str) -> SeatRequest
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L507-L514)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `prior_text` | `str` | *required* |  |
| `retry_prompt` | `str` | *required* |  |

## `save` {#save}

```python
save(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L516-L518)

## `score_provisional` {#score_provisional}

```python
score_provisional(self, message: Message) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L492-L498)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | [Message](../../message/Message.md) | *required* |  |

## `turn_cap` {#turn_cap}

```python
turn_cap(self, request: SeatRequest) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L405-L414)

The output cap for one generation: the request's own cap, shrunk by the budget's `turn_cap` (a `TokenBudget` lands the final turn on budget).

A participant-level `turn_token_floor` may raise it
back — the thinking-aware tradeoff documented on `APIParticipant`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |

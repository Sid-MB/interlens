# `Scenario`

```python
Scenario()
```

Defined in [`interlens.arena.scenario`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L45-L260)

**Inherits from:** `ABC`

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` | `int` |  |
| `SOLO_CEILING` | `int \| None` |  |
| `SOLO_SEAT` | `str` |  |
| `default_communication` | `str` | The communication mode task runners (e.g. the Inspect tasks) use when none is given. |
| `has_solo` | `bool` |  |
| `name` | `str` |  |

## Methods {#methods}

## `annotate_turn` {#annotate_turn}

```python
annotate_turn(self, state: dict, request: SeatRequest, turn) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L98-L104)

Inline per-turn oracle annotations, run by the engine right after `apply` commits `turn` (no extra generation).

Return a list of `interlens.arena.oracles.OracleRecord` — the engine appends them to the
episode's oracle log. A scenario with a pure-Python oracle stack scores the seat's ACTUAL move against
the oracle's best here (`interlens.arena.oracles.annotate` is the ready one-liner); the default runs no
oracles. This is the inline sibling of the forked `provisional_due` path — the two coexist.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `turn` |  | *required* |  |

## `apply` {#apply}

```python
apply(self, state: dict, request: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L81-L86)

Parse `text`, mutate state (append events, record actions, advance phase/round, set `done`).

Return `{'retry': <prompt>}` to request ONE re-prompt of the same seat (engine-enforced), else
`None`. Must record the parsed action for the turn log via
`state['_last_parse'] = (parsed_action, parse_ok)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `classify_outcome` {#classify_outcome}

```python
classify_outcome(self, state: dict, turns: list, outcome: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L230-L235)

Post-scoring outcome refinement, merged into the episode's outcome by the engine AND by replay.

Must be pure in `(state, turns, outcome)`. `turns` items are `TurnRecord`s live and plain dicts in
replay — read fields defensively. Default: no refinement. The distributed long-context scenario uses
this for its `truncated_at_budget` / `capitulated` outcome classes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `turns` | `list` | *required* |  |
| `outcome` | `dict` | *required* |  |

## `final_retry_directive` {#final_retry_directive}

```python
final_retry_directive(
	self,
	state: dict,
	request: SeatRequest,
	retry_prompt: str,
	*,
	key=None,
) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L129-L140)

The one-retry-then-give-up bookkeeping shared by every scenario's forced-finalization phase: on the FIRST malformed final action for `key` (default `("retry", request.round)`) return `{'retry': retry_prompt}` (the engine re-prompts once); on the second, return `None` so the caller finalizes with what it has.

Idempotent per key via `state['_r']`, so replay re-emits the identical retry.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `retry_prompt` | `str` | *required* |  |
| `key` |  | `None` |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L60-L62)

Generate one solver-verified instance at `level` from `seed` (deterministic payload per seed).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L65-L69)

Fresh episode state.

For `arm='solo'` the single seat gets ALL private info; solo episodes iterate
until a final action or the engine's budget forces finalization. `cfg` is an optional sweep-cell
config (situational knobs: rounds, framings, personas); scenarios that don't support one may ignore it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `messaging_decider` {#messaging_decider}

```python
messaging_decider(self, state: dict) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L123-L126)

The seat whose last fenced action decides a messaging episode (the finalizer / proposer).

The adapter
scans this seat's turns for the deciding `answer` / `proposal` JSON. Default: the first seat.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `messaging_finalizable` {#messaging_finalizable}

```python
messaging_finalizable(self) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L115-L121)

Whether a free-form messaging episode can be reduced to one final action by the adapter's final-answer/proposal extraction — True exactly when the protocol ends in a single structured answer that the deciding seat emits.

Scenarios that instead implement `score_from_messaging` don't need this. The
Inspect messaging adapter uses this capability (not a hardcoded scenario name) to decide whether it can
run the scenario at all. Default: False.

## `next_requests` {#next_requests}

```python
next_requests(self, state: dict) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L76-L79)

The requests due now (>1 only for simultaneous phases).

`[]` iff done. `episode_id` on the
returned requests is filled by the engine.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, state: dict) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L89-L92)

Forked finalize-now elicitations due at this point (the engine calls right after each applied wave).

Provisional responses never enter state or any transcript. Default: none.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, state: dict) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L242-L243)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `score` {#score}

```python
score(self, state: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L237-L240)

Final outcome dict.

Must include `primary` (float, higher is better) and `success` (bool) where
meaningful, plus scenario-specific fields.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `score_from_messaging` {#score_from_messaging}

```python
score_from_messaging(
	self,
	instance,
	transcript: list[tuple[str, str]],
	cfg: dict | None = None,
) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L107-L113)

Score a free-form messaging-mode episode (the Inspect adapter's `communication="messaging"`): `transcript` is `[(seat, text), ...]` in send order.

Return the outcome dict, or `None` when the
scenario has no messaging reduction — the adapter then falls back to the final-answer/proposal
reduction for scenarios whose protocol ends in one structured action, and raises otherwise.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` |  | *required* |  |
| `transcript` | `list[tuple[str, str]]` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, state: dict, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L94-L96)

Score a provisional final action with the normal scorer.

Default: not scored.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `parsed` |  | *required* |  |

## `seat_framings` {#seat_framings}

```python
seat_framings(self, state: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L245-L260)

`{seat_name: verbatim system prompt}` for a fresh state — the private framing each seat receives.

Team arms render every seat directly; solo arms capture the single seat's system prompt from its first
request. Lets a dataset/record ship self-contained framings.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, state: dict) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L71-L73)

`[{name, role, ...}]` for the episode record.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_apply` {#solo_apply}

```python
solo_apply(self, state: dict, request: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L208-L227)

The solo arm's `apply`: record the turn, finalize on a genuine answer, give up on a forced-final that produced none, else (below any `SOLO_CEILING`) nudge and continue.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `request` | [SeatRequest](../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `solo_continue` {#solo_continue}

```python
solo_continue(self, state: dict) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L159-L161)

The 'keep going, answer when ready' user nudge appended after a non-final solo turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_final_cap` {#solo_final_cap}

```python
solo_final_cap(self, state: dict) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L185-L187)

Per-turn output cap for the forced-final solo turn.

Default: 2048.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_final_prompt` {#solo_final_prompt}

```python
solo_final_prompt(self, state: dict) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L163-L165)

The 'budget reached — answer NOW' user prompt for the forced-final solo turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_finalize` {#solo_finalize}

```python
solo_finalize(self, state: dict, answer, text: str) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L173-L175)

Commit `answer` (from a genuine final turn) to state.

The base sets `done` afterwards.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `answer` |  | *required* |  |
| `text` | `str` | *required* |  |

## `solo_give_up` {#solo_give_up}

```python
solo_give_up(self, state: dict) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L177-L179)

Commit a no-answer outcome when the forced-final turn produced no valid answer.

Base sets `done`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_parse` {#solo_parse}

```python
solo_parse(self, state: dict, text: str) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L167-L171)

Parse one solo turn -> `(parsed, parse_ok, has_final, answer)`: `parsed` is the extracted JSON, `parse_ok` the value logged as the turn's `parse_ok`, `has_final` whether the turn committed a final answer, and `answer` the finalized value passed to `solo_finalize` (may itself be `None`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |
| `text` | `str` | *required* |  |

## `solo_requests` {#solo_requests}

```python
solo_requests(self, state: dict) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L189-L206)

The solo arm's `next_requests`: forced-final on budget exhaustion (once), else seed the task on the first call and emit a working turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_system` {#solo_system}

```python
solo_system(self, state: dict) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L151-L153)

The solo seat's system prompt (full-info framing).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_task` {#solo_task}

```python
solo_task(self, state: dict) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L155-L157)

The initial user task text seeding the solo conversation (all private info + the question).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

## `solo_work_cap` {#solo_work_cap}

```python
solo_work_cap(self, state: dict) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenario.py#L181-L183)

Per-turn output cap for a solo working turn.

Default: `solo_turn_cap` cell knob, else 900.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

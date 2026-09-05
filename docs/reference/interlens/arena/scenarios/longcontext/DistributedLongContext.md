# `DistributedLongContext`

```python
DistributedLongContext(adapter: TaskAdapter, name: str | None = None)
```

Defined in [`interlens.arena.scenarios.longcontext`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L93-L409)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `adapter` | [TaskAdapter](TaskAdapter.md) | *required* |  |
| `name` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `SOLO_CEILING` |  |  |
| `SOLO_SYS` |  |  |
| `adapter` |  |  |
| `has_solo` |  |  |
| `name` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L214-L276)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `req` | [SeatRequest](../../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `classify_outcome` {#classify_outcome}

```python
classify_outcome(self, st, turns, outcome) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L364-L384)

Truncation + capitulation classification.

Pure in `(turns, outcome, instance)`, so the engine
applies it live and `replay` recomputes it exactly on stored records.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `turns` |  | *required* |  |
| `outcome` |  | *required* |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L102-L104)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L160-L165)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `next_requests` {#next_requests}

```python
next_requests(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L174-L212)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L279-L297)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L408-L409)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L356-L361)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_provisional_text` {#score_provisional_text}

```python
score_provisional_text(self, st, text: str) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L299-L304)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` | `str` | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L167-L171)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_continue` {#solo_continue}

```python
solo_continue(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L327-L329)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_final_cap` {#solo_final_cap}

```python
solo_final_cap(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L339-L340)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_final_prompt` {#solo_final_prompt}

```python
solo_final_prompt(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L331-L333)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_finalize` {#solo_finalize}

```python
solo_finalize(self, st, answer, text) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L347-L350)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `answer` |  | *required* |  |
| `text` |  | *required* |  |

## `solo_give_up` {#solo_give_up}

```python
solo_give_up(self, st) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L352-L353)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_parse` {#solo_parse}

```python
solo_parse(self, st, text) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L342-L345)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` |  | *required* |  |

## `solo_system` {#solo_system}

```python
solo_system(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L319-L320)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_task` {#solo_task}

```python
solo_task(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L322-L325)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_work_cap` {#solo_work_cap}

```python
solo_work_cap(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L335-L337)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, st, si: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/longcontext.py#L151-L157)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `si` | `int` | *required* |  |

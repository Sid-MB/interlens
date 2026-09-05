# `InfoRelay`

```python
InfoRelay()
```

Defined in [`interlens.arena.scenarios.relay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L348-L688)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `SOLO_SYS` |  |  |
| `has_solo` |  |  |
| `name` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L552-L599)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `req` | [SeatRequest](../../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L354-L439)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L480-L514)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `messaging_finalizable` {#messaging_finalizable}

```python
messaging_finalizable(self) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L665-L668)

The protocol ends in the finalizer's single `{"answer": ...}`, so a messaging episode reduces to that final action (the deciding seat is the default first seat, the finalizer).

## `next_requests` {#next_requests}

```python
next_requests(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L523-L550)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L602-L618)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L687-L688)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L671-L685)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, st, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L620-L625)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `parsed` |  | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L516-L520)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_continue` {#solo_continue}

```python
solo_continue(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L645-L646)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_final_prompt` {#solo_final_prompt}

```python
solo_final_prompt(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L648-L649)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_finalize` {#solo_finalize}

```python
solo_finalize(self, st, answer, text) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L657-L659)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L661-L662)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_parse` {#solo_parse}

```python
solo_parse(self, st, text) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L651-L655)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` |  | *required* |  |

## `solo_system` {#solo_system}

```python
solo_system(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L636-L637)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_task` {#solo_task}

```python
solo_task(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L639-L643)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, st, si: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/relay.py#L467-L477)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `si` | `int` | *required* |  |

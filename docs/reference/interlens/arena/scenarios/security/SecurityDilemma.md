# `SecurityDilemma`

```python
SecurityDilemma()
```

Defined in [`interlens.arena.scenarios.security`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L76-L314)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `PROVISIONAL_MARKS` |  |  |
| `default_communication` |  |  |
| `has_solo` |  |  |
| `name` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L182-L211)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L86-L96)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L141-L149)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L156-L180)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L269-L289)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L313-L314)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L302-L311)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, st, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L291-L299)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `parsed` |  | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L151-L153)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, st, si: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/security.py#L136-L138)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `si` | `int` | *required* |  |

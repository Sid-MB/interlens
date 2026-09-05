# `CodingCollab`

```python
CodingCollab()
```

Defined in [`interlens.arena.scenarios.coding`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L557-L843)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `PROVISIONAL_MARKS` |  |  |
| `SOLO_SYS` |  |  |
| `has_solo` |  |  |
| `name` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L675-L709)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L564-L599)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L645-L650)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L658-L673)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L712-L729)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L840-L843)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L834-L838)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_from_messaging` {#score_from_messaging}

```python
score_from_messaging(self, instance, transcript, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L742-L752)

Messaging-mode reduction: the latest complete ```python fence anywhere in the sends is the working draft (the same rule as the protocol), scored with the exact sandboxed scorer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` |  | *required* |  |
| `transcript` |  | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, st, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L731-L734)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `parsed` |  | *required* |  |

## `score_provisional_text` {#score_provisional_text}

```python
score_provisional_text(self, st, text: str) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L736-L739)

Full primary scorer on the code fence in a provisional reply.

Pure.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` | `str` | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L652-L655)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, st, si: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/coding.py#L634-L642)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `si` | `int` | *required* |  |

# `Negotiation`

```python
Negotiation()
```

Defined in [`interlens.arena.scenarios.negotiation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L162-L598)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `SOLO_SEAT` |  |  |
| `has_solo` |  |  |
| `name` |  |  |

## Methods {#methods}

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L422-L468)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `req` | [SeatRequest](../../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int, coherent: bool = True) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L221-L228)

The 6-party difficulty-ladder generator.

`coherent=True` (default) enforces per-role
sign/monotonicity on each seat's issue scores per the role-prior table — a seat's own-best option never
falls in its role's disfavored set. `coherent=False` reproduces the original (incoherent) generator;
either way the seeded payload is deterministic. (The ladder's historical threshold scan starts at 30;
the sweep generator's at 25 — both preserved so stored instances regenerate exactly.)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `coherent` | `bool` | `True` |  |

## `generate_instance_n` {#generate_instance_n}

```python
generate_instance_n(self, n_parties: int, seed: int, coherent: bool = False) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L230-L236)

The party-count sweep generator: n parties over the fixed issue set, feasible-set FRACTION held at the base ladder's L0 bucket (so party count is not confounded with deal-space size).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_parties` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `coherent` | `bool` | `False` |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L308-L327)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | [Instance](../../schema/Instance.md) | *required* |  |
| `arm` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `cfg` | `dict \| None` | `None` |  |

## `messaging_decider` {#messaging_decider}

```python
messaging_decider(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L554-L556)

The proposer registers the final binding proposal, so its last fenced `proposal` decides.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `messaging_finalizable` {#messaging_finalizable}

```python
messaging_finalizable(self) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L549-L552)

The protocol ends in the proposer's single binding proposal, so a messaging episode reduces to that final action.

## `next_requests` {#next_requests}

```python
next_requests(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L340-L362)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L478-L493)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L597-L598)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L567-L595)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, st, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L495-L499)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `parsed` |  | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L329-L337)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_continue` {#solo_continue}

```python
solo_continue(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L529-L530)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_final_prompt` {#solo_final_prompt}

```python
solo_final_prompt(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L532-L533)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_finalize` {#solo_finalize}

```python
solo_finalize(self, st, answer, text) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L541-L543)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L545-L546)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_parse` {#solo_parse}

```python
solo_parse(self, st, text) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L535-L539)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` |  | *required* |  |

## `solo_system` {#solo_system}

```python
solo_system(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L506-L515)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_task` {#solo_task}

```python
solo_task(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L517-L527)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `system_prompt` {#system_prompt}

```python
system_prompt(self, st, si: int) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/negotiation.py#L285-L305)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `si` | `int` | *required* |  |

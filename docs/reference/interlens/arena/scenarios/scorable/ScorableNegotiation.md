# `ScorableNegotiation`

The repaired scorable-negotiation protocol over a :class:`GameSpec` (see the module docstring).

```python
ScorableNegotiation(
	scaffold: PromptScaffold | None = None,
	oracles: list[Oracle] | None = None,
	turn_max_tokens: int | None = None,
)
```

Defined in [`interlens.arena.scenarios.scorable`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L70-L1000)

**Inherits from:** [Scenario](../../scenario/Scenario.md)

Parameters
----------
scaffold : PromptScaffold
        The prompt wording (one canonical config; ablate by passing a variant). Defaults to
        :data:`~interlens.arena.scenarios.scorable_prompts.DEFAULT_SCAFFOLD`.
oracles : list[Oracle] | None
        Rational-reference oracles run inline after every turn (:meth:`annotate_turn`) to score the seat's actual
        move against the oracle's best — the per-turn regret series. `None` runs no oracles (episodes still
        carry the full move ledger for post-hoc annotation via :meth:`oracle_inputs`).
turn_max_tokens : int | None
        Raise every request's per-turn output cap to at least this many tokens. `None` (the default) leaves the
        protocol's own caps — 2048 on ordinary turns, 2560 on the forced final — exactly as every frozen campaign
        ran them. This is the ONLY hook for the budget, because the engine's `turn_cap` can only ever SHRINK a
        request's cap (:meth:`interlens.arena.engine.EpisodeRun.turn_cap`), so a per-turn budget large enough for
        a reasoning stream plus a visible action has to be set where the request is built.

        Setting it is a PROTOCOL CHANGE, not a tuning knob: turn caps censor behaviour, so a run at a raised cap
        does not pair with a run at the default and must not be pooled with one. It exists because of a measured
        failure — with native thinking ON, Qwen3-8B spends the entire 2048 inside `<think>` on ~2/3 of turns
        and Qwen3-32B on 24.4%, and the engine then substitutes `EMPTY_TURN_PLACEHOLDER` for the visible
        action (rational_agents notes 0026/0041). A turn that says nothing is real model behaviour, so no
        fabrication gate catches it; only a cap census does.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scaffold` | [PromptScaffold](../scorable_prompts/PromptScaffold.md) \| None | `None` |  |
| `oracles` | list[[Oracle](../../oracles/Oracle.md)] \| None | `None` |  |
| `turn_max_tokens` | `int \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `N_LEVELS` |  |  |
| `SOLO_CEILING` |  |  |
| `SOLO_SEAT` |  |  |
| `default_communication` |  |  |
| `has_solo` |  |  |
| `name` |  |  |
| `oracles` |  |  |
| `scaffold` |  |  |
| `turn_max_tokens` |  |  |

## Methods {#methods}

## `annotate_turn` {#annotate_turn}

```python
annotate_turn(self, st, req, turn) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L813-L826)

Inline per-turn oracle annotations (engine hook): score the seat's ACTUAL move against each oracle's best on the pre-move decision point captured in :meth:`_commit`.

`agent` is the seat INDEX (the
unambiguous key into `game.sheets`, matching `PolicyParticipant(seat=int)`; the oracles accept it
as-is); the record's `seat` is the display persona (what the analysis layer reads). No-op when no
oracles are attached.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `req` |  | *required* |  |
| `turn` |  | *required* |  |

## `apply` {#apply}

```python
apply(self, st, req: SeatRequest, text: str) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L538-L586)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `req` | [SeatRequest](../../schema/SeatRequest.md) | *required* |  |
| `text` | `str` | *required* |  |

## `generate_instance` {#generate_instance}

```python
generate_instance(self, level: int, seed: int, **overrides={}) -> Instance
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L113-L123)

One solver-verified instance at difficulty `level` from `seed`, delegated to the game-theory generator+bridge (`interlens.arena.negotiation.generate.generate_instance`) — the single owner of the difficulty ladder, the score-sheet-design knobs (Pareto slack / feasible size / sparsity-IoU), the per-round discount, and the `(GameSpec, analysis) -> Instance` wrap (`payload` = `GameSpec.to_json`, `solution` = the enumeration-verified `analyze` dict).

`overrides` pass straight through (e.g.
`info="private"`, `n_parties`, `dominated_target`, `discount`), so `run.py` and the
`instances/` bank all call one code path. Scoring recomputes the surplus ceiling itself, so it is
independent of the bridge's ceiling/floor convention.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `level` | `int` | *required* |  |
| `seed` | `int` | *required* |  |
| `overrides` |  | `{}` |  |

## `make_state` {#make_state}

```python
make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L132-L206)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L472-L473)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `oracle_inputs` {#oracle_inputs}

```python
oracle_inputs(self, st) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L828-L839)

The per-turn `(game, agent, history, legal_actions)` context for the seat about to move — the same shape the oracles consume, exposed for POST-HOC annotation (replay to a turn, then call this).

`None`
when no team turn is pending (solo / done). Inline annotation during a live run uses :meth:`annotate_turn`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `provisional_due` {#provisional_due}

```python
provisional_due(self, st) -> list[SeatRequest]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L761-L762)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `rounds_used` {#rounds_used}

```python
rounds_used(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L999-L1000)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score` {#score}

```python
score(self, st) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L922-L997)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `score_provisional` {#score_provisional}

```python
score_provisional(self, st, parsed) -> float | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L785-L789)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `parsed` |  | *required* |  |

## `seat_specs` {#seat_specs}

```python
seat_specs(self, st) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L268-L274)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_continue` {#solo_continue}

```python
solo_continue(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L864-L865)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_final_prompt` {#solo_final_prompt}

```python
solo_final_prompt(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L867-L868)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_finalize` {#solo_finalize}

```python
solo_finalize(self, st, answer, text: str) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L881-L883)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `answer` |  | *required* |  |
| `text` | `str` | *required* |  |

## `solo_give_up` {#solo_give_up}

```python
solo_give_up(self, st) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L885-L887)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_parse` {#solo_parse}

```python
solo_parse(self, st, text: str) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L870-L879)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |
| `text` | `str` | *required* |  |

## `solo_system` {#solo_system}

```python
solo_system(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L845-L859)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_task` {#solo_task}

```python
solo_task(self, st) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L861-L862)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

## `solo_work_cap` {#solo_work_cap}

```python
solo_work_cap(self, st) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/scorable.py#L889-L890)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `st` |  | *required* |  |

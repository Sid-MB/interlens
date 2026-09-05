# `DifficultyRatchet`

Probe -> measure -> paired-solo driver over one scenario/participant pair (see the module docstring).

```python
DifficultyRatchet(
	scenario: Scenario,
	participant,
	pool: EpisodePool,
	*,
	instances_dir: str | Path,
	state_path: str | Path,
	arm: str = 'team',
	probe_n: int = PROBE_N,
	meas_n: int = MEAS_N,
	step_up: float = STEP_UP,
	speculative: bool = False,
	wave: int = 3,
	cfg: dict | None = None,
	gen_config: dict | None = None,
	estimated_cost: float | None = None,
	solo_budget_default: int = 4000,
	seed0: int = 1000,
)
```

Defined in [`interlens.arena.ratchet`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/ratchet.py#L70-L243)

`pool` supplies the store (episode persistence + resume dedup) and optional `UsageMeter` (spend
gating: each phase stops launching once the meter is exhausted; in-flight episodes finish).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `participant` |  | *required* |  |
| `pool` | [EpisodePool](../engine/EpisodePool.md) | *required* |  |
| `instances_dir` | `str \| Path` | *required* |  |
| `state_path` | `str \| Path` | *required* |  |
| `arm` | `str` | `'team'` |  |
| `probe_n` | `int` | `PROBE_N` |  |
| `meas_n` | `int` | `MEAS_N` |  |
| `step_up` | `float` | `STEP_UP` |  |
| `speculative` | `bool` | `False` |  |
| `wave` | `int` | `3` |  |
| `cfg` | `dict \| None` | `None` |  |
| `gen_config` | `dict \| None` | `None` |  |
| `estimated_cost` | `float \| None` | `None` |  |
| `solo_budget_default` | `int` | `4000` |  |
| `seed0` | `int` | `1000` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arm` |  |  |
| `estimated_cost` |  |  |
| `instances_dir` |  |  |
| `model` |  |  |
| `participant` |  |  |
| `pool` |  |  |
| `scenario` |  |  |
| `seed0` |  |  |
| `solo_budget_default` |  |  |
| `state` |  |  |
| `state_path` |  |  |

## Methods {#methods}

## `run` {#run}

```python
run(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/ratchet.py#L225-L243)

Run (or resume) the ratchet to completion; returns the final state dict.

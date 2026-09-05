# `Episode`

One complete play-through: turns, forked provisional checkpoints, outcome, and usage accounting.

```python
Episode(
	episode_id: str,
	scenario: str,
	arm: str,
	model: str,
	level: int,
	instance_id: str,
	seed: int,
	seats: list[dict],
	cell: str = 'base',
	cell_cfg: dict = dict(),
	turns: list[TurnRecord] = list(),
	round_checkpoints: list[dict] = list(),
	outcome: dict = dict(),
	rounds_used: int = 0,
	tokens_in: int = 0,
	tokens_out: int = 0,
	cost_usd: float = 0.0,
	gen_config: dict = dict(),
	status: str = 'running',
	error: str | None = None,
	started_at: float = time.time(),
	ended_at: float | None = None,
	schema_version: str = SCHEMA_VERSION,
)
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L196-L256)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `scenario` | `str` | *required* |  |
| `arm` | `str` | *required* |  |
| `model` | `str` | *required* |  |
| `level` | `int` | *required* |  |
| `instance_id` | `str` | *required* |  |
| `seed` | `int` | *required* |  |
| `seats` | `list[dict]` | *required* |  |
| `cell` | `str` | `'base'` |  |
| `cell_cfg` | `dict` | `dict()` |  |
| `turns` | list[[TurnRecord](TurnRecord.md)] | `list()` |  |
| `round_checkpoints` | `list[dict]` | `list()` |  |
| `outcome` | `dict` | `dict()` |  |
| `rounds_used` | `int` | `0` |  |
| `tokens_in` | `int` | `0` |  |
| `tokens_out` | `int` | `0` |  |
| `cost_usd` | `float` | `0.0` |  |
| `gen_config` | `dict` | `dict()` |  |
| `status` | `str` | `'running'` |  |
| `error` | `str \| None` | `None` |  |
| `started_at` | `float` | `time.time()` |  |
| `ended_at` | `float \| None` | `None` |  |
| `schema_version` | `str` | `SCHEMA_VERSION` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arm` | `str` |  |
| `cell` | `str` |  |
| `cell_cfg` | `dict` |  |
| `cost_usd` | `float` |  |
| `ended_at` | `float \| None` |  |
| `episode_id` | `str` |  |
| `error` | `str \| None` |  |
| `gen_config` | `dict` |  |
| `instance_id` | `str` |  |
| `level` | `int` |  |
| `model` | `str` |  |
| `outcome` | `dict` |  |
| `round_checkpoints` | `list[dict]` |  |
| `rounds_used` | `int` |  |
| `scenario` | `str` |  |
| `schema_version` | `str` |  |
| `seats` | `list[dict]` |  |
| `seed` | `int` |  |
| `started_at` | `float` |  |
| `status` | `str` |  |
| `tokens_in` | `int` |  |
| `tokens_out` | `int` |  |
| `turns` | list[[TurnRecord](TurnRecord.md)] |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(cls, d: dict) -> 'Episode'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L231-L245)

Rebuild an episode from a stored record — the inverse of :meth:`to_json`.

`to_json` is `dataclasses.asdict`, so `turns` comes back as plain dicts and is rehydrated through
:meth:`TurnRecord.from_json`; `round_checkpoints` is stored as dicts by design and stays that way.
Unknown keys are dropped and missing ones take their defaults, so an episode written by a different
schema version loads rather than raising. This exists because anything that reads episodes back — a
post-hoc analysis, or a driver that collected episodes in worker processes and has to reassemble them —
otherwise re-derives the dataclass shape by hand and drifts from it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L228-L229)

## `usage` {#usage}

```python
usage(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L247-L256)

This episode's usage summary: tokens in/out (total and per seat) and dollar cost.

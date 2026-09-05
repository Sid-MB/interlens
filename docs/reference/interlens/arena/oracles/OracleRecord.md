# `OracleRecord`

One per-turn oracle annotation on an episode (the typed replacement for the loose checkpoint dict).

```python
OracleRecord(
	round: int,
	seat: str,
	turn_idx: int = -1,
	oracle: str | None = None,
	chosen_value: float | None = None,
	best_value: float | None = None,
	divergence: float | None = None,
	verdict: dict | None = None,
	flags: list[str] = list(),
	provisional_action: Any = None,
	score: float | None = None,
	content: str | None = None,
)
```

Defined in [`interlens.arena.oracles`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L184-L242)

Two provenances share this record and are distinguished by whether `verdict` is set:

- **inline annotation** (`verdict` present): an :class:`Oracle` scored the seat's ACTUAL move against its
  best on the same state — `divergence` = `best_value - chosen_value` in the oracle's value units.
- **forked provisional probe** (`verdict` absent): the model was re-asked to finalize now on a private
  forked view; `provisional_action` / `score` / `content` capture that probe (the legacy checkpoint
  shape).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `turn_idx` | `int` | `-1` |  |
| `oracle` | `str \| None` | `None` |  |
| `chosen_value` | `float \| None` | `None` |  |
| `best_value` | `float \| None` | `None` |  |
| `divergence` | `float \| None` | `None` |  |
| `verdict` | `dict \| None` | `None` |  |
| `flags` | `list[str]` | `list()` |  |
| `provisional_action` | `Any` | `None` |  |
| `score` | `float \| None` | `None` |  |
| `content` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `best_value` | `float \| None` |  |
| `chosen_value` | `float \| None` |  |
| `content` | `str \| None` |  |
| `divergence` | `float \| None` |  |
| `flags` | `list[str]` |  |
| `oracle` | `str \| None` |  |
| `provisional_action` | `Any` |  |
| `round` | `int` |  |
| `score` | `float \| None` |  |
| `seat` | `str` |  |
| `turn_idx` | `int` |  |
| `verdict` | `dict \| None` |  |

## Methods {#methods}

## `annotation` {#annotation}

```python
annotation(
	cls,
	verdict: OracleVerdict,
	*,
	round: int,
	seat: str,
	oracle: str,
	chosen_action: Any = None,
	turn_idx: int = -1,
) -> 'OracleRecord'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L212-L221)

An inline-oracle record: the seat's `chosen_action` scored against `verdict.best`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `verdict` | [OracleVerdict](OracleVerdict.md) | *required* |  |
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `oracle` | `str` | *required* |  |
| `chosen_action` | `Any` | `None` |  |
| `turn_idx` | `int` | `-1` |  |

## `provisional` {#provisional}

```python
provisional(
	cls,
	*,
	round: int,
	seat: str,
	provisional_action: Any,
	score: float | None,
	content: str | None,
	turn_idx: int = -1,
) -> 'OracleRecord'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L223-L228)

A forked provisional-probe record (the `Scenario.provisional_due` path).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `round` | `int` | *required* |  |
| `seat` | `str` | *required* |  |
| `provisional_action` | `Any` | *required* |  |
| `score` | `float \| None` | *required* |  |
| `content` | `str \| None` | *required* |  |
| `turn_idx` | `int` | `-1` |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/oracles.py#L230-L242)

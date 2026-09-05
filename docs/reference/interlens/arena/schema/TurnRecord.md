# `TurnRecord`

```python
TurnRecord(
	idx: int,
	round: int,
	phase: str,
	seat: str,
	content: str,
	parsed_action: Any,
	parse_ok: bool,
	n_tokens_out: int = 0,
	n_tokens_in: int = 0,
	stop_reason: str | None = None,
	cap: int = 0,
	effective_cap: int | None = None,
	raw: str | None = None,
	reasoning: str | None = None,
	reasoning_provenance: str = 'none',
	reasoning_tokens: int = 0,
	view: list[dict] | None = None,
	gen_failed: bool = False,
	gen_failure: str | None = None,
	refusal_recovery: dict | None = None,
	occupant: str | None = None,
	human_note: str | None = None,
)
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L110-L193)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `idx` | `int` | *required* |  |
| `round` | `int` | *required* |  |
| `phase` | `str` | *required* |  |
| `seat` | `str` | *required* |  |
| `content` | `str` | *required* |  |
| `parsed_action` | `Any` | *required* |  |
| `parse_ok` | `bool` | *required* |  |
| `n_tokens_out` | `int` | `0` |  |
| `n_tokens_in` | `int` | `0` |  |
| `stop_reason` | `str \| None` | `None` |  |
| `cap` | `int` | `0` |  |
| `effective_cap` | `int \| None` | `None` |  |
| `raw` | `str \| None` | `None` |  |
| `reasoning` | `str \| None` | `None` |  |
| `reasoning_provenance` | `str` | `'none'` |  |
| `reasoning_tokens` | `int` | `0` |  |
| `view` | `list[dict] \| None` | `None` |  |
| `gen_failed` | `bool` | `False` |  |
| `gen_failure` | `str \| None` | `None` |  |
| `refusal_recovery` | `dict \| None` | `None` |  |
| `occupant` | `str \| None` | `None` |  |
| `human_note` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `cap` | `int` |  |
| `content` | `str` |  |
| `effective_cap` | `int \| None` |  |
| `gen_failed` | `bool` |  |
| `gen_failure` | `str \| None` |  |
| `human_note` | `str \| None` |  |
| `idx` | `int` |  |
| `n_tokens_in` | `int` |  |
| `n_tokens_out` | `int` |  |
| `occupant` | `str \| None` |  |
| `parse_ok` | `bool` |  |
| `parsed_action` | `Any` |  |
| `phase` | `str` |  |
| `raw` | `str \| None` |  |
| `reasoning` | `str \| None` |  |
| `reasoning_provenance` | `str` |  |
| `reasoning_tokens` | `int` |  |
| `refusal_recovery` | `dict \| None` |  |
| `round` | `int` |  |
| `seat` | `str` |  |
| `stop_reason` | `str \| None` |  |
| `view` | `list[dict] \| None` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(cls, d: dict) -> 'TurnRecord'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L185-L193)

Rebuild a turn from its stored dict, ignoring fields this version does not know.

Forward-compatible on purpose: a record written by a newer schema carries keys this dataclass has no
field for, and dropping them is the only way an older reader can load a newer file at all. Missing
keys fall back to the field defaults, which is what makes pre-v1.2 episodes load unchanged.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

# `ParseResult`

The outcome of reading one formal action from a model's turn.

```python
ParseResult(
	action: Action | None = None,
	ok: bool = False,
	error: str | None = None,
	error_kind: str | None = None,
	raw: Any = None,
)
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L295-L323)

`ok` with an `action` on success; on failure `action` is `None`, `error` is a specific,
model-facing message for the one retry, and `error_kind` is :data:`SYNTAX` or :data:`LEGALITY` — the two
failure classes the arena logs separately as data (AucArena's retry-once pattern).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](Action.md) \| None | `None` |  |
| `ok` | `bool` | `False` |  |
| `error` | `str \| None` | `None` |  |
| `error_kind` | `str \| None` | `None` |  |
| `raw` | `Any` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `action` | [Action](Action.md) \| None |  |
| `error` | `str \| None` |  |
| `error_kind` | `str \| None` |  |
| `ok` | `bool` |  |
| `raw` | `Any` |  |

## Methods {#methods}

## `bad` {#bad}

```python
bad(kind: str, error: str, raw: Any = None) -> 'ParseResult'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L313-L315)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `kind` | `str` | *required* |  |
| `error` | `str` | *required* |  |
| `raw` | `Any` | `None` |  |

## `good` {#good}

```python
good(action: Action, raw: Any = None) -> 'ParseResult'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L309-L311)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](Action.md) | *required* |  |
| `raw` | `Any` | `None` |  |

## `retry_directive` {#retry_directive}

```python
retry_directive(self) -> dict | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L317-L323)

`{'retry': <error>, 'error_kind': <kind>}` on failure (the scenario returns this from `apply` to trigger the engine's one re-prompt), else `None`.

The engine reads `'retry'`; `'error_kind'` rides
along for logging.

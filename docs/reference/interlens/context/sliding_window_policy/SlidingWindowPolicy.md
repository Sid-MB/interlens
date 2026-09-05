# `SlidingWindowPolicy`

Keep the preserved framing plus the most recent `keep_last` turns; drop older turns.

```python
SlidingWindowPolicy(keep_last: int, keep_system: bool = True)
```

Defined in [`interlens.context.sliding_window_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/sliding_window_policy.py#L22-L48)

**Inherits from:** [ContextPolicy](../context_policy/ContextPolicy.md)

`keep_system=True` (the default) preserves the system/moderator/private_context framing regardless of the
window; set it False to also let framing fall outside the window (rarely wanted). Unlike `DropOldestPolicy`
this is a fixed-size window rather than a fit-to-budget trim, so it's predictable turn-to-turn.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `keep_last` | `int` | *required* |  |
| `keep_system` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `keep_last` |  |  |
| `keep_system` |  |  |

## Methods {#methods}

## `fit` {#fit}

```python
fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/sliding_window_policy.py#L37-L48)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `segments` | list[[ViewSegment](../../view/ViewSegment.md)] | *required* |  |
| `tokenizer` |  | *required* |  |
| `limit` | `int \| None` | *required* |  |

## `to_dict` {#to_dict}

```python
to_dict(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/sliding_window_policy.py#L34-L35)

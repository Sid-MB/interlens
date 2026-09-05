# `ContextPolicy`

Decides how to fit a participant's view within its model's context window.

```python
ContextPolicy()
```

Defined in [`interlens.context.context_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/context_policy.py#L28-L61)

**Inherits from:** `ABC`

Crucially, `fit` runs on the **typed** `ViewSegment` list, *before* the family-specific `finalize_view`
folds/merges anything. Operating pre-finalize means the policy can reliably preserve the system block and
moderator seed (their `origin` is still intact) and trim only `turn` segments, instead of trying to
reverse-engineer meaning out of already-folded text.

## Methods {#methods}

## `fit` {#fit}

```python
fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/context_policy.py#L37-L39)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/context_policy.py#L41-L44)

Serialize as `{"kind": ..., **params}`.

Subclasses with parameters extend the params; the default
covers parameterless policies.

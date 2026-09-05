# `SummarizePolicy`

Compress older turns into a single summary segment instead of dropping them outright (the heaviest policy).

```python
SummarizePolicy(keep_last: int = 4, summarizer=None)
```

Defined in [`interlens.context.summarize_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/summarize_policy.py#L22-L62)

**Inherits from:** [ContextPolicy](../context_policy/ContextPolicy.md)

Keeps the preserved framing (system / moderator / private_context) and the most recent `keep_last` turns
verbatim, and replaces the older middle turns with one summary segment produced by `summarizer` — a
callable `list[str] -> str` over the dropped turns' contents. With no summarizer it inserts a neutral
placeholder, so it degrades to a labelled drop rather than silently losing content.

`summarizer` is a live callable and so is not serialized; a loaded template gets `summarizer=None` and
the caller re-injects one if needed.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `keep_last` | `int` | `4` |  |
| `summarizer` |  | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `keep_last` |  |  |
| `summarizer` |  |  |

## Methods {#methods}

## `fit` {#fit}

```python
fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/summarize_policy.py#L47-L62)

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/summarize_policy.py#L39-L40)

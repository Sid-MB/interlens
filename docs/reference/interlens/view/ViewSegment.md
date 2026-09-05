# `ViewSegment`

One entry in a participant's *structured* view, before it is flattened to the `[{role, content}]` shape a chat template consumes.

```python
ViewSegment(role: Role, content: str, origin: Origin, author: str | None = None)
```

Defined in [`interlens.view`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/view.py#L29-L46)

Carrying `origin` (and `author` for turns) through the pipeline is the whole point: it keeps the
semantic identity of each piece intact so context-trimming and author-labelling can act on it, rather than
reverse-engineering meaning out of already-folded text.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `role` | `Role` | *required* |  |
| `content` | `str` | *required* |  |
| `origin` | `Origin` | *required* |  |
| `author` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `author` | `str \| None` |  |
| `content` | `str` |  |
| `origin` | `Origin` |  |
| `role` | `Role` |  |

## Methods {#methods}

## `as_message` {#as_message}

```python
as_message(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/view.py#L44-L46)

Flatten to the `{"role", "content"}` dict a chat template expects.

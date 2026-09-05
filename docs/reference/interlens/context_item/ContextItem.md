# `ContextItem`

A single item of *private* asymmetric knowledge given to one participant (a briefing, a document, a fact).

```python
ContextItem(content: str, role_hint: Role = 'user', author: str = 'moderator')
```

Defined in [`interlens.context_item`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context_item.py#L23-L38)

Deliberately distinct from `Message`: a briefing is not a dialogue turn — it has no turn index and its
`author` is nominal — so overloading `Message` would give it misleading turn/authorship semantics.

Role semantics are pinned rather than role-swapped: a briefing renders by default as **user-provided
context** (`role_hint=USER`) — the participant reads it as information handed to it, not as its own prior
speech — with `SYSTEM` available for standing private instructions. Private context is injected only into
the owning participant's view and never enters the shared transcript.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `content` | `str` | *required* |  |
| `role_hint` | `Role` | `'user'` |  |
| `author` | `str` | `'moderator'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `author` | `str` |  |
| `content` | `str` |  |
| `role_hint` | `Role` |  |

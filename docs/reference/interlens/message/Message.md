# `Message`

A single committed turn in a conversation.

```python
Message(author: str, content: str, metadata: dict = dict())
```

Defined in [`interlens.message`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/message.py#L19-L39)

The transcript is stored canonically and author-centric: a message records *who* said *what*, and is
deliberately agnostic to the `assistant`/`user` role distinction. That role mapping is a per-participant
*view* concern (see `Transcript.render_roles`), not a property of the message itself — so one transcript can
be rendered from every participant's perspective without duplicating state.

`author` is the participant's `name` (a string), never the `Participant` object. This keeps transcripts
trivially JSON-serializable and valid even when no models are loaded (e.g. when scoring saved transcripts).

`content` is the committed, visible text — the only field that is authoritative for rendering history back
into a model. Anything else a generation produced (parsed `<think>` reasoning, the raw completion, tool
call/result trails, per-token logprobs) lives in `metadata` under neutral keys, so hidden generated text is
never silently promoted into what other participants see.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `author` | `str` | *required* |  |
| `content` | `str` | *required* |  |
| `metadata` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `author` | `str` |  |
| `content` | `str` |  |
| `metadata` | `dict` |  |

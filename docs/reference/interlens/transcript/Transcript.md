# `Transcript`

The canonical, perspective-neutral record of a conversation, plus the logic to render it *from* a given participant's perspective.

```python
Transcript(messages: list[Message] = list())
```

Defined in [`interlens.transcript`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L75-L274)

Design: the transcript never commits to `assistant`/`user` roles. Each message just knows its `author`.
When it's a participant's turn, `render_roles` maps that neutral record into the chat-template `[{role,
content}]` shape *from that participant's point of view* — its own turns become `self_role` (normally
`assistant`), everyone else's become `others_role` (normally `user`). This single trick is why two
different models with different tokenizers can share one transcript: each gets the view its own template
expects, and the stored record stays singular.

P0 scope: this holds only the message list + rendering + list-like ergonomics. Serialization, context
policies, author-labelling for N-party, and reasoning re-injection are layered on in later phases.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `messages` | list[[Message](../message/Message.md)] | `list()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `messages` | list[[Message](../message/Message.md)] |  |

## Methods {#methods}

## `append` {#append}

```python
append(self, author: str, content: str, **metadata={}) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L93-L98)

Append a committed turn and return it.

`metadata` captures anything non-authoritative (parsed
reasoning, logprobs, tool trails) without polluting `content`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `author` | `str` | *required* |  |
| `content` | `str` | *required* |  |
| `metadata` |  | `{}` |  |

## `clear` {#clear}

```python
clear(self) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L203-L211)

Drop **every** turn, returning `self`.

⚠️ This wipes the whole record, including any leading seed turn — the `shared_context` scenario framing and
any moderator/initial-instruction turns injected at construction. Nothing about the conversation's opening
setup survives. If you want to clear the *dialogue* but keep that framing (e.g. to rerun the same scenario),
call `Conversation.reset` instead, which empties and then re-seeds the `shared_context` turn.

## `copy` {#copy}

```python
copy(self) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L158-L161)

Deep-ish copy of the message list for branching.

Messages are small string records, so this is cheap;
the invariant that keeps it cheap is that heavy tensors never live in `Message.metadata`.

## `edit` {#edit}

```python
edit(
	self,
	ref: 'MessageRef',
	content: str | None = None,
	*,
	author: str | None = None,
	**metadata={},
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L213-L226)

Edit a committed past turn in place and return it.

`ref` is a `MessageRef` (int index, negatives
allowed, or a `Message` object matched by identity). Only the arguments you pass are changed: `content`
and/or `author` are replaced when given; `metadata` keys are merged over the existing metadata (pass an
explicit key to overwrite it — untouched keys are left alone). Editing the `Message` object's fields
directly does the same thing, since the transcript holds it by reference.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ref` | `'MessageRef'` | *required* |  |
| `content` | `str \| None` | `None` |  |
| `author` | `str \| None` | `None` |  |
| `metadata` |  | `{}` |  |

## `from_dict` {#from_dict}

```python
from_dict(cls, data: dict) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L263-L266)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `data` | `dict` | *required* |  |

## `load` {#load}

```python
load(cls, path: str | Path) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L271-L274)

Load a transcript from disk.

Works with no models present (for scoring/analysis of saved runs).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |

## `pretty` {#pretty}

```python
pretty(self, metadata: bool = False) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L228-L238)

A human-readable dump for debugging: one `[i] author: content` block per turn.

With `metadata=True`,
also list each turn's non-empty metadata (parsed reasoning, tool trail, token counts, …). Also what
`str(transcript)` / `print(transcript)` uses (without metadata).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `metadata` | `bool` | `False` |  |

## `render_roles` {#render_roles}

```python
render_roles(self, *, pov: 'Participant') -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L115-L131)

Render **the transcript turns only** as `[{"role", "content"}]` from `pov`'s perspective (`pov` is keyword-only: `render_roles(pov=alice)`).

Its own turns become `self_role` (normally `assistant`),
everyone else's become `others_role` (normally `user`). For a "what if X had just been said" render,
extend first with `with_extra` and render the result.

**Limitation — this is NOT what the model actually sees.** The `Transcript` is the perspective-neutral
record; it knows nothing about a participant's `system_prompt` / `private_context`, the conversation's
`shared_system_prompt` / `shared_context` framing, the `context_policy` fitting, or the family-specific
flatten (Gemma system-folding etc.). Those are added by the `Conversation` pipeline. For the **real**
generation input use `Conversation.view(pov)` (or `Conversation.render_templated(pov)` for the templated
string); use this method for lower-level inspection of the record itself.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pov` | `'Participant'` | *required* |  |

## `render_templated` {#render_templated}

```python
render_templated(
	self,
	*,
	pov: 'ModelParticipant',
	add_generation_prompt: bool = False,
	tokenize: bool = False,
)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L133-L156)

Template **the transcript turns only** from `pov`'s point of view — i.e. `render_roles` role-swapped, then run through `pov`'s tokenizer chat template so the special / control tokens (`<|im_start|>assistant` etc.) are included.

`pov` is keyword-only: call `render_templated(pov=alice)`. Returns a str
(`tokenize=False`, default) or token ids (`tokenize=True`); `add_generation_prompt` appends the
assistant open tag.

**Prefer `Conversation.render_templated` if you have access to a conversation**: it adds the system prompt, private context, context-fitting, and family-specific flattening, printing the exact input models see.

**Limitations**

**NOT the exact model input.** This omits the system prompt, private context, context-fitting,
and the family-specific flatten that a real turn also gets (see `render_roles`); it also renders the raw
role-swapped turns as-is, which can even *raise* for families needing strict alternation / system-folding
(e.g. Gemma) since the merge isn't applied. For the **exact, family-correct prompt the model actually sees**,
use `Conversation.render_templated(pov)`. This method is a lower-level inspection of the record. Requires a
local model participant (with a tokenizer); an API participant has none and raises.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pov` | `'ModelParticipant'` | *required* |  |
| `add_generation_prompt` | `bool` | `False` |  |
| `tokenize` | `bool` | `False` |  |

## `resolve_index` {#resolve_index}

```python
resolve_index(self, ref: 'MessageRef') -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L170-L184)

Normalize a message reference to a concrete `[0, len)` position.

`ref` is either an `int` index
(Python semantics — negatives count from the end, `-1` = last turn) or a `Message` **object**, located
by identity (`is`, not equality — two turns with the same text are still distinct). Raises `IndexError`
for an out-of-range int and `ValueError` for a message that isn't in this transcript.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ref` | `'MessageRef'` | *required* |  |

## `rewind` {#rewind}

```python
rewind(self, *, to: 'MessageRef') -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L196-L201)

Rewind so the turn referenced by `to` becomes the new last turn — i.e. drop everything **after** it, keeping `to` itself (mutates in place, returns `self`).

`to` is a `MessageRef`: an `int` index
(negatives count from the end — `rewind(to=-2)` takes back the single last turn) or a `Message` object
matched by identity. To drop all turns use `clear`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `to` | `'MessageRef'` | *required* |  |

## `save` {#save}

```python
save(self, path: str | Path) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L268-L269)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| Path` | *required* |  |

## `to_dict` {#to_dict}

```python
to_dict(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L257-L261)

## `truncate` {#truncate}

```python
truncate(self, length: int) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L186-L194)

Keep only the first `length` turns, dropping everything after (mutates in place, returns `self`).

`length` is a *count*, clamped to `[0, len]`: over-long values are a no-op and negatives count from the
end (`-1` keeps all but the last turn). To cut relative to a specific message, use `resolve_index` /
`rewind(to=…)` instead.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `length` | `int` | *required* |  |

## `with_extra` {#with_extra}

```python
with_extra(self, *extra: Message = ()) -> 'Transcript'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/transcript.py#L100-L113)

Return a lightweight, ephemeral **read-only** `Transcript` = this one's messages followed by `extra`, backed by a lazy concatenation (`_ConcatMessages`): the base message list is **not copied** — only `extra` is materialized, so this is O(len(extra)), not O(len(transcript)), and `Message` objects are shared by reference.

The original is untouched.

This is the data-layer primitive behind ephemeral sampling ("what would a participant say if `extra` had
just been said?"): build the extended transcript, render it, discard it —
`transcript.with_extra(Message("bob", "…")).render_roles(pov=alice)`. The result is read-only (rendering,
`len`, indexing, iteration all work; appending raises — `copy()` first if you need a mutable one).

(A one-shot generator was rejected: `Transcript` needs `len` / indexing / repeated iteration, which a
generator can't provide.)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `extra` | [Message](../message/Message.md) | `()` |  |

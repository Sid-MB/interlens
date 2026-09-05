# `Participant`

A participant in a conversation, either a model or a person.

```python
Participant()
```

Defined in [`interlens.participant.participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participant.py#L25-L190)

**Inherits from:** `ABC`

A participant owns three things: an *identity* within the conversation (`name` + `self_role`/
`others_role`), its *private framing* (`system_prompt` + `private_context` — instructions/knowledge
only it sees), and the ability to turn a rendered view into its next message (`generate`). The
`Conversation` assembles the structured view from the shared transcript; the participant flattens that view
to what its chat template expects via `finalize_view` and generates.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `OPENING_USER_PLACEHOLDER` |  |  |
| `name` | `str` | A name or identifier to uniquely identify this participant within a conversation. |
| `others_role` | `Role` |  |
| `private_context` | `tuple` |  |
| `requires_alternating_roles` | `bool` |  |
| `self_role` | `Role` |  |
| `supports_system_role` | `bool` |  |
| `system_prompt` | `str \| None` |  |

## Methods {#methods}

## `finalize_view` {#finalize_view}

```python
finalize_view(self, segments: list[ViewSegment]) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participant.py#L71-L91)

Flatten the structured, context-fitted view into the `[{role, content}]` list the chat template consumes.

Applies family-specific repairs driven by the capability flags:

- `supports_system_role=False` → fold the leading system content into the first user turn (Gemma-2's
  template errors on a standalone `system` role).
- `requires_alternating_roles=True` → merge consecutive same-role segments (Gemma requires strict
  user/model alternation; the moderator seed + another speaker + private context can otherwise produce
  consecutive `user` turns that the template rejects). Merged turns keep author labels so speaker
  identity isn't lost in the concatenation.

The dict-level tail of the same repairs lives in :meth:`repair_view`, which this delegates to (and which
participants handed an ALREADY-flattened view — arena scenarios build their per-seat views as plain
`[{role, content}]` lists — call directly). Both are idempotent, so running them twice is a no-op.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `segments` | list[[ViewSegment](../../view/ViewSegment.md)] | *required* |  |

## `generate` {#generate}

```python
generate(
	self,
	view: list[dict],
	*,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	turn: int | None = None,
	max_new_tokens: int | None = None,
	seat: str | None = None,
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participant.py#L52-L69)

Produce this participant's next message given `view` — the conversation flattened to `[{"role", "content"}]` from this participant's perspective.

Returns a `Message` it authored.

Interp options apply to local-model participants: `steering` (a `SteeringSpec`), `capture` (a
`CaptureRequest`), `patch` (a `Patch`), and `return_logprobs`; `turn` is the message index used
to tag captured activations. Participants that can't honor an interp request (e.g. API-backed) must raise
rather than silently ignore it — a failed capture/steer must fail loudly.

`seat` is WHICH SEAT this turn is being spoken for, passed by the arena engine straight from
`SeatRequest.seat` (`None` outside the arena, e.g. a plain `Conversation`). Most participants ignore
it — the view already addresses them — but a participant that fronts several seats needs to know which one
it is answering as, and reading that from the request is exact where recovering it from the prompt text is
guesswork that breaks whenever the wording changes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` | `list[dict]` | *required* |  |
| `steering` |  | `None` |  |
| `capture` |  | `None` |  |
| `patch` |  | `None` |  |
| `return_logprobs` | `bool` | `False` |  |
| `turn` | `int \| None` | `None` |  |
| `max_new_tokens` | `int \| None` | `None` |  |
| `seat` | `str \| None` | `None` |  |

## `repair_view` {#repair_view}

```python
repair_view(self, messages: list[dict]) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participant.py#L93-L116)

Apply this family's chat-template repairs to an **already-flattened** `[{role, content}]` view, so a view that never went through :meth:`finalize_view` (an arena scenario builds its per-seat views directly) still renders under a strict template.

Idempotent; a no-op for permissive families (both flags at their
default), which is why every render path can call it unconditionally.

With `requires_alternating_roles` two repairs run, in order:

1. **merge** consecutive same-role turns (joined with a blank line) — a seat that speaks twice in a row
   (the round-boundary/rotation repeat in a multi-party game) otherwise emits two `assistant` turns.
2. **user-first**: a strict template (Gemma, Mistral/Ministral) requires the first turn after the optional
   leading `system` to be `user`, so a view that opens with the seat's OWN turn — the opener of a
   multi-round game, whose first event in the shared log is its own proposal — is repaired by inserting one
   minimal placeholder `user` turn there. Insertion, not re-roling: every existing turn keeps its role
   and text, so a family that renders `system` in its own tokens (Mistral's `[SYSTEM_PROMPT]`) keeps
   that framing, and the seat's own words are never re-attributed to anyone else.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `messages` | `list[dict]` | *required* |  |

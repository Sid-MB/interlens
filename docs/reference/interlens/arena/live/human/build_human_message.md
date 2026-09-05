# `build_human_message`

Turn a validated browser form into the message a human seat plays — the assembly half of the split above.

```python
build_human_message(
	form: dict,
	*,
	name: str,
	space: Any,
	pending: PendingRequest,
) -> Message
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L331-L386)

`form` is the POST body (`{action, deal, offer_id, message, note}`); `space` decodes a named deal;
`pending` supplies the legality rules the submission is checked against. Builds the typed `Action`,
renders it with `arena.actions.action_message` so the envelope matches an LLM seat's exactly, and stamps
`occupant`/`human_note` metadata for the turn record.

Raises `ValueError` with a player-readable message for anything illegal — an unknown option name, an accept
referencing a dead offer, an action the phase does not allow, an empty submission. The caller answers that
with a 400 and an `input_rejected` event; nothing is enqueued.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `form` | `dict` | *required* |  |
| `name` | `str` | *required* |  |
| `space` | `Any` | *required* |  |
| `pending` | [PendingRequest](PendingRequest.md) | *required* |  |

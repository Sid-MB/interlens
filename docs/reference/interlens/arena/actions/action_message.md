# `action_message`

Render `action` as a message body: an optional free-text `preface`, then the fenced `json` action block — the exact envelope an LLM seat produces, so a transcript is symmetric across seat types (a `PolicyParticipant` emits through here).

```python
action_message(
	action: Action,
	space=None,
	*,
	preface: str = '',
	message: str | None = None,
) -> str
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L463-L487)

The action serializes through its own :meth:`Action.to_json` — the ONE action serializer — so `deal` is a
list of option indices. Pass `space` (anything with a `named(deal)` method, i.e. a
:class:`~interlens.arena.negotiation.space.DealSpace`) to render a `Propose`'s deal as
`{issue_name: option_label}` instead, which is what an LLM-legible transcript wants; `DealSpace.parse` is
the inverse when reading one back. `space` is duck-typed, so this module keeps no dependency on the
negotiation package.

`message` puts public cheap talk INSIDE the envelope, under the `"message"` key an LLM seat uses and a
chat-enabled scenario republishes to every other seat. That is the only speaking channel a scripted seat
has: `preface` is free text OUTSIDE the fence, which the scenario's parser never reads, so a preface is
transcript decoration whereas a `message` is an actual public statement. Key order matches the LLM
envelope (message first, then the formal action) so the two are indistinguishable on the wire. A
moves-only game has no talk channel and drops the key, so a speaking policy belongs in a chat arm.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | [Action](Action.md) | *required* |  |
| `space` |  | `None` |  |
| `preface` | `str` | `''` |  |
| `message` | `str \| None` | `None` |  |

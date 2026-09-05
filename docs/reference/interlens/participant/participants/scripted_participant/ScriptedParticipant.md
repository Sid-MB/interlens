# `ScriptedParticipant`

A non-model participant that replies with **pre-written (scripted) messages**, cycled in order — its turns are fixed, NOT generated from the conversation.

```python
ScriptedParticipant(
	name: str,
	scripts: 'str | list[str]',
	*,
	system_prompt: str | None = None,
	private_context: tuple = (),
)
```

Defined in [`interlens.participant.participants.scripted_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/scripted_participant.py#L22-L73)

**Inherits from:** [Participant](../../participant/Participant.md)

The motivating use is a **reliable adversary / pusher**: to measure whether a target model capitulates under
social pressure you need an interlocutor that asserts a specific (often wrong) answer *every* turn. A real
model is a poor adversary for this — aligned/reasoning models frequently refuse to argue a known-wrong answer
and instead re-solve correctly, so the "pressure" silently vanishes (an invisible confound unless you read
transcripts). Scripting the adversary guarantees uniform, controlled pressure and costs no model/API calls.

It ignores the conversation `view` (its replies are fixed) and holds no activations, so it raises on any
interp request (`steering`/`capture`/`patch`/`return_logprobs`) rather than silently ignoring it —
consistent with the `Participant.generate` contract.

Parameters
----------
name : str
    Identifier within the conversation.
scripts : str | list[str]
    The canned message(s). A single string is treated as a one-element list. Turns cycle through the list in
    order (turn `k` emits `scripts[k % len(scripts)]`), so a few varied assertions read less robotically
    than one repeated line while still asserting the same position.
system_prompt : str | None
    Optional system framing (recorded for view/transcript symmetry; the scripted replies don't depend on it).
private_context : tuple
    Optional private context, for parity with other participants (unused by the fixed replies).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `scripts` | `'str | list[str]'` | *required* |  |
| `system_prompt` | `str \| None` | `None` |  |
| `private_context` | `tuple` | `()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` |  |  |
| `others_role` |  |  |
| `private_context` |  |  |
| `scripts` |  |  |
| `self_role` |  |  |
| `system_prompt` |  |  |

## Methods {#methods}

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/scripted_participant.py#L63-L73)

Return the next scripted message (cycled), ignoring `view`.

Raises on interp requests — a scripted
participant has no model/activations to steer, capture, patch, or read logprobs from.

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

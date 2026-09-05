# `HumanParticipant`

A negotiation seat whose moves come from a browser.

```python
HumanParticipant(
	name: str,
	seat: int,
	sheet: Any,
	space: Any,
	deadline: int,
	publisher: Callable[[str, dict], None],
)
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L181-L328)

**Inherits from:** [Participant](../../../participant/participant/Participant.md)

Parameters
----------
name : str
    Identifier within the conversation, and the `human:<name>` occupant label's detail.
seat : int
    This seat's index into the game's seat-indexed sheets/tables.
sheet : object
    This seat's PRIVATE score sheet (`.utility`/`.surplus`/`.threshold`) — shown in the player's dock,
    and shown to nobody else. A human plays under the same information a model seat has.
space : DealSpace
    The shared deal space: the issue/option name table the offer builder is generated from, and the decoder
    (`DealSpace.parse`) a submitted deal is validated with.
deadline : int
    Total rounds `T`, so the dock can say which round of how many is being played.
publisher : callable
    `publisher(event_type, data) -> None` — how the participant announces that it is waiting. Injected
    rather than reaching for the session, so the participant is testable with a list.append.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `seat` | `int` | *required* |  |
| `sheet` | `Any` | *required* |  |
| `space` | `Any` | *required* |  |
| `deadline` | `int` | *required* |  |
| `publisher` | `Callable[[str, dict], None]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `deadline` |  |  |
| `name` |  |  |
| `occupant` | `str` | This seat's occupant label, `human:<name>` — stamped on every message the person plays so the transcript records WHO took the turn, not just which seat it was. |
| `others_role` |  |  |
| `pending` | [PendingRequest](PendingRequest.md) \| None | The open ask, or `None` when this seat is not waiting. |
| `private_context` |  |  |
| `publisher` |  |  |
| `seat` |  |  |
| `self_role` |  |  |
| `sheet` |  |  |
| `space` |  |  |
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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L230-L266)

Ask the person for this turn and block until they answer.

Parses the `negotiation_state` block out of `view`, builds a :class:`PendingRequest`, publishes
`awaiting_human`, then blocks on the inbox with NO timeout — a human thinking is not an error, and a
deadline that fired mid-decision would fabricate a turn nobody played. Returns the `Message` the server
assembled, whose metadata carries `action`, `occupant` (`human:<name>`) and `human_note`.

Raises on any interp request, exactly as `PolicyParticipant` does: there is no model here to steer,
capture, patch or read logprobs from, and silently ignoring the request would corrupt an experiment.

`turn_idx` on the published request is :data:`events.UNKNOWN_TURN_IDX`: the participant does not know
the episode's turn count
(the engine passes `turn` only alongside a capture request), and the SESSION does — it stamps the real
index on the event before broadcasting, the same way it supplies `turn_idx` for `turn_started`,
which the router cannot know either.

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

## `publish` {#publish}

```python
publish(self, request: PendingRequest) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L293-L306)

Announce that this seat is waiting, through the injected publisher.

A publisher that raises must not take the game down with it — the person can still be asked in another
browser tab, and a broadcast failure is a UI problem, not a negotiation one — so the exception is logged
and swallowed, matching how the engine treats its wave observer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `request` | [PendingRequest](PendingRequest.md) | *required* |  |

## `submit` {#submit}

```python
submit(self, message: Message) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L308-L316)

Hand the server-assembled message to the blocked :meth:`generate`.

Called from the HTTP thread.

Refuses when the seat is not waiting: a message queued against a closed prompt would sit in the inbox
and play itself on some LATER turn, under a state the player never saw.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | [Message](../../../message/Message.md) | *required* |  |

## `unblock` {#unblock}

```python
unblock(self, reason: str = 'stopped') -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L318-L321)

Release a blocked :meth:`generate` without a move — the stop path.

Feeds a sentinel that makes
`generate` raise, so a stopped session's episode ends as an error rather than as a fabricated pass.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `reason` | `str` | `'stopped'` |  |

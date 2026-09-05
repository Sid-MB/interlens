# `AuctionPolicyParticipant`

One computable auction seat: an information-conditional best response, plus its templated channel behavior.

```python
AuctionPolicyParticipant(
	name: str,
	*,
	spec: AuctionSpec,
	seat: int,
	information: str = 'private',
	instance_id: str = '',
)
```

Defined in [`interlens.arena.scenarios.auction_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_policy.py#L73-L236)

**Inherits from:** [Participant](../../../participant/participant/Participant.md)

Parameters
----------
name : str
    Participant name recorded on the episode.
spec : AuctionSpec
    The episode spec. Public structure only is read from it; the seat's realized draws arrive through the
    state block, so the same object can back every seat without an information leak by construction.
seat : int
    Seat index.
information : str
    `"private"` (the rational seat: own information only) or `"oracle"` (the same best response with
    everyone's realized private information). This is the ONLY difference between the two arms.
instance_id : str
    Frozen instance id, used to seed the surface variant of every templated line so the variant is
    reproducible and arm-invariant.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `spec` | [AuctionSpec](../../auction/spec/AuctionSpec.md) | *required* |  |
| `seat` | `int` | *required* |  |
| `information` | `str` | `'private'` |  |
| `instance_id` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `information` |  |  |
| `instance_id` |  |  |
| `name` |  |  |
| `others_role` |  |  |
| `policy` |  |  |
| `private_context` |  |  |
| `seat` |  |  |
| `self_role` |  |  |
| `spec` |  |  |
| `system_prompt` |  |  |

## Methods {#methods}

## `generate` {#generate}

```python
generate(
	self,
	view,
	*,
	seat: str | None = None,
	max_new_tokens: int | None = None,
	**kwargs={},
) -> Message
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_policy.py#L109-L120)

Read the state block, compute the move, and emit the envelope an LLM seat would have written.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `view` |  | *required* |  |
| `seat` | `str \| None` | `None` |  |
| `max_new_tokens` | `int \| None` | `None` |  |
| `kwargs` |  | `{}` |  |

# `PolicyParticipant`

A pure-Python negotiation seat driven by a bound `policy`.

```python
PolicyParticipant(
	name: str,
	policy,
	*,
	seat: int,
	sheet,
	space,
	deadline: int,
	discount: float = 1.0,
	opponents: tuple = (),
	n_seats: int | None = None,
	tables=None,
	state_provider=None,
	registry_prefix: str = 'O',
	system_prompt: str | None = None,
	private_context: tuple = (),
	min_accept: int | None = None,
	veto_seats: tuple = (),
)
```

Defined in [`interlens.arena.negotiation.policy_participant`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/policy_participant.py#L47-L223)

**Inherits from:** [Participant](../../../participant/participant/Participant.md)

Parameters
----------
name : str
    Identifier within the conversation.
policy : callable
    `policy(state: NegotiationState) -> Action` — e.g. any policy from
    `interlens.arena.negotiation.strategies` or an oracle wrapped as a policy.
seat : int
    This seat's index into the game's seat-indexed sheets/tables.
sheet : object
    This seat's private score sheet (exposes `.utility`/`.surplus`/`.threshold`).
space : DealSpace
    The shared deal space. Also the seat's issue/option NAME table: proposals are emitted with names
    (`space.named`) and incoming name-based deals decoded (`space.parse`), so the transcript is
    LLM-legible and there is no second copy of the issue names to keep in sync.
deadline : int
    Total number of rounds `T` (for the policy's time-dependent concession).
discount : float
    Per-round discount `delta` carried into the state.
opponents : tuple[int, ...]
    Opponent seat indices (default: inferred as all seats != `seat` up to `n_seats`).
n_seats : int | None
    Total seat count (used to default `opponents` when not given).
tables : object | None
    Optional full-information `GameTables` to attach to the state (enables exact full-info policies).
min_accept : int | None
    Fixed acceptance quorum out of the original seats; `None` means unanimity.
veto_seats : tuple[int, ...]
    Seats whose support is mandatory.
state_provider : callable | None
    Optional `callable(view) -> NegotiationState` overriding the default view reconstruction.
registry_prefix : str
    Offer-id prefix for the reconstructed registry (default `"O"`, matching `OfferRegistry`).
system_prompt : str | None
    Optional system framing (recorded for view/transcript symmetry; unused by the policy).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `policy` |  | *required* |  |
| `seat` | `int` | *required* |  |
| `sheet` |  | *required* |  |
| `space` |  | *required* |  |
| `deadline` | `int` | *required* |  |
| `discount` | `float` | `1.0` |  |
| `opponents` | `tuple` | `()` |  |
| `n_seats` | `int \| None` | `None` |  |
| `tables` |  | `None` |  |
| `state_provider` |  | `None` |  |
| `registry_prefix` | `str` | `'O'` |  |
| `system_prompt` | `str \| None` | `None` |  |
| `private_context` | `tuple` | `()` |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` | `tuple` | `()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `deadline` |  |  |
| `discount` |  |  |
| `min_accept` |  |  |
| `name` |  |  |
| `opponents` |  |  |
| `others_role` |  |  |
| `policy` |  |  |
| `private_context` |  |  |
| `registry_prefix` |  |  |
| `seat` |  |  |
| `self_role` |  |  |
| `sheet` |  |  |
| `space` |  |  |
| `state_provider` |  |  |
| `system_prompt` |  |  |
| `tables` |  |  |
| `veto_seats` |  |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/policy_participant.py#L147-L152)

Compute this seat's action from a `NegotiationState` directly — no view parsing, no engine.

The
pure entry a counterfactual-rollout loop calls (equivalent to `self.policy(state)`). Note the bound
`self.policy` is itself a public callable `policy(NegotiationState) -> Action`, so a rollout can
skip the participant wrapper entirely and call the policy on a reconstructed state.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../strategies/NegotiationState.md) | *required* |  |

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

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/policy_participant.py#L117-L132)

Reconstruct the negotiation state from `view`, ask the bound policy for an action, and return it as a fenced-JSON message (the same envelope LLM seats emit).

Raises on any interp request — a
pure-Python seat has no model to steer/capture/patch or read logprobs from.

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

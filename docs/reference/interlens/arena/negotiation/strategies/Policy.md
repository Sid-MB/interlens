# `Policy`

A deterministic (or seeded) negotiation policy: `policy(state) -> action`.

```python
Policy()
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L306-L405)

**Inherits from:** `ABC`

Subclasses set `name`
and implement `act`. `__call__` is the invocation surface a `PolicyParticipant` binds to.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `name` | `str` |  |

## Methods {#methods}

## `act` {#act}

```python
act(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L320-L322)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `declaration` {#declaration}

```python
declaration(self, state: NegotiationState) -> str | None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L324-L336)

Public cheap talk this policy says ONCE, on its first turn of the episode — or `None` (the default) for a silent policy.

This is the commitment channel. A policy's moves already reveal what it will do eventually; a
declaration states it in plain language up front, before the other parties have made a move, which is
what makes it a *commitment* rather than a pattern the opponents have to infer. `PolicyParticipant`
decides when "first turn" is by reading the view (no prior turn of this seat's own) and attaches the
string under the envelope's `message` key, so it is published exactly like an LLM seat's chat.

Render deals and scores in the same human terms the transcript uses — `state.space.named(deal)` for
packages, raw sheet points for thresholds — since the audience is the LLM seats reading the log.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

## `vote` {#vote}

```python
vote(self, state: NegotiationState)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L338-L347)

The terminal individually-rational vote on the standing offer when the scenario allows only accept/reject/walk (`state.must_vote`).

Accept any offer that clears this seat's threshold (surplus
>= 0), since the sole alternative is no-deal = 0; otherwise reject it (or walk if there is no standing
offer). Shared by every policy — proposing in a vote-only phase is an economic-legality violation, so
no policy must ever fall through to a Propose here.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](NegotiationState.md) | *required* |  |

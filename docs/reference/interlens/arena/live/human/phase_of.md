# `phase_of`

The scenario phase this state describes: :data:`FINAL_VOTE` on the forced-final ballot, :data:`FINAL_PROPOSAL` on the turn that tables it, else an ordinary :data:`TURN`.

```python
phase_of(state: NegotiationState) -> str
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L163-L170)

Read off the same two
fields the policies read (`must_vote` and `round > deadline`) so a human seat and a policy seat agree
about what turn they are playing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../../negotiation/strategies/NegotiationState.md) | *required* |  |

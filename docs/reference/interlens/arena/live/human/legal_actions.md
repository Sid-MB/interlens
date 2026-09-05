# `legal_actions`

What this seat may legally submit right now, as `{can_accept, can_reject, can_offer, can_walk, can_pass}` — the form's rules and the server's validation, computed once from one state.

```python
legal_actions(state: NegotiationState) -> dict
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L135-L160)

It mirrors `ScorableNegotiation._PHASE_ALLOWED` exactly, because the scenario is the authority and a form
that offers a disallowed move burns a real turn on a legality error:

- an ordinary **turn** allows everything: propose, accept/reject any live offer, walk, or stand pat;
- the forced-final **proposal** turn allows propose / accept / walk but NOT reject (the scenario reads a
  reject here as an economic-legality violation), and not a pass either — this turn tables the last binding
  package or there is nothing to vote on;
- the forced-final **vote** allows accept / reject of THE offer under vote only (`state.standing`, which
  the scenario pins to its `final_offer`) or a walk.

`can_accept`/`can_reject` are lists of offer ids in registration order, so the dock renders the ballot in
the order the offers were tabled.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | [NegotiationState](../../negotiation/strategies/NegotiationState.md) | *required* |  |

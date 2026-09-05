# `replay_integrity`

Re-derive every computable turn of `episode` from its own recorded state block and check it matches what the seat actually played.

```python
replay_integrity(episode: dict, bank_dir) -> dict
```

Defined in [`interlens.arena.scenarios.auction_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/auction_policy.py#L296-L372)

**The mechanism-independent form of "the played seat is its rule."** For each turn the participant
recorded, this rebuilds the :class:`~interlens.arena.auction.bidders.AuctionState` from the very
`auction_state` block that turn was rendered with, re-runs the policy over it, and asserts the freshly
computed move equals the recorded `parsed_action`. It needs no equilibrium concept and no benchmark, so
it applies to **every** mechanism family — including the clock families, where asserting equality against
an equilibrium bid is meaningless because the policy is a stage-myopic best responder while the benchmark
is a symmetric equilibrium (design.md §6).

This is the check that generalizes the SAA on-path gate, and it is exactly the class that catches a policy
silently forfeiting a lot it merely did not demand, a state block fed with the wrong round, a renderer
dropping a field, or an oracle seat handed information it should not have — all for $0, from episodes
already on disk, before a paid arm runs.

Determinism note: the recorded block is the seat's own input, so seeded tie-breaks and the realized
standing table are reproduced rather than re-drawn, and the comparison is exact rather than
tolerance-based. Only turns whose seat is computable in this arm are checked; an LLM seat has no rule to
replay, which is the entire point of the contrast.

Parameters
----------
episode : dict
    A stored episode record, carrying `instance_id`, `cell_cfg`, `seats` and `turns` with each
    turn's `view` and `parsed_action`.
bank_dir : str | Path
    The frozen bank directory the episode's instance was drawn from.

Returns
-------
dict
    `{"arm", "turns", "checked", "mismatches", "pass"}`. `checked` is 0 and `pass` True for an
    all-LLM episode, which has no computable seat to replay.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `bank_dir` |  | *required* |  |

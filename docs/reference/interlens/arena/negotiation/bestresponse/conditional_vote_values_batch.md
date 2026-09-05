# `conditional_vote_values_batch`

:func:`conditional_vote_values` for `K` offers at once; returns four `(K,)` arrays.

```python
conditional_vote_values_batch(
	accept_prob: np.ndarray,
	proposers,
	agent: int,
	deal_indices,
	deal_surpluses,
	continuation: float,
	*,
	min_accept: int | None = None,
	veto_seats=(),
	forced_yes=None,
	forced_no=None,
) -> tuple
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L150-L203)

Same semantics per offer — each gets its own proposer, deal, already-cast `forced_yes` / `forced_no`
votes, and surplus — but the Poisson-binomial solves are BATCHED. The DP in
:func:`passage_probability` is elementwise across its deal axis, so stacking K independent single-offer
rows into one call returns each row's own answer, bitwise identical to solving it alone. Offers are
grouped by proposer (the one argument the DP takes per call rather than per row), so a turn costs at most
two solves per distinct proposer instead of two per offer — the difference between O(live offers) and
O(seats) numpy calls on a turn, and the reason a long-horizon episode, whose live-offer list grows every
round, stops being quadratic.

Parameters
----------
accept_prob : np.ndarray
    `(D, n)` acceptance probabilities (full-information 0/1 or posterior).
proposers : sequence[int | None]
    Per-offer proposing seat, or `None` for a facilitator-tabled offer with no implicit supporter.
agent : int
    The seat whose yes/no vote is being valued (the same seat for every offer).
deal_indices, deal_surpluses : sequence
    Per-offer row into `accept_prob` and the payoff agreement pays `agent`.
continuation : float
    What failing to pass is worth to `agent` — shared by every offer, since it is a property of the turn.
forced_yes, forced_no : sequence[sequence[int]] | None
    Per-offer already-cast votes; `None` means none for any offer.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept_prob` | `np.ndarray` | *required* |  |
| `proposers` |  | *required* |  |
| `agent` | `int` | *required* |  |
| `deal_indices` |  | *required* |  |
| `deal_surpluses` |  | *required* |  |
| `continuation` | `float` | *required* |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |
| `forced_yes` |  | `None` |  |
| `forced_no` |  | `None` |  |

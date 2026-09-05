# `conditional_vote_values`

Value this seat's yes/no vote after conditioning on votes already cast.

```python
conditional_vote_values(
	accept_prob: np.ndarray,
	proposer: int | None,
	agent: int,
	deal_index: int,
	deal_surplus: float,
	continuation: float,
	*,
	min_accept: int | None = None,
	veto_seats=(),
	forced_yes=(),
	forced_no=(),
) -> tuple[float, float, float, float]
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L127-L147)

Returns `(yes_value, no_value, p_pass_if_yes, p_pass_if_no)`. This is load-bearing for quorum games:
a yes vote may be insufficient to pass, while a no vote may be non-pivotal. Existing supporters/rejecters
and walkers are forced through `forced_yes`/`forced_no`; all uncast votes retain their deterministic
full-information or posterior probability. Agreement pays `deal_surplus` and failure pays
`continuation`.

`proposer=None` values a vote on a facilitator-tabled offer, which no seat implicitly supports (see
:func:`passage_probability`).

One offer is the `K = 1` case of :func:`conditional_vote_values_batch`, which is where the arithmetic
actually lives — a turn with many live offers should call that instead of this in a loop.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept_prob` | `np.ndarray` | *required* |  |
| `proposer` | `int \| None` | *required* |  |
| `agent` | `int` | *required* |  |
| `deal_index` | `int` | *required* |  |
| `deal_surplus` | `float` | *required* |  |
| `continuation` | `float` | *required* |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |
| `forced_yes` |  | `()` |  |
| `forced_no` |  | `()` |  |

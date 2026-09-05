# `passage_probability`

Probability each deal passes under independent responder votes.

```python
passage_probability(
	accept_prob: np.ndarray,
	proposer: int | None,
	*,
	min_accept: int | None = None,
	veto_seats=(),
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.bestresponse`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/bestresponse.py#L67-L114)

`accept_prob` has shape `(D, n)`.  The proposer implicitly supports its own offer, `min_accept` is
a fixed count out of the original `n` seats, and every veto seat must support.  `None` preserves the
historical unanimity rule.  A small Poisson-binomial DP computes `P(# yes >= quorum)` exactly, rather
than multiplying every opponent probability (which silently turns every quorum into unanimity).

`proposer=None` means the offer has NO implicit supporter — a package tabled by the protocol's neutral
facilitator (:data:`~interlens.arena.actions.FACILITATOR`), which holds no sheet and casts no vote. Every
seat then votes on its own merits: the quorum must be met out of the responders alone, and each veto seat's
probability enters the product rather than being satisfied for free by proposing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `accept_prob` | `np.ndarray` | *required* |  |
| `proposer` | `int \| None` | *required* |  |
| `min_accept` | `int \| None` | `None` |  |
| `veto_seats` |  | `()` |  |

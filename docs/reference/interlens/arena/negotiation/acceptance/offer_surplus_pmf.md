# `offer_surplus_pmf`

The distribution `F` of the surplus `agent` expects to *receive*, induced by the belief posterior.

```python
offer_surplus_pmf(
	tables: GameTables,
	agent: int,
	accept_prob_fn=None,
	*,
	only_closable: bool = True,
	only_ir: bool = True,
	objective=None,
	accept_weights=None,
)
```

Defined in [`interlens.arena.negotiation.acceptance`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/acceptance.py#L100-L158)

Each deal `d` is weighted by `P(all opponents accept d)` (so only deals that can actually close carry
mass) and contributes its own surplus `tables.surplus[d, agent]` to the support.

Parameters
----------
tables : GameTables
    Precomputed surplus tables.
agent : int
    Whose received-surplus distribution to build.
accept_prob_fn : callable | None
    `accept_prob_fn(deal) -> P(all opponents accept deal)`. Typically
    `lambda d: prod_j belief_states[j].accept_prob(d)`. If None, all closable = uniform (full-info
    proxy: every IR deal equally offerable). Ignored when `accept_weights` is given.
accept_weights : np.ndarray | None
    The SAME per-deal acceptance probabilities as a ready `(|D|,)` vector in `tables.deals` order —
    the vectorized form of `accept_prob_fn`, and the one to prefer. `passage_probability` already
    solves every deal at once (its Poisson-binomial DP is elementwise across the deal axis, so a row of
    the batched result is bitwise identical to solving that row alone), whereas calling `accept_prob_fn`
    here runs one numpy-heavy call per deal — |D| times per turn, per seat, which measured as the single
    largest cost in a long-horizon private-information episode.
only_closable : bool
    Drop deals with zero acceptance probability.
only_ir : bool
    Drop deals with negative surplus for `agent` (below own threshold — never worth receiving).
objective : np.ndarray | None
    Optional `(|D|,)` payoff column to use **instead of** `agent`'s own surplus — the objective
    substitution that makes this recursion serve a fairness-seeking agent (`fairness.mnw_objective`)
    as well as a self-interested one. `None` (default) reads `tables.surplus[:, agent]`, which is the
    exact prior behaviour. Whatever is passed must share own-surplus's convention that **no-deal scores
    zero**, since that is the recursion's `v_0` base case; the `only_ir` filter then reads
    "non-negative on this column" in the substituted units.

Returns `(values, probs)` — a normalized pmf. Empty support falls back to a point mass at surplus 0
(i.e. "no acceptable offer expected", so the reservation collapses to the no-deal value).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `agent` | `int` | *required* |  |
| `accept_prob_fn` |  | `None` |  |
| `only_closable` | `bool` | `True` |  |
| `only_ir` | `bool` | `True` |  |
| `objective` |  | `None` |  |
| `accept_weights` |  | `None` |  |

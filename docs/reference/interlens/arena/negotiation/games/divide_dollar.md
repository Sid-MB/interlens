# `divide_dollar`

The **divide-the-dollar / legislative-bargaining** testbed [baron_ferejohn1989]: `n_parties` split a unit pie over multiple rounds with a rotating proposer, under a unanimity or majority agreement rule.

```python
divide_dollar(
	*,
	n_parties: int = 3,
	steps: int = 12,
	rounds: int | None = None,
	rule: str = 'unanimity',
	discount: float = 0.99,
	seed: int = 0,
) -> tuple[GameSpec, dict, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L128-L183)

Encoding: J=1 issue ("Allocation") whose options are every integer allocation of `steps` units among the
parties (the compositions summing to `steps`); party `i`'s utility for an allocation is its own share
`units_i / steps in [0, 1]`, thresholds `tau=0`. The deal space is reused from the equilibrium oracle's
Okada anchor (:func:`~interlens.arena.negotiation.equilibrium.divide_the_dollar`), so the same game the
oracle solves is the one the scenario plays. Rotating proposer + multi-round is the scenario's default
protocol (`protocol_cfg = {}`).

Rational anchor: the Banks-Duggan / Baron-Ferejohn stationary equilibrium. For the **unanimity** rule the
Okada 1996 closed form [okada1996] gives the sanity value `v_i = 1/n` (proposer keeps `1 - delta(n-1)/n`,
each responder `delta/n`) -- exactly what
:class:`~interlens.arena.negotiation.equilibrium.EquilibriumOracle` recovers on this preset. The **majority**
rule (`min_accept = floor(n/2)+1`) is the minimal-winning-coalition Baron-Ferejohn game; the equilibrium
oracle models unanimity social acceptance, so the `v = 1/n` anchor is stated only for `rule="unanimity"`.

Like `ultimatum` this is a pure division: every allocation is Pareto-optimal
(`dominated_acceptable_fraction = 0`), so the score-sheet-repair knob does not apply.

Parameters
----------
n_parties : number of parties splitting the pie (N in {2, 3} is the usual testbed; larger works but the deal
    space is `C(steps+n-1, n-1)` compositions -- keep it enumerable).
steps : allocation granularity (the pie is `steps` indivisible units). Finer `steps` = the equilibrium
    value tracks `1/n` more precisely but a larger deal space.
rounds : round-robin rounds before the forced final (default `2 * n_parties`, so each seat proposes ~twice).
rule : `"unanimity"` (all parties must clear their threshold -- the Okada `v=1/n` anchor) or `"majority"`
    (`floor(n/2)+1` parties -- the minimal-winning-coalition game).
discount : per-round discount `delta` in `(0, 1]` stored on the game (the equilibrium/acceptance oracles'
    single source of truth); `< 1` makes interior concession rational rather than deadline brinkmanship.
seed : accepted for a uniform preset interface; the game is deterministic, so it is unused.

Returns `(GameSpec, analysis, protocol_cfg)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_parties` | `int` | `3` |  |
| `steps` | `int` | `12` |  |
| `rounds` | `int \| None` | `None` |  |
| `rule` | `str` | `'unanimity'` |  |
| `discount` | `float` | `0.99` |  |
| `seed` | `int` | `0` |  |

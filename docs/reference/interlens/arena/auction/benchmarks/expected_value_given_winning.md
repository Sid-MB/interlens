# `expected_value_given_winning`

`E[v_i | own signal, i has the highest signal]` for the INTERDEP structure — the winner's-curse correction [kagel_levin1986, pp. 908-915].

```python
expected_value_given_winning(
	signal: int,
	*,
	private_part: float,
	gamma: float,
	sigma_nu: float,
	n_rivals: int,
	resale_grid,
) -> float
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L139-L160)

The unobserved common resale value `R` has the public prior `resale_grid` (the generator draws it
uniformly on the catalogue base range). The seat's signal is `s = round(R * exp(nu))` with
`nu ~ N(0, sigma_nu^2)` public, so the likelihood of the signal is lognormal around `R`, and
conditioning on WINNING multiplies in the probability that all `n_rivals` rival signals fall below
`s` given `R`. The returned value is `private_part + gamma * E[R | ...]`, which is strictly below
the naive `private_part + gamma * signal` whenever `sigma_nu > 0` and there is at least one rival —
the shading that separates a sophisticated bidder from a cursed one.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `signal` | `int` | *required* |  |
| `private_part` | `float` | *required* |  |
| `gamma` | `float` | *required* |  |
| `sigma_nu` | `float` | *required* |  |
| `n_rivals` | `int` | *required* |  |
| `resale_grid` |  | *required* |  |

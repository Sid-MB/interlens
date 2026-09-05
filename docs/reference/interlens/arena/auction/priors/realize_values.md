# `realize_values`

The value equation of design.md §2.2, evaluated for every `(bidder, slot)` pair of one stage.

```python
realize_values(
	*,
	base_values: np.ndarray,
	loadings: np.ndarray,
	attrs: np.ndarray,
	beta: float,
	z: np.ndarray,
	eps: np.ndarray,
	gammas: np.ndarray,
	resale: np.ndarray | None = None,
) -> np.ndarray
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L214-L258)

`ell_ij = log(B_j) + (beta / K) * (a_i . w_j) + z_i + eps_ij` and
`v_ij = round(exp(ell_ij)) + round(gamma_i * R_j)`, with the result clipped at 1 so a deep negative draw
cannot produce a zero- or negative-valued lot (which would make `bid / value` undefined).

Parameters
----------
base_values : np.ndarray
    `(n_items,)` public whole-number catalogue base values `B_jt`.
loadings : np.ndarray
    `(n_items, K)` public loadings `w_j`.
attrs : np.ndarray
    `(n_bidders, K)` public attribute vectors `a_i`.
beta : float
    Public strength of the persona term; `0` under IPV, which is what makes public facts uninformative
    about values there.
z : np.ndarray
    `(n_bidders,)` realized private bidder-level shifters (already scaled by `sigma_z`).
eps : np.ndarray
    `(n_bidders, n_items)` realized private idiosyncrasies (already scaled by `sigma_eps`).
gammas : np.ndarray
    `(n_bidders,)` public resale weights; all zero outside INTERDEP.
resale : np.ndarray | None
    `(n_items,)` common resale values `R_jt`, known to nobody. `None` outside INTERDEP.

Returns
-------
np.ndarray
    `(n_bidders, n_items)` whole-number valuations, dtype `int64`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `base_values` | `np.ndarray` | *required* |  |
| `loadings` | `np.ndarray` | *required* |  |
| `attrs` | `np.ndarray` | *required* |  |
| `beta` | `float` | *required* |  |
| `z` | `np.ndarray` | *required* |  |
| `eps` | `np.ndarray` | *required* |  |
| `gammas` | `np.ndarray` | *required* |  |
| `resale` | `np.ndarray \| None` | `None` |  |

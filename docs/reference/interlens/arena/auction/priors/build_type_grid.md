# `build_type_grid`

The auction analogue of `negotiation/beliefs.py::build_type_grid`: one rival's type is the pair `(z, eps)` of continuous Gaussian draws, so the grid is a Gauss-Hermite product rule rather than an enumeration of discrete hypotheses.

```python
build_type_grid(
	sigma_z: float,
	sigma_eps: float,
	n_z: int = 9,
	n_eps: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L375-L393)

Returns `(z_nodes, z_weights, eps_nodes, eps_weights)`, each 1-D, with weights summing to 1. A
degenerate `sigma = 0` (the IPV switch zeroing `sigma_z`) collapses to the single node `0.0` with
weight 1, so an IPV posterior is exact rather than approximated. `n_z`/`n_eps` of 9 integrate the
smooth exp-transformed integrand to well under a whole-number rounding step over the design's value
range, which is the accuracy that matters when bids are integers.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sigma_z` | `float` | *required* |  |
| `sigma_eps` | `float` | *required* |  |
| `n_z` | `int` | `9` |  |
| `n_eps` | `int` | `9` |  |

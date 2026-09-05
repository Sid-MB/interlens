# `RoutingStats`

Aggregate expert-usage distributions over a set of token positions.

```python
RoutingStats(
	expert_load: torch.Tensor,
	expert_mass: torch.Tensor | None,
	layers: tuple[int, ...],
	n_tokens: int,
	top_k: int,
)
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L125-L139)

`expert_load[l, e]` is the fraction of top-k selections at layer `l` that went to expert `e`
(rows sum to 1 — the discrete "which experts fired" histogram). `expert_mass[l, e]` is the mean softmax
router probability (`None` if the captures were `top_k_only` — full logits are needed for mass).
`layers` are the decoder-layer indices of the rows; `n_tokens` is how many positions were pooled.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `expert_load` | `torch.Tensor` | *required* |  |
| `expert_mass` | `torch.Tensor \| None` | *required* |  |
| `layers` | `tuple[int, ...]` | *required* |  |
| `n_tokens` | `int` | *required* |  |
| `top_k` | `int` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `expert_load` | `torch.Tensor` |  |
| `expert_mass` | `torch.Tensor \| None` |  |
| `layers` | `tuple[int, ...]` |  |
| `n_tokens` | `int` |  |
| `top_k` | `int` |  |

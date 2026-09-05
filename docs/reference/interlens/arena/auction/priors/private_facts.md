# `private_facts`

The private fact VALUES for one seat at one stage — re-rendered every stage because `z` redraws while the public card is fixed (design.md §2.2).

```python
private_facts(
	*,
	z: float,
	sigma_z: float,
	budget: int,
	values: np.ndarray,
	synergy_target: tuple[int, ...] | None,
	signals: np.ndarray | None = None,
	n_items: int,
) -> dict
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L348-L369)

Keys: `capital_position` (the tercile LABEL of the realized `z`, against public boundaries),
`budget` (the realized whole-number budget), `top_slot` (the seat's own argmax slot name and value),
`synergy_target` (the private target SET as slot names, or `None`), and `resale_signal` (the noisy
per-slot resale signals, INTERDEP only).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `z` | `float` | *required* |  |
| `sigma_z` | `float` | *required* |  |
| `budget` | `int` | *required* |  |
| `values` | `np.ndarray` | *required* |  |
| `synergy_target` | `tuple[int, ...] \| None` | *required* |  |
| `signals` | `np.ndarray \| None` | `None` |  |
| `n_items` | `int` | *required* |  |

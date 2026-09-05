# `public_facts`

The public fact VALUES for one seat card: the persona's own keys, every attribute entry as its own fact (each entry of `a_i` is one public fact, per design.md §2.2), and the public mechanism-relevant parameters.

```python
public_facts(
	persona: Persona,
	attrs: tuple[int, ...],
	*,
	capacity: int,
	gamma: float,
	synergy_rate: float,
	decay: float,
	budget_mult: float,
) -> dict
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L336-L345)

Returned as data; :func:`render_facts` turns it into prose.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `persona` | [Persona](Persona.md) | *required* |  |
| `attrs` | `tuple[int, ...]` | *required* |  |
| `capacity` | `int` | *required* |  |
| `gamma` | `float` | *required* |  |
| `synergy_rate` | `float` | *required* |  |
| `decay` | `float` | *required* |  |
| `budget_mult` | `float` | *required* |  |

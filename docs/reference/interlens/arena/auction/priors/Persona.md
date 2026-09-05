# `Persona`

One of the five archetypes of design.md §2.2, fixed across the bank and across all stages.

```python
Persona(
	persona_id: str,
	display_name: str,
	attrs: tuple[int, ...],
	capacity: int,
	gamma: float,
	synergy_rate: float,
	decay: float,
	budget_mult: float,
	role: str,
	public_fact_keys: tuple[str, ...],
	private_fact_keys: tuple[str, ...],
)
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L95-L115)

Every field is PUBLIC and appears on the seat card. `attrs` is the attribute signature over
:data:`ATTR_NAMES` with entries in {-1, 0, +1} — each entry is one public fact. `budget_mult` is the
multiple of the seat's own top-capacity valuation total at which its per-stage budget is set: the multiple
is public (rendered as a tercile label), the realized whole-number budget is private. `role` records
what the persona is FOR in the design, so the table documents its own experimental purpose.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `persona_id` | `str` | *required* |  |
| `display_name` | `str` | *required* |  |
| `attrs` | `tuple[int, ...]` | *required* |  |
| `capacity` | `int` | *required* |  |
| `gamma` | `float` | *required* |  |
| `synergy_rate` | `float` | *required* |  |
| `decay` | `float` | *required* |  |
| `budget_mult` | `float` | *required* |  |
| `role` | `str` | *required* |  |
| `public_fact_keys` | `tuple[str, ...]` | *required* |  |
| `private_fact_keys` | `tuple[str, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `attrs` | `tuple[int, ...]` |  |
| `budget_mult` | `float` |  |
| `capacity` | `int` |  |
| `decay` | `float` |  |
| `display_name` | `str` |  |
| `gamma` | `float` |  |
| `persona_id` | `str` |  |
| `private_fact_keys` | `tuple[str, ...]` |  |
| `public_fact_keys` | `tuple[str, ...]` |  |
| `role` | `str` |  |
| `synergy_rate` | `float` |  |

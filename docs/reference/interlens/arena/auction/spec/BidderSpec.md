# `BidderSpec`

One seat's persistent structure.

```python
BidderSpec(
	seat: int,
	persona_id: str,
	display_name: str,
	attrs: tuple[int, ...],
	capacity: int,
	gamma: float,
	synergy_rate: float,
	decay: float,
	budget_mult: float,
	public_fact_keys: tuple[str, ...] = (),
	private_fact_keys: tuple[str, ...] = (),
)
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L291-L334)

Everything here persists across all `T` stages (design.md §2.4).

Every field except `private_fact_keys` is PUBLIC and rendered on every seat's card: the attribute vector
`attrs` (entries in {-1, 0, +1}, one public fact each), `capacity` (max lots per stage), `gamma`
(resale weight), `synergy_rate` (the complementarity rate `c_i` — its EXISTENCE and RATE are public
while the target set is private, which is what makes exposure real), `decay` (the diminishing-returns
factor `d_i`), and `budget_mult` (the multiple of its own top-capacity valuation total that the seat's
per-stage budget is set to — public as a tercile label on the card, while the realized whole-number budget
is private).

`public_fact_keys` / `private_fact_keys` are template KEYS, not prose: rendering data lives in
`priors.py` and the prose in docs/templates/, so a prompt-wording change never edits a stored spec.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |
| `persona_id` | `str` | *required* |  |
| `display_name` | `str` | *required* |  |
| `attrs` | `tuple[int, ...]` | *required* |  |
| `capacity` | `int` | *required* |  |
| `gamma` | `float` | *required* |  |
| `synergy_rate` | `float` | *required* |  |
| `decay` | `float` | *required* |  |
| `budget_mult` | `float` | *required* |  |
| `public_fact_keys` | `tuple[str, ...]` | `()` |  |
| `private_fact_keys` | `tuple[str, ...]` | `()` |  |

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
| `seat` | `int` |  |
| `synergy_rate` | `float` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'BidderSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L326-L334)

Rebuild a :class:`BidderSpec` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L318-L324)

JSON-ready dict.

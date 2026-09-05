# `OfferCurve`

One opponent model's fitted distribution of the `z` an offer delivers to its RECIPIENT, as a function of round position.

```python
OfferCurve(
	frac_edges: tuple,
	z_quantiles: tuple,
	n_offers: tuple = (),
	low_power: bool = False,
	notes: str = '',
)
```

Defined in [`interlens.arena.negotiation.llm_calibrated`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L80-L138)

This is the concession curve seen from the receiving side, which is the side the stopping rule needs: it
answers "if I wait, what is the next package worth to me", in my own affine-invariant units, without
knowing the proposer's sheet at all — the recipient's `z` is computed from the recipient's own sheet, so
the fit needs no revelation and the runtime evaluation needs no belief.

Parameters
----------
frac_edges : list[float]
    `K-1` strictly ascending interior edges partitioning round fraction `t = (round-1)/deadline` in
    `[0, 1]` into `K` bins (`searchsorted` right, exactly like the acceptance bins). Scale-free so a
    curve fitted on 4-round games evaluates on any deadline.
z_quantiles : list[list[float]]
    `K` rows of equiprobable `z` support points (fitted quantiles of the observed recipient-`z`
    distribution in that round bin). Row lengths may differ; each row is one discrete pmf with uniform
    masses.
n_offers : list[int]
    Observation count behind each row, carried so a consumer can see a bin fitted on 12 offers.
low_power : bool
    The fitting lane's own not-quotable flag, carried through like the acceptance curves'.
notes : str
    Free text from the fitting lane (runs, exclusions, caveats).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `frac_edges` | `tuple` | *required* |  |
| `z_quantiles` | `tuple` | *required* |  |
| `n_offers` | `tuple` | `()` |  |
| `low_power` | `bool` | `False` |  |
| `notes` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `frac_edges` | `tuple` |  |
| `low_power` | `bool` |  |
| `n_offers` | `tuple` |  |
| `notes` | `str` |  |
| `z_quantiles` | `tuple` |  |

## Methods {#methods}

## `from_dict` {#from_dict}

```python
from_dict(cls, d: dict) -> 'OfferCurve'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L132-L138)

Build from one model's JSON block, ignoring keys the schema does not define.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `pmf` {#pmf}

```python
pmf(self, frac: float) -> tuple
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/llm_calibrated.py#L124-L130)

The discrete pmf `(z_values, probs)` of an incoming offer's recipient-`z` at round fraction `frac` (clipped to `[0, 1]`): the fitted quantiles of that round bin with uniform masses.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `frac` | `float` | *required* |  |

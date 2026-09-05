# `SteeringSpec`

A residual-stream intervention applied during generation via forward hooks on decoder layers.

```python
SteeringSpec(
	direction: torch.Tensor,
	layers: tuple[int, ...],
	coef: float = 1.0,
	mode: Mode = 'add',
)
```

Defined in [`interlens.interp.steering`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/steering.py#L31-L95)

`mode='add'` adds `coef * direction` to the residual at `layers`; `mode='ablate'` projects the
`direction` component *out* of the residual (directional ablation). The same mechanism covers both because
ablation is just the projection-removal variant of an additive hook.

A summary (mode, layers, coef, direction norm) is recorded into `Message.metadata['steering']` by the
participant so a steered/ablated turn is reproducible.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `direction` | `torch.Tensor` | *required* |  |
| `layers` | `tuple[int, ...]` | *required* |  |
| `coef` | `float` | `1.0` |  |
| `mode` | `Mode` | `'add'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `coef` | `float` |  |
| `direction` | `torch.Tensor` |  |
| `layers` | `tuple[int, ...]` |  |
| `mode` | `Mode` |  |

## Methods {#methods}

## `difference_of_means` {#difference_of_means}

```python
difference_of_means(
	cls,
	pos_acts,
	neg_acts,
	layers,
	coef: float = 1.0,
	mode: Mode = 'add',
) -> 'SteeringSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/steering.py#L48-L64)

Build a spec whose `direction` is the **unit difference-of-means** of two activation populations, `normalize(mean(pos) − mean(neg))` — the classic contrastive/concept-direction recipe, pointing TOWARD the positive class.

`pos_acts`/`neg_acts` are `[n, d_model]` (a stack of per-example residuals) or a
pre-pooled `[d_model]` vector; anything `torch.as_tensor` accepts works. Steer toward the positive
concept with `coef>0` and **away** from it (suppress) with `coef<0`. `layers` is an int or an
iterable of decoder-layer indices. This lives here (not re-hand-rolled per experiment) per the
contribution convention.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pos_acts` |  | *required* |  |
| `neg_acts` |  | *required* |  |
| `layers` |  | *required* |  |
| `coef` | `float` | `1.0` |  |
| `mode` | `Mode` | `'add'` |  |

## `register` {#register}

```python
register(self, model: 'PreTrainedModel') -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/steering.py#L66-L72)

Register the steering hooks on `model` and return the handles (caller removes them after generate).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |

## `summary` {#summary}

```python
summary(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/steering.py#L93-L95)

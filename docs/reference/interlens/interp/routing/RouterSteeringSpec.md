# `RouterSteeringSpec`

A causal intervention on MoE routing: add a per-expert bias to the gate logits during generation, nudging which experts fire.

```python
RouterSteeringSpec(bias: torch.Tensor, layers: tuple[int, ...], coef: float = 1.0)
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L203-L251)

The routing analogue of :class:`SteeringSpec` (which steers the residual stream) — here
forward hooks sit on each sparse layer's `mlp.gate` (the router `nn.Linear` whose output is the
`[tokens, n_experts]` logits) and add `coef * bias` before top-k selection.

Build it with :meth:`toward_load` to push routing *toward* a target expert-usage distribution (e.g. the MoE's
solo-on-domain `RoutingStats.expert_load`): the bias is `log(target + eps)`, so adding it acts like a
log-prior that shifts the router's softmax toward the target experts, with `coef` the strength (0 = no-op).

A summary (layers, coef, per-layer bias norm) is available via :meth:`summary` for reproducibility.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bias` | `torch.Tensor` | *required* |  |
| `layers` | `tuple[int, ...]` | *required* |  |
| `coef` | `float` | `1.0` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `bias` | `torch.Tensor` |  |
| `coef` | `float` |  |
| `layers` | `tuple[int, ...]` |  |

## Methods {#methods}

## `register` {#register}

```python
register(self, model: 'PreTrainedModel') -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L228-L237)

Register the gate-bias hooks on `model`'s sparse layers; returns handles (caller removes after use).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |

## `summary` {#summary}

```python
summary(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L249-L251)

## `toward_load` {#toward_load}

```python
toward_load(
	cls,
	target_load: torch.Tensor,
	layers: tuple[int, ...],
	coef: float = 1.0,
	eps: float = 1e-06,
) -> 'RouterSteeringSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L221-L226)

Steer toward a target expert-usage distribution `target_load` (`[len(layers), n_experts]`, rows the fraction of routing mass per expert).

Bias `= log(target_load + eps)` (a log-prior on expert choice).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `target_load` | `torch.Tensor` | *required* |  |
| `layers` | `tuple[int, ...]` | *required* |  |
| `coef` | `float` | `1.0` |  |
| `eps` | `float` | `1e-06` |  |

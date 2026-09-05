# `Patch`

Activation patching: overwrite a decoder layer's residual at specific token `positions` with saved `activations` (captured from another run/branch).

```python
Patch(activations: torch.Tensor, layer: int, positions: tuple[int, ...])
```

Defined in [`interlens.interp.patching`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/patching.py#L29-L65)

This is the cross-branch causal-tracing primitive: capture activations at turn N in one branch (via
`ActivationCache`), then inject them at the aligned positions of another branch's forward. The harness owns
this because only it knows the turn/position correspondence between branches.

P2 applies the patch on the (single) prompt forward — positions index into the prompt sequence. Aligning
positions across branches is the caller's responsibility; `Patch` just performs the overwrite.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `activations` | `torch.Tensor` | *required* |  |
| `layer` | `int` | *required* |  |
| `positions` | `tuple[int, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `activations` | `torch.Tensor` |  |
| `layer` | `int` |  |
| `positions` | `tuple[int, ...]` |  |

## Methods {#methods}

## `register` {#register}

```python
register(self, model: 'PreTrainedModel') -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/patching.py#L46-L48)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |

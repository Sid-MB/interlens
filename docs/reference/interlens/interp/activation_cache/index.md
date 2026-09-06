# `activation_cache`

Module `interlens.interp.activation_cache`

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `OffloadLocation` |  |  |
| `Phase` |  |  |
| `Site` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`ActivationCache`](ActivationCache.md) | A queryable store of captured activations, tagged by conversation structure. |
| [`ActivationRecord`](ActivationRecord.md) | One captured tensor plus everything needed to know *what it is*. |
| [`CaptureSpec`](CaptureSpec.md) | What to capture during a generation: which `sites` at which `layers`, and where to keep the tensors. |

## Functions

| Name | Summary |
|---|---|
| [`offload_to_cpu`](offload_to_cpu.md) | Move a list of GPU tensors to CPU efficiently, preserving order. |

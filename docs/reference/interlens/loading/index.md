# `interlens.loading`

## Modules

- [`devices`](devices/index.md) — Where to put a model's *inputs*, which is not the same question as "what device is the model on".
- [`load`](load/index.md)
- [`model_cache`](model_cache/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`derive_chat_flags`](load/derive_chat_flags.md) | `interlens.loading.load` | Probe a tokenizer's chat template to derive `(supports_system_role, requires_alternating_roles)`. |
| [`device_map_kind`](devices/device_map_kind.md) | `interlens.loading.devices` | Interpret a `device` argument as a `device_map` when it names a sharding strategy, else `None`. |
| [`free`](model_cache/free.md) | `interlens.loading.model_cache` | Drop both caches and reclaim GPU memory. |
| [`input_device`](devices/input_device.md) | `interlens.loading.devices` | The device to place `input_ids` on for `model`: its input embedding's device. |
| [`is_sharded`](devices/is_sharded.md) | `interlens.loading.devices` | True if `model` was placed by `device_map=` across more than one device (including cpu/disk offload). |
| [`load_model`](load/load_model.md) | `interlens.loading.load` | Load a causal LM + tokenizer, sharing through the process-local caches. |
| [`load_tokenizer`](load/load_tokenizer.md) | `interlens.loading.load` | Load a tokenizer for `hf_id` (or a local path), defaulting `pad_token` to `eos_token` when absent — the single source of the pad-token convention, shared by `load_model` and `AutoModelParticipant` when it has to infer a tokenizer from a bare model. |

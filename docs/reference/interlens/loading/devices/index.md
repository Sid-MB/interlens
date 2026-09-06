# `devices`

Module `interlens.loading.devices`

Where to put a model's *inputs*, which is not the same question as "what device is the model on".

A single-device model answers both with one device, so `model.device` and `next(model.parameters()).device`
are interchangeable and every call site historically used whichever was shorter. A model sharded across GPUs by
`device_map=` answers them differently: its parameters live on several devices, and `input_ids` must land on
whichever one holds the **input embedding**, because that is the first module the tensor meets. Accelerate's
hooks move activations *between* shards for you, but they do not move the tensor you hand to `forward`.

Hence :func:`input_device` — one helper, used by every site that places `input_ids`, so single-device behavior
is bit-identical to before and sharded behavior is correct.

## Functions

| Name | Summary |
|---|---|
| [`device_map_kind`](device_map_kind.md) | Interpret a `device` argument as a `device_map` when it names a sharding strategy, else `None`. |
| [`input_device`](input_device.md) | The device to place `input_ids` on for `model`: its input embedding's device. |
| [`is_sharded`](is_sharded.md) | True if `model` was placed by `device_map=` across more than one device (including cpu/disk offload). |

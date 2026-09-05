# `available_devices`

List the devices to spread conversations across: every CUDA GPU, else a single mps/cpu fallback.

```python
available_devices() -> list[str]
```

Defined in [`interlens.runner.devices`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/devices.py#L21-L30)

Multi-GPU parallelism lives *across* conversations (they're independent); within one conversation turns are
sequential, so more GPUs never speed up a single conversation — only throughput over many.

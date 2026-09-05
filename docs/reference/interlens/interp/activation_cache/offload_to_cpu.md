# `offload_to_cpu`

Move a list of GPU tensors to CPU efficiently, preserving order.

```python
offload_to_cpu(tensors: list[torch.Tensor]) -> list[torch.Tensor]
```

Defined in [`interlens.interp.activation_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L28-L53)

Two wins over per-tensor `.to('cpu')`: (1) **batching** — same-shape/dtype tensors are stacked into one D2H
copy, so N transfer launches collapse to one per shape-group; (2) **pinned + non_blocking** — the copy goes
through a pinned host staging buffer, which hits full PCIe bandwidth (pageable D2H is throttled by CUDA's
internal bounce buffer) and lets the transfer overlap with compute. Results are cloned into pageable memory so
the (limited) pinned buffer is freed immediately rather than pinned for the cache's lifetime. Falls back to a
plain detach/copy when there's nothing to gain (CPU inputs or CUDA unavailable).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tensors` | `list[torch.Tensor]` | *required* |  |

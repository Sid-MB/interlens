# `found_level`

The found level implied by a set of probe means: the first (ascending) probed level whose mean fails the bar, else the highest level probed (the model never dropped below the bar).

```python
found_level(probe_means: dict[int, float], step_up: float = STEP_UP) -> int
```

Defined in [`interlens.arena.ratchet`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/ratchet.py#L58-L67)

Pure — both probing modes
and the ratchet's resume path decide through this one function.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `probe_means` | `dict[int, float]` | *required* |  |
| `step_up` | `float` | `STEP_UP` |  |

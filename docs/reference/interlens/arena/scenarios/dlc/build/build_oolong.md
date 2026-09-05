# `build_oolong`

OOLONG-Pairs instances: the 20 paper queries x the trec_coarse windows at `context_len`.

```python
build_oolong(
	out_dir: str | Path,
	*,
	context_len: int = 65536,
	seed: int = 42,
	probe32: bool = False,
	revision: str | None = None,
) -> list[Instance]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L217-L274)

Shards are
contiguous line-range blocks balanced by characters; concatenating them reproduces the window's data lines
exactly (asserted). Gold pair sets come from the dataset's own labels. `probe32=True` builds the reduced
5-instance probe bank with a raised final cap (the source experiment's 32K probe).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out_dir` | `str \| Path` | *required* |  |
| `context_len` | `int` | `65536` |  |
| `seed` | `int` | `42` |  |
| `probe32` | `bool` | `False` |  |
| `revision` | `str \| None` | `None` |  |

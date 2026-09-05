# `build_codeqa`

LongBench-v2 'Code Repository Understanding' instances, seeded-sampled stratified by difficulty.

```python
build_codeqa(
	out_dir: str | Path,
	*,
	n: int = 40,
	max_chars: int = 2600000,
	seed: int = 42,
	revision: str | None = None,
) -> list[Instance]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L279-L323)

Rows
whose context exceeds `max_chars` are excluded BEFORE sampling (exclusion count recorded in the bank
metadata, never silent). Shards are contiguous line-block splits balanced by characters (LongBench
contexts carry no reliable file markers).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out_dir` | `str \| Path` | *required* |  |
| `n` | `int` | `40` |  |
| `max_chars` | `int` | `2600000` |  |
| `seed` | `int` | `42` |  |
| `revision` | `str \| None` | `None` |  |

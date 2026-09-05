# `build_sniah`

Seeded PG-essay haystacks + one needle each; the needle is inserted BEFORE the 4-way split, so exactly one shard unknowingly holds it (holder index and depth recorded in the payload metadata).

```python
build_sniah(
	out_dir: str | Path,
	*,
	n: int = 50,
	total_tokens: int = 131072,
	seed: int = 42,
	revision: str | None = None,
) -> list[Instance]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L160-L194)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out_dir` | `str \| Path` | *required* |  |
| `n` | `int` | `50` |  |
| `total_tokens` | `int` | `131072` |  |
| `seed` | `int` | `42` |  |
| `revision` | `str \| None` | `None` |  |

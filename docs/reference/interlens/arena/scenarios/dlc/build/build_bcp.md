# `build_bcp`

BrowseComp-Plus instances: decrypt queries with the published canary, then assemble a per-instance corpus of gold + evidence docs (guaranteed present) + seeded filler negatives up to `k_docs`.

```python
build_bcp(
	out_dir: str | Path,
	*,
	n: int = 30,
	k_docs: int = 100,
	max_doc_chars: int = 20000,
	seed: int = 42,
	revision: str | None = None,
	corpus_revision: str | None = None,
) -> list[Instance]
```

Defined in [`interlens.arena.scenarios.dlc.build`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/scenarios/dlc/build.py#L358-L433)

Streams
the full document corpus once — run it somewhere with the bandwidth and memory for that.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `out_dir` | `str \| Path` | *required* |  |
| `n` | `int` | `30` |  |
| `k_docs` | `int` | `100` |  |
| `max_doc_chars` | `int` | `20000` |  |
| `seed` | `int` | `42` |  |
| `revision` | `str \| None` | `None` |  |
| `corpus_revision` | `str \| None` | `None` |  |

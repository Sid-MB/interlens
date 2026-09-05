# `annotation_from_episode`

Build an `EpisodeAnnotation` purely from an episode's inline oracle rows (`round_checkpoints`).

```python
annotation_from_episode(
	episode: dict,
	*,
	threshold: float = 1e-06,
) -> 'EpisodeAnnotation | None'
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L189-L203)

Returns `None` when the episode carries no inline oracle rows (a v0 dataset or a not-yet-annotated run), so
callers fall back to the mechanical-only path. Used by `report.py` to show oracle regret straight from a
stored run without a separate annotate pass.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `threshold` | `float` | `1e-06` |  |

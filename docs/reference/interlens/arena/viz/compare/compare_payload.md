# `compare_payload`

One seat-swap comparison, ready to render: both episode payloads, the slot alignment, the divergence point, the focal seat(s), and the score table.

```python
compare_payload(
	left: dict,
	right: dict,
	*,
	left_label: str = 'A',
	right_label: str = 'B',
	pair_fields: tuple[str, ...] = DEFAULT_PAIR_KEY,
) -> dict
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L197-L223)

Both sides keep their FULL episode payload, so the comparison page reuses the same transcript and frontier
renderer as a single-episode page — the frontier is drawn once, from the shared instance, with both
trajectories on it. The two episodes are not required to be a valid pair; a mismatch on the pairing key is
recorded in `pairing.matched` and surfaced as a warning instead of being rejected, because comparing two
deliberately unrelated episodes is sometimes exactly what a reader wants.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left` | `dict` | *required* |  |
| `right` | `dict` | *required* |  |
| `left_label` | `str` | `'A'` |  |
| `right_label` | `str` | `'B'` |  |
| `pair_fields` | `tuple[str, ...]` | `DEFAULT_PAIR_KEY` |  |

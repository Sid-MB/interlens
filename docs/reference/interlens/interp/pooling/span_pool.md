# `span_pool`

Pool `hidden[start:end]` for each span; returns `[len(spans), d_model]`.

```python
span_pool(
	hidden: torch.Tensor,
	spans: Sequence[Span],
	mode: Pool = 'mean',
) -> torch.Tensor
```

Defined in [`interlens.interp.pooling`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/pooling.py#L51-L77)

**Raises**

| Exception | Description |
|---|---|
| `ValueError` | on a non-2D `hidden`, an unknown `mode`, or an empty/out-of-bounds span. |

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `hidden` | `torch.Tensor` | *required* | `[seq, d_model]` per-token activations from one forward pass (any site, any layer). |
| `spans` | `Sequence[Span]` | *required* | half-open `(start, end)` token ranges. Spans may overlap and need not be sorted, but each must be non-empty and within `seq` — an empty span is a bug in the span construction, not a zero vector, so it raises rather than silently contributing nothing. |
| `mode` | `Pool` | `'mean'` | `"mean"` averages the span's tokens (order-insensitive; the probe default) while `"last"` takes the span's final token (the position that causally sees the whole span, and what a next-token readout actually conditions on). |

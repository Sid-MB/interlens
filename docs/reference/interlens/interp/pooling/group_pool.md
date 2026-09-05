# `group_pool`

Pool each *group* of spans into one vector; returns `([len(groups), d_model], valid[len(groups)])`.

```python
group_pool(
	hidden: torch.Tensor,
	groups: Sequence[Sequence[Span]],
	mode: Pool = 'mean',
	empty: Literal['zeros', 'raise'] = 'zeros',
) -> tuple[torch.Tensor, torch.Tensor]
```

Defined in [`interlens.interp.pooling`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/pooling.py#L80-L129)

The multi-span generalization of :func:`span_pool`: a group is an arbitrary set of (possibly scattered,
possibly overlapping) token ranges — e.g. every message one speaker contributed to a long transcript. Under
`"mean"` the average is over the union of the group's *token positions*, taken with multiplicity if spans
overlap, so a speaker's long message weighs more than a short one; under `"last"` the result is the final
token of the group's highest-ending span.

**Returns**

| Name | Type | Description |
|---|---|---|
|  | `torch.Tensor` | `(pooled, valid)` where `pooled` is `[len(groups), d_model]` and `valid` is a bool tensor that is |
|  | `torch.Tensor` | `False` exactly on rows pooled from an empty group. Always check `valid` before using a row: a zero |
|  | `tuple[torch.Tensor, torch.Tensor]` | row is indistinguishable from a genuine zero activation without it. |

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `hidden` | `torch.Tensor` | *required* | `[seq, d_model]` per-token activations. |
| `groups` | `Sequence[Sequence[Span]]` | *required* | one span list per output row. Groups are what varies across a batch of readouts sharing one forward pass, which is why they are the outer axis. |
| `mode` | `Pool` | `'mean'` | as in :func:`span_pool`. |
| `empty` | `Literal['zeros', 'raise']` | `'zeros'` | what an *empty group* means. `"zeros"` (default) emits a zero row and marks it invalid in the returned mask — the right behaviour when a group is legitimately absent (a party that has not spoken yet at this point in the dialogue), so callers can mask it downstream instead of dropping the row and losing alignment. `"raise"` treats it as a construction bug. |

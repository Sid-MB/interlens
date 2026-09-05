# `closing_turn_index`

The index of the turn that CLOSED the deal, or `None` when nothing closed.

```python
closing_turn_index(rows: list[dict], deal_index: int | None) -> int | None
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L399-L415)

The chart's AGREED square is the one mark that stands for an event without naming its turn, so a reader
clicking it has nowhere to land unless this is derived. Preference order, most specific first: the last
published closing action (accept, or a vote ballot) taken while the agreed deal was the one standing; then the
last published closing action at all (protocols where the standing deal is not recoverable from the ledger);
then the last turn, since an episode that closed a deal ended by doing so. Requires `rows` to have been
through :func:`public_ledger`, which is what annotates `published` and `standing_deal_index`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |
| `deal_index` | `int \| None` | *required* |  |

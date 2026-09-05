# `public_ledger`

Reconstruct what the seats publicly saw, from the per-turn records alone.

```python
public_ledger(rows: list[dict]) -> dict
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L345-L392)

Three things the page needs and no stored record carries directly:

- **published** — a turn that was a first attempt at a slot the seat later retried never reached the other
  seats: the engine's retry path returns the repair directive *before* publishing, so only the LAST turn in a
  `(round, phase, seat)` slot is public. A conversation view that showed the malformed attempt would be
  showing text no other party ever read.
- **offer_id** — the id a proposal was registered under. `OfferRegistry` mints ids sequentially over
  published proposals that resolved to a legal deal, so replaying that counter over the turns reproduces the
  exact ids the seats quoted back (`ACCEPT P2`), which the stored record keeps only on the accepting side.
- **standing_deal_index** — the deal on the table as of each turn: the offer this turn's action referenced if
  it referenced one, else the most recently registered offer, else `None`. This is the deal the per-agent
  issue view puts its marker on.

Returns `{"offers": {offer_id: {...}}, "prefix": str}` and annotates `rows` in place.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |

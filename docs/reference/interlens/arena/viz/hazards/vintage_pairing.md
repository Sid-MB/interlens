# `vintage_pairing`

What pairing THESE two episodes means, when either side carries a vintage hazard.

```python
vintage_pairing(left: dict, right: dict, labels: dict) -> str
```

Defined in [`interlens.arena.viz.hazards`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/hazards.py#L212-L243)

The intended and most valuable use of a comparison page is a spoiled run against its repaired counterpart —
the same instance and seed, one agent defect apart. But that is also the pairing whose deltas are easiest to
misread: they are the effect of the REPAIR, not of any behavioural manipulation, so a page that showed them
beside a seat-swap banner would invite exactly the wrong reading. Three cases, each stated in its own words:

- **one side spoiled** — a vintage contrast; the deltas measure the fix.
- **both spoiled by the same file** — vintage-matched, which is like-for-like and the one safe pooling of a
  spoiled arm.
- **both spoiled by different files** — two different defects, so the deltas mix them and belong to neither.

Silent when neither side carries a hazard, which is the ordinary case.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left` | `dict` | *required* |  |
| `right` | `dict` | *required* |  |
| `labels` | `dict` | *required* |  |

# `focal_seats`

The seats whose OCCUPANT KIND differs between the two episodes — the substitution being measured.

```python
focal_seats(left: dict, right: dict) -> list[dict]
```

Defined in [`interlens.arena.viz.compare`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/compare.py#L113-L124)

Each entry
is `{party, name, left_kind, right_kind}`. An empty list means the two runs put the same kind of agent in
every seat, which the page reports as "no seat swap detected" rather than inventing a focal seat.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `left` | `dict` | *required* |  |
| `right` | `dict` | *required* |  |

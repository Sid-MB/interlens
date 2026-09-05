# `occupant_defaults`

Each seat's DEFAULT occupant: the one it played its first recorded turn under.

```python
occupant_defaults(payload: dict) -> dict
```

Defined in [`interlens.arena.viz.page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/page.py#L345-L357)

Batch episodes carry no occupant at all and get an empty map. Live play stamps every turn with who held the
seat (`TurnRecord.occupant`), and a seat that never changed hands would otherwise wear the same badge on
every one of its turns — so the badge marks a DEPARTURE from this map, which is what a reader wants to see.
Derived from the payload rather than stored anywhere, so it always describes the transcript being rendered.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |

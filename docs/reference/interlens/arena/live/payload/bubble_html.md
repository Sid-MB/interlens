# `bubble_html`

The chat bubble for one turn, server-rendered by the visualizer's own `_chat_bubble`.

```python
bubble_html(payload: dict, turn: dict) -> str
```

Defined in [`interlens.arena.live.payload`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/payload.py#L87-L103)

Rendered server-side rather than reimplemented in JS for the same reason the static page renders it there:
there would otherwise be two bubble renderers to keep in step, and the browser copy would be the one that
quietly went stale.

`payload` must carry BOTH the seat table and the transcript so far (`{"seats": [...], "turns": [...]}`),
and `turn` should already be among those turns. The seats are the obvious half; the turns are the half that
is easy to skip and silently wrong to omit. `_chat_bubble` derives each seat's DEFAULT occupant from the
transcript and badges a turn only when it DEPARTS from that default — so against an empty `turns` no seat
has a known default, every badge suppresses itself, and a transcript renders as though no seat had ever
changed hands. That is not a degraded bubble, it is the swap badge silently doing nothing, which is the one
thing a live transcript shows that a static one cannot. Passing the accumulated rows is also what makes the
bubble byte-identical to the one a reload rebuilds, since a reload derives the same map from the same rows.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
| `turn` | `dict` | *required* |  |

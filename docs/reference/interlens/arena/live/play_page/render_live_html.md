# `render_live_html`

The complete live page for a session.

```python
render_live_html(snapshot: dict) -> str
```

Defined in [`interlens.arena.live.play_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/play_page.py#L239-L305)

`snapshot` is `LiveSession.snapshot()`: `{seq, payload, phase, awaiting, occupants, lobby}`. The
`payload` is a full `viz.episode_payload` — the same object the exported page is built from — so the page
is a correct static rendering of the game so far even before its JS runs, and `seq` is the sequence number
the page then subscribes from so nothing is missed between render and attach.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `snapshot` | `dict` | *required* |  |

# `render_lobby_html`

The complete lobby page.

```python
render_lobby_html(state: dict) -> str
```

Defined in [`interlens.arena.live.lobby_page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/lobby_page.py#L105-L154)

`state` is `SessionManager.lobby_state()`: the provider's listings (`banks`, `framings`, `models`,
`policies`) plus the current selection (`bank`, `framing`, `instance_id`, `seats`, `budget_usd`)
and whether a session is already running (`running`, `sid`). Self-contained — inline CSS and JS, no
network fetches on load — so it opens the same way the exported visualizer pages do.

Every key is read defensively: a provider with no banks, a state recorded before a key existed, or a bank
whose party count is not yet known all render a page that says so rather than raising. A lobby that 500s is
a lobby nobody can use to fix the configuration that broke it.

Parameters
----------
state : dict
    The lobby state described above. Embedded verbatim into the document as an inert JSON script tag, which
    is what the browser layer edits and POSTs back — so the page needs no fetch to become interactive.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `dict` | *required* |  |

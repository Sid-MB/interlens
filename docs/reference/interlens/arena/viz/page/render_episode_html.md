# `render_episode_html`

One self-contained interactive page for one episode.

```python
render_episode_html(payload: dict) -> str
```

Defined in [`interlens.arena.viz.page`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/page.py#L677-L757)

Sections, in order: the summary strip; the frontier chart with the play trajectory, the oracle's
recommendations, and every normative reference point (plus its numeric table view); the per-turn regret strip;
the system-prompt audit; and the transcript, where each turn shows what the model did NEXT TO what the rational
agent would have done there, with the regret between them. The tabbed sidebar (see :func:`_sidebar`) is sticky
alongside and follows the transcript as it scrolls.

The top bar carries the run name, the episode picker, and the quick read; where the picker's contents go is a
marker the exporter fills once every page of the run is known (see :func:`~.chrome.nav_group`), so a page
rendered on its own is still complete — it simply has nothing to navigate to.

An AUCTION payload takes :func:`render_auction_episode_html` instead: an auction has no deal space, so the
frontier chart, the solution-concept legend, the regret strip and the ballot table have nothing to draw,
and the four panels of design.md §10 stand in their place. Everything shared — the shell, the census and
vintage badges, the prompt audit, the transcript — is the same code on both paths.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |

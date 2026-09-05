# `nav_group`

The prev/next links and episode picker for the page at `position` in `rows`.

```python
nav_group(rows: list[dict], position: int, *, label_key: str = 'label') -> str
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L155-L175)

Written by the exporter into :data:`NAV_MARKER` once every page of the run is known. Prev/next are real
`<a href>` elements (so they work without scripting, and the keyboard bindings just follow them); the picker
is a `<select>` of every sibling page. A page at either end gets a disabled link rather than a missing one,
so the control row never changes width as a reader walks the run.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `rows` | `list[dict]` | *required* |  |
| `position` | `int` | *required* |  |
| `label_key` | `str` | `'label'` |  |

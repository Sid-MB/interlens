# `topbar`

The sticky top bar: run identity on the left, the navigation slot, the quick read, theme and help.

```python
topbar(
	brand: str,
	brand_href: str | None,
	quick: str = '',
	*,
	brand_title: str = '',
	nav: bool = True,
) -> str
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L122-L140)

`brand` names the run; `brand_href` links it to the run index, or is `None` on the index itself, where
there is nothing above to go up to. `quick` is the pre-rendered stat run — the two or three numbers a reader
wants without scrolling. The navigation slot is :data:`NAV_MARKER`, omitted entirely when `nav` is false
(the run index has no siblings to walk).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `brand` | `str` | *required* |  |
| `brand_href` | `str \| None` | *required* |  |
| `quick` | `str` | `''` |  |
| `brand_title` | `str` | `''` |  |
| `nav` | `bool` | `True` |  |

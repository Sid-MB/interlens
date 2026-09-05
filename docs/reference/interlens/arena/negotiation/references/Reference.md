# `Reference`

One bibliographic entry.

```python
Reference(key: str, citation: str, url: str, note: str = '')
```

Defined in [`interlens.arena.negotiation.references`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/references.py#L36-L52)

`key` is the short citation key used in docstrings; `citation` the full human-readable reference
(authors, year, title, venue, volume(issue):pages, DOI where available); `url` a stable link (publisher
landing page, JSTOR, arXiv, or open PDF). `note` optionally records what specifically this reference
grounds (e.g. the exact theorem/algorithm/page a module relies on).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `key` | `str` | *required* |  |
| `citation` | `str` | *required* |  |
| `url` | `str` | *required* |  |
| `note` | `str` | `''` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `citation` | `str` |  |
| `key` | `str` |  |
| `note` | `str` |  |
| `url` | `str` |  |

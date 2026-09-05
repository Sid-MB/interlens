# `ItemSlot`

One lot in the catalogue.

```python
ItemSlot(slot_id: int, name: str, blurb_slug: str, loading: tuple[float, ...])
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L266-L288)

PERSISTS across all stages; only its base value `B_jt` redraws.

`loading` is the public attribute-loading vector `w_j` (length `K`, aligned with
`AuctionSpec.attr_names`) printed numerically in the catalogue as well as narrated in `blurb`.
`blurb_slug` keys the prose template the scenario lane renders (the prose lives in docs/templates/, not
here), so wording changes never touch the payload.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `slot_id` | `int` | *required* |  |
| `name` | `str` | *required* |  |
| `blurb_slug` | `str` | *required* |  |
| `loading` | `tuple[float, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `blurb_slug` | `str` |  |
| `loading` | `tuple[float, ...]` |  |
| `name` | `str` |  |
| `slot_id` | `int` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'ItemSlot'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L285-L288)

Rebuild an :class:`ItemSlot` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L280-L283)

JSON-ready dict.

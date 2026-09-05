# `Issue`

One negotiable issue: a name and its discrete options (order defines the option indices).

```python
Issue(name: str, options: tuple[str, ...])
```

Defined in [`interlens.arena.negotiation.space`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L53-L79)

`options` are human-readable labels (e.g. site names, funding tiers); a deal never stores these, only the
integer index into this tuple, so option semantics stay out of the numeric game.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `options` | `tuple[str, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `n_options` | `int` | Number of options for this issue. |
| `name` | `str` |  |
| `options` | `tuple[str, ...]` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'Issue'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L76-L79)

Rebuild an `Issue` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L72-L74)

JSON-ready dict (`options` as a list).

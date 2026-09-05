# `RingSpec`

An instructed bidding ring: which seats are in it, and whether the instruction is given in the prompt.

```python
RingSpec(members: tuple[int, ...], instructed: bool = False)
```

Defined in [`interlens.arena.auction.spec`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L337-L354)

`instructed=False` records a ring the ANALYSIS designated (for a counterfactual) without telling the
seats; the committed cells never instruct a ring, so this is a tail/robustness knob.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `members` | `tuple[int, ...]` | *required* |  |
| `instructed` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `instructed` | `bool` |  |
| `members` | `tuple[int, ...]` |  |

## Methods {#methods}

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'RingSpec'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L351-L354)

Rebuild a :class:`RingSpec` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/spec.py#L347-L349)

JSON-ready dict.

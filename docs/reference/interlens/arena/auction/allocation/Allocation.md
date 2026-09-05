# `Allocation`

Who won each lot.

```python
Allocation(winner_of: tuple[int | None, ...])
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L122-L155)

`winner_of[j]` is the seat index that won lot `j`, or `None` if it went
unsold. The canonical allocation object every welfare, payment, and metric function consumes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `winner_of` | `tuple[int \| None, ...]` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `n_items` | `int` | Number of lots this allocation covers. |
| `winner_of` | `tuple[int \| None, ...]` |  |

## Methods {#methods}

## `bundle` {#bundle}

```python
bundle(self, seat: int) -> tuple[int, ...]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L134-L136)

The lots won by `seat`, in slot order.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `int` | *required* |  |

## `empty` {#empty}

```python
empty(n_items: int) -> 'Allocation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L151-L155)

The all-unsold allocation (welfare 0) — what a stage with no sale scores, never "excluded" (design.md §5.1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n_items` | `int` | *required* |  |

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'Allocation'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L146-L149)

Rebuild an :class:`Allocation` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L142-L144)

JSON-ready dict.

## `winners` {#winners}

```python
winners(self) -> tuple[int, ...]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L138-L140)

Seats that won at least one lot, ascending.

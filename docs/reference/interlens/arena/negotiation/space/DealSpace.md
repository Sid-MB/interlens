# `DealSpace`

The Cartesian product of all issues' options -- the full, enumerable set of possible deals.

```python
DealSpace(issues: tuple[Issue, ...])
```

Defined in [`interlens.arena.negotiation.space`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L82-L198)

Frozen and hashable so it can back a cached utility matrix. All indexing (`enumerate`, `deal_at`,
`index_of`) uses one consistent mixed-radix order (issue 0 most significant, last issue fastest), matching
`itertools.product` and the row order of the utility matrix.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `issues` | tuple[[Issue](Issue.md), ...] | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `issues` | tuple[[Issue](Issue.md), ...] |  |
| `n_issues` | `int` | Number of issues `J`. |
| `shape` | `tuple[int, ...]` | Per-issue option counts `(\|options_0\|, ..., \|options_{J-1}\|)` -- the mixed-radix base. |
| `size` | `int` | Total number of deals `\|D\| = prod_j \|options_j\|`. |

## Methods {#methods}

## `deal_at` {#deal_at}

```python
deal_at(self, index: int) -> Deal
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L131-L137)

The deal at flat position `index` in :meth:`enumerate` order (mixed-radix decode).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `index` | `int` | *required* |  |

## `deals` {#deals}

```python
deals(self) -> list[Deal]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L127-L129)

All deals as a list (convenience wrapper over :meth:`enumerate`).

## `enumerate` {#enumerate}

```python
enumerate(self) -> Iterator[Deal]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L123-L125)

Iterate all `|D|` deals in mixed-radix order (issue 0 most significant, last issue fastest).

## `from_json` {#from_json}

```python
from_json(d: dict) -> 'DealSpace'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L195-L198)

Rebuild a `DealSpace` from :meth:`to_json` output.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d` | `dict` | *required* |  |

## `index_of` {#index_of}

```python
index_of(self, deal: Deal) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L139-L151)

The flat position of `deal` in :meth:`enumerate` order (mixed-radix encode); inverse of :meth:`deal_at`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `named` {#named}

```python
named(self, deal: Deal) -> dict[str, str]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L153-L156)

Human-readable `{issue_name: option_label}` view of a deal -- for solutions, transcripts, and audits (never fed back into numeric scoring).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `option_index` {#option_index}

```python
option_index(self, issue: int | str, label: str) -> int
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L168-L179)

Index of an option `label` within an issue (given by position or name), tolerant of surrounding whitespace and case on both.

Raises `ValueError` if the label matches no option.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `issue` | `int \| str` | *required* |  |
| `label` | `str` | *required* |  |

## `parse` {#parse}

```python
parse(self, named: dict[str, str]) -> Deal
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L181-L189)

Map a `{issue_name: option_label}` proposal dict to a :data:`Deal` (option index per issue, in issue order), tolerant of case/whitespace on both issue names and option labels -- the inverse of :meth:`named`.

The dict must name every issue exactly once. Raises `ValueError` on a missing/unknown/duplicate issue or
an unknown option, so a scenario can turn a malformed model proposal into a clean parse error to log.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `named` | `dict[str, str]` | *required* |  |

## `strides` {#strides}

```python
strides(self) -> tuple[int, ...]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L111-L121)

Mixed-radix strides: `strides[j] = prod(shape[j+1:])` = the number of consecutive deals for which issue `j`'s option is held fixed under :meth:`enumerate`.

Used to map deal <-> flat index and to build
the utility matrix without materializing every deal.

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/space.py#L191-L193)

JSON-ready dict of the whole space.

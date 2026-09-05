# `JsonRecordStore`

A directory tree of JSON records, one file per record, written atomically.

```python
JsonRecordStore(root: str | Path)
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L259-L289)

The persistence shared by every arena record store: a `root`, an atomic `save` (write a sibling `.tmp`
then `os.replace`, so a crash mid-write leaves the previous file intact rather than a truncated one), and a
sorted recursive `load_all`. Subclasses supply only what actually differs — :meth:`path` (the on-disk
layout) and, optionally, `indent` (pretty-print) — so a new store is a few lines and inherits the crash
safety instead of re-deriving it.

Records are duck-typed: anything with a `to_json()` method can be saved.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `root` | `str \| Path` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `indent` | `int \| None` |  |
| `root` |  |  |

## Methods {#methods}

## `load_all` {#load_all}

```python
load_all(self, pattern: str = '**/*.json') -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L287-L289)

Every stored record under `root` matching `pattern`, as raw dicts, in sorted path order.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pattern` | `str` | `'**/*.json'` |  |

## `path` {#path}

```python
path(self, record) -> Path
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L275-L277)

The file `record` is stored at, creating its parent directory.

Subclasses define the layout.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `record` |  | *required* |  |

## `save` {#save}

```python
save(self, record) -> Path
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L279-L285)

Write `record.to_json()` atomically to :meth:`path` and return that path.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `record` |  | *required* |  |

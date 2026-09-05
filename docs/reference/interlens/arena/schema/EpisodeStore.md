# `EpisodeStore`

Per-episode JSON persistence, written atomically on every update so a crash loses at most one turn.

```python
EpisodeStore()
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L292-L327)

**Inherits from:** [JsonRecordStore](JsonRecordStore.md)

Layout: `{root}/{scenario}/{cell}/{arm}/{model_short}/L{level}/{episode_id}.json`.

## Methods {#methods}

## `load_all` {#load_all}

```python
load_all(self, scenario: str | None = None) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L304-L306)

Every stored episode, or only those of one `scenario` (the top layout level).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | `str \| None` | `None` |  |

## `path` {#path}

```python
path(self, ep: Episode) -> Path
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L297-L302)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ep` | [Episode](Episode.md) | *required* |  |

## `summary` {#summary}

```python
summary(self) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L308-L327)

A printable run-usage summary aggregated over every stored episode: episode counts, token totals, and dollar cost, broken down per (model, arm) — plus cost-per-success where outcomes carry `success`.

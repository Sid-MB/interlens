# `RunDir`

A run directory's three record stores, indexed for lookup: `episodes/`, `instances/`, and the annotation subdirectory named by `annotations_dirname` (`annotations/` by default), plus `manifest.json`.

```python
RunDir(root: str | Path, *, annotations_dirname: str = 'annotations')
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L774-L852)

Geometry
is built lazily and CACHED per instance, so a run whose 120 episodes share 6 instances builds 6 utility
matrices rather than 120.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `root` | `str \| Path` | *required* |  |
| `annotations_dirname` | `str` | `'annotations'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `advice` |  |  |
| `annotations_dirname` |  |  |
| `derivation` |  |  |
| `episodes_dir` |  |  |
| `manifest` |  |  |
| `root` |  |  |
| `vintage` |  |  |

## Methods {#methods}

## `episode_files` {#episode_files}

```python
episode_files(self) -> list[Path]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L805-L807)

Every episode JSON under the run, in sorted path order.

## `geometry` {#geometry}

```python
geometry(self, instance_id: str, cell_cfg: dict | None = None)
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L809-L825)

The cached geometry for an instance id: a :class:`GameGeometry` for a negotiation instance, an :class:`~interlens.arena.viz.auction_geometry.AuctionGeometry` for an auction one, `None` if the instance is missing or is neither.

Auction geometry is cached per `(instance_id, cell)`, not per instance: a single bank instance is
consumed by cells that override the mechanism and the horizon, so caching one spec per instance would
hand a Dutch episode the sealed cell's geometry — a real defect class in this lane's history.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
| `cell_cfg` | `dict \| None` | `None` |  |

## `payload` {#payload}

```python
payload(
	self,
	episode_path: str | Path,
	*,
	reconstruct: bool = True,
	auction_counterfactuals: bool = True,
) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L827-L852)

The render payload for one episode file in this run, with its instance, annotation, manifest, and cached geometry wired in.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_path` | `str \| Path` | *required* |  |
| `reconstruct` | `bool` | `True` |  |
| `auction_counterfactuals` | `bool` | `True` |  |

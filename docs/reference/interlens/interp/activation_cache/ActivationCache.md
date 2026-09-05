# `ActivationCache`

A queryable store of captured activations, tagged by conversation structure.

```python
ActivationCache(offload: OffloadLocation = 'cpu')
```

Defined in [`interlens.interp.activation_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L89-L147)

Records know which participant/turn/layer/site they came from, so a downstream probe can ask for "bob's turn
3, layer 18, the answer span" rather than juggling anonymous tensors. This is the object every interp
consumer reads; the harness never puts activations in `Message.metadata` (that would blow up `branch()`'s
transcript copy), so the cache is the single home for heavy tensors.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offload` | `OffloadLocation` | `'cpu'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `offload` |  |  |
| `records` | list[[ActivationRecord](ActivationRecord.md)] |  |

## Methods {#methods}

## `add` {#add}

```python
add(self, record: ActivationRecord) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L102-L107)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `record` | [ActivationRecord](ActivationRecord.md) | *required* |  |

## `add_batch` {#add_batch}

```python
add_batch(self, records: list[ActivationRecord]) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L109-L122)

Add many records at once, offloading all their tensors in one batched pinned transfer (see `offload_to_cpu`).

Preferred over a loop of `add` when a single capture pass produces many records —
it turns N GPU->CPU copies into one per shape-group.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `records` | list[[ActivationRecord](ActivationRecord.md)] | *required* |  |

## `at` {#at}

```python
at(
	self,
	*,
	participant=None,
	message_idx=None,
	layer=None,
	site='residual',
) -> torch.Tensor
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L134-L141)

Return the single matching tensor, erroring if the filters aren't unique — the ergonomic accessor for "give me exactly this activation".

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` |  | `None` |  |
| `message_idx` |  | `None` |  |
| `layer` |  | `None` |  |
| `site` |  | `'residual'` |  |

## `query` {#query}

```python
query(
	self,
	*,
	participant=None,
	message_idx=None,
	layer=None,
	site=None,
) -> list[ActivationRecord]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L124-L132)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` |  | `None` |  |
| `message_idx` |  | `None` |  |
| `layer` |  | `None` |  |
| `site` |  | `None` |  |

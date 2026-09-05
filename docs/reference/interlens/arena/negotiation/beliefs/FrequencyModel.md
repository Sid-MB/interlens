# `FrequencyModel`

Count-based opponent model: issue *stability* -> weights (an issue whose chosen option stays fixed across consecutive offers is important), option *frequency* -> values (a frequently-offered option is preferred).

```python
FrequencyModel(option_counts)
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L217-L253)

Induces a utility function; `update(offer)` is O(J). Often competitive with Bayes.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `option_counts` |  | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `J` |  |  |
| `option_counts` |  |  |

## Methods {#methods}

## `copy` {#copy}

```python
copy(self) -> 'FrequencyModel'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L247-L253)

An independent model with the same counts — the fold state a cached replay hands out.

## `update` {#update}

```python
update(self, offer: Deal) -> 'FrequencyModel'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L229-L236)

Fold one observed opponent offer into the counts.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `offer` | `Deal` | *required* |  |

## `utility` {#utility}

```python
utility(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L242-L245)

Induced utility of `deal` in `[0, 1]` (per-issue value normalized to its max).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `weights` {#weights}

```python
weights(self) -> np.ndarray
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L238-L240)

Normalized issue weights.

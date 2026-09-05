# `OpponentType`

One enumerated hypothesis about an opponent: normalized issue `weights` (sum 1), a per-issue evaluator `shapes` tuple, and a reservation `threshold` on the induced `[0, 1]` utility scale.

```python
OpponentType(weights: tuple, shapes: tuple, threshold: float, option_counts: tuple)
```

Defined in [`interlens.arena.negotiation.beliefs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L76-L100)

`utility(deal) = sum_j weights[j] * evaluator(shapes[j])[deal[j]]` lies in `[0, 1]`; `accepts(deal)`
iff that utility is at least `threshold`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `weights` | `tuple` | *required* |  |
| `shapes` | `tuple` | *required* |  |
| `threshold` | `float` | *required* |  |
| `option_counts` | `tuple` | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `option_counts` | `tuple` |  |
| `shapes` | `tuple` |  |
| `threshold` | `float` |  |
| `weights` | `tuple` |  |

## Methods {#methods}

## `accepts` {#accepts}

```python
accepts(self, deal: Deal) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L98-L100)

Whether a myopically-rational opponent of this type would accept `deal`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

## `evaluator_table` {#evaluator_table}

```python
evaluator_table(self) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L89-L91)

Per-issue option-value arrays (cached-free; cheap).

## `utility` {#utility}

```python
utility(self, deal: Deal) -> float
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/beliefs.py#L93-L96)

Additive utility of `deal` in `[0, 1]`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `deal` | `Deal` | *required* |  |

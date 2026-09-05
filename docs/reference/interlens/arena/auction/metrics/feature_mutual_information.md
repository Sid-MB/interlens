# `feature_mutual_information`

`I(feature ; y)` for every column of an `(n_obs, n_features)` integer feature matrix.

```python
feature_mutual_information(features, y) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L623-L637)

Returns `{"per_feature", "max", "mean", "joint", "n"}`; `joint` treats the whole feature ROW as one
categorical symbol, which is the sharper statistic when a code is carried by a combination of features
rather than any one of them.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `features` |  | *required* |  |
| `y` |  | *required* |  |

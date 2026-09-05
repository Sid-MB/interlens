# `dyad_mutual_information`

Per-dyad mutual information between message features and the sender's value bin, with a WITHIN-GROUP permutation null (design.md §9.3 item 3, [lo2023]).

```python
dyad_mutual_information(
	features,
	value_bins,
	*,
	groups=None,
	n_perm: int = 999,
	seed: int = 20260815,
	statistic: str = 'joint',
) -> dict
```

Defined in [`interlens.arena.auction.metrics`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/metrics.py#L640-L672)

`features` is `(n_obs, n_features)` integer message features for ONE ordered dyad; `value_bins` the
sender's quantized top-item value per observation; `groups` an optional label per observation (the
instance id) so the null shuffles payloads only WITHIN an instance, preserving the dyad structure and any
instance-level difference in how much there is to say. `n_perm` shuffles give a p-value of
`(1 + #{MI_perm >= MI_obs}) / (1 + n_perm)`, which is bounded away from 0 and never reports a
significance the resampling cannot support.

Returns `{"mi", "p", "n", "n_perm", "null_mean"}`. On independent inputs the p-value is uniform by
construction, which the tests check.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `features` |  | *required* |  |
| `value_bins` |  | *required* |  |
| `groups` |  | `None` |  |
| `n_perm` | `int` | `999` |  |
| `seed` | `int` | `20260815` |  |
| `statistic` | `str` | `'joint'` |  |

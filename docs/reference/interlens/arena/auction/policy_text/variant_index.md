# `variant_index`

The seeded surface-variant index, `hash(instance_id, seat, stage, template_id) mod n_variants`.

```python
variant_index(
	instance_id: str,
	seat: int,
	stage: int,
	template_id: str,
	n_variants: int,
) -> int
```

Defined in [`interlens.arena.auction.policy_text`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/policy_text.py#L107-L114)

Uses SHA-256 rather than Python's `hash`, which is salted per process and would make the same episode
render differently on two runs -- the variant must be reproducible and arm-invariant, since a variant that
moved between arms would be a confound in exactly the comparison Q5 is about.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
| `seat` | `int` | *required* |  |
| `stage` | `int` | *required* |  |
| `template_id` | `str` | *required* |  |
| `n_variants` | `int` | *required* |  |

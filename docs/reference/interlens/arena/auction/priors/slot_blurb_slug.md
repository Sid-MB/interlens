# `slot_blurb_slug`

A deterministic prose-template KEY for a slot, derived from its loading vector: the dominant positive attribute, or `"balanced"` when none dominates, suffixed `"_light"` when the vector's mass is negative.

```python
slot_blurb_slug(loading: np.ndarray) -> str
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L188-L200)

The prose itself lives in `docs/templates/` — a slug keeps the wording out of the payload, so
a prompt-wording change never edits a stored instance.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `loading` | `np.ndarray` | *required* |  |

# `json_safe`

`value` with every non-finite float replaced by `None`, recursively through dicts and lists.

```python
json_safe(value)
```

Defined in [`interlens.arena.viz.auction_geometry`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/auction_geometry.py#L373-L388)

An auction outcome legitimately carries `NaN`: a stage with no losing bid has no suppression denominator
and an on-path multi-lot benchmark has no counterfactual revenue. Both are "no measurement here", and both
are hostile to a web page in two distinct ways — `json.dumps` emits the bare token `NaN`, which
`JSON.parse` rejects and which therefore disables every script on the page, and a formatter that prints
it renders the absence of a measurement as the word "nan" beside real numbers. Converting to `None` at
the payload boundary fixes both, and it is the same claim the analysis makes: absent, not zero.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `value` |  | *required* |  |

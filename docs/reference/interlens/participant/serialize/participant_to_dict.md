# `participant_to_dict`

Serialize participant `p` to a plain dict of its constructor kwargs (no weights).

```python
participant_to_dict(p) -> dict
```

Defined in [`interlens.participant.serialize`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/serialize.py#L28-L54)

Dispatches on the
participant kind via duck-typed attributes (a local model participant has `hf_id`; an API one has
`provider`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `p` |  | *required* |  |

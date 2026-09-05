# `participant_from_dict`

Rebuild a (lazy) participant from :func:`participant_to_dict` output.

```python
participant_from_dict(data: dict, device='cuda', registry=None)
```

Defined in [`interlens.participant.serialize`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/serialize.py#L57-L91)

Local models resolve their family class
from the HF config and load lazily on `device`; API participants are reconstructed directly.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `data` | `dict` | *required* |  |
| `device` |  | `'cuda'` |  |
| `registry` |  | `None` |  |

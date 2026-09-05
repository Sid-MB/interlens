# `SeatRequest`

One pending generation: a seat that must speak now, with the exact view its model is conditioned on.

```python
SeatRequest(
	episode_id: str,
	seat: str,
	view: list[dict],
	phase: str,
	round: int,
	max_tokens: int = 2048,
	meta: dict = dict(),
	provisional: bool = False,
)
```

Defined in [`interlens.arena.schema`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/schema.py#L96-L107)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `seat` | `str` | *required* |  |
| `view` | `list[dict]` | *required* |  |
| `phase` | `str` | *required* |  |
| `round` | `int` | *required* |  |
| `max_tokens` | `int` | `2048` |  |
| `meta` | `dict` | `dict()` |  |
| `provisional` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `episode_id` | `str` |  |
| `max_tokens` | `int` |  |
| `meta` | `dict` |  |
| `phase` | `str` |  |
| `provisional` | `bool` |  |
| `round` | `int` |  |
| `seat` | `str` |  |
| `view` | `list[dict]` |  |

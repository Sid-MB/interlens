# `public_position`

The broadcast: presence and public-profile fit at stage start, holdings mid-stage.

```python
public_position(
	*,
	instance_id: str,
	seat: int,
	stage: int,
	display_name: str,
	fit_lots,
	held_lots,
	single_item: bool,
	fit_word: str = 'neutral',
	opening: bool = True,
) -> str
```

Defined in [`interlens.arena.auction.policy_text`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/policy_text.py#L123-L136)

Nothing else.

`fit_lots` is the public fit score `a_i . w_j`, so a rival gains nothing it could not compute -- which
is the point: the seat is present and legible on the channel without disclosing anything.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance_id` | `str` | *required* |  |
| `seat` | `int` | *required* |  |
| `stage` | `int` | *required* |  |
| `display_name` | `str` | *required* |  |
| `fit_lots` |  | *required* |  |
| `held_lots` |  | *required* |  |
| `single_item` | `bool` | *required* |  |
| `fit_word` | `str` | `'neutral'` |  |
| `opening` | `bool` | `True` |  |

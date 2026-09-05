# `generate_games`

Generate `count` independent games with consecutive base seeds `seed, seed+1, ...` (all other knobs forwarded to :func:`generate_game`).

```python
generate_games(count: int, seed: int = 0, **kwargs={}) -> list[tuple[GameSpec, dict]]
```

Defined in [`interlens.arena.negotiation.generate`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/generate.py#L310-L313)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `count` | `int` | *required* |  |
| `seed` | `int` | `0` |  |
| `kwargs` |  | `{}` |  |

# `make_preset`

Look up a preset by `name` and build it, returning `(GameSpec, analysis, protocol_cfg)`.

```python
make_preset(name: str, **kwargs={}) -> tuple[GameSpec, dict, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L249-L257)

`kwargs` are
the preset's own knobs (see each factory). Raises `KeyError` (listing the known presets) on an unknown name.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `kwargs` |  | `{}` |  |

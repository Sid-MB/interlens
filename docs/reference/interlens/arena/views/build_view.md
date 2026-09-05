# `build_view`

Render `events` (`[{seat|'MODERATOR', content, only?}]`, public unless `only` names seats) into an alternating per-speaker view for `seat`, ending with `phase_prompt` as the final user turn.

```python
build_view(seat: str, system: str, events: list[dict], phase_prompt: str) -> list[dict]
```

Defined in [`interlens.arena.views`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/views.py#L38-L61)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `system` | `str` | *required* |  |
| `events` | `list[dict]` | *required* |  |
| `phase_prompt` | `str` | *required* |  |

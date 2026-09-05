# `replay_episode`

Feed a stored episode's turns back through `scenario` and return the recomputed outcome dict.

```python
replay_episode(
	scenario: Scenario,
	instance: Instance,
	episode: dict,
	*,
	on_turn=None,
	on_request=None,
) -> dict
```

Defined in [`interlens.arena.replay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/replay.py#L92-L106)

`episode` is the stored JSON record (`Episode.to_json()` shape; the arena experiments' records load
directly). The instance must be the one the episode was played on (`episode['instance_id']`).

`on_turn` and `on_request` are as in :func:`apply_prefix`, whose full-replay case this is.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `episode` | `dict` | *required* |  |
| `on_turn` |  | `None` |  |
| `on_request` |  | `None` |  |

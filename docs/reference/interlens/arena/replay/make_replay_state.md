# `make_replay_state`

A fresh state built exactly the way `episode` was: same instance, arm, seed, and `cell_cfg` (minus the resolved personas, which `make_state` re-resolves identically from the seed).

```python
make_replay_state(scenario: Scenario, instance: Instance, episode: dict) -> dict
```

Defined in [`interlens.arena.replay`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/replay.py#L45-L52)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) | *required* |  |
| `instance` | [Instance](../schema/Instance.md) | *required* |  |
| `episode` | `dict` | *required* |  |

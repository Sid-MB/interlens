# `interlens_team_policy`

Control Tower policy backed by a private Interlens planner-reviewer-executor team.

```python
interlens_team_policy(
	state: TaskState,
	participant_factory: str,
	mode: str = 'honest',
	planner_max_tokens: int = 512,
	reviewer_max_tokens: int = 512,
) -> InterlensGenerateFn
```

Defined in [`interlens.integrations.control_tower`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/integrations/control_tower.py#L558-L581)

**Returns**

`InterlensGenerateFn` — An Inspect-compatible generate function whose external actions remain fully visible to Control Tower.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `TaskState` | *required* | Current Control Tower sample. In `attack` mode its side-task goal is used for the private prompt. |
| `participant_factory` | `str` | *required* | Zero-argument `module:function` factory for the local policy under evaluation. |
| `mode` | `str` | `'honest'` | `"honest"` preserves Control Tower's task prompt. `"attack"` privately replaces it with the same side-task scaffold used by :func:`interlens_attack_policy`. |
| `planner_max_tokens` | `int` | `512` | Maximum output tokens used by each internal planner generation. Values around 256–1024 trade deliberation depth against the three-call team's inference cost. |
| `reviewer_max_tokens` | `int` | `512` | Maximum output tokens used by each internal reviewer generation. Values around 256–1024 trade critique depth against inference cost. |

# `interlens_attack_policy`

Control Tower attack policy backed by an Interlens local participant.

```python
interlens_attack_policy(state: TaskState, participant_factory: str) -> InterlensGenerateFn
```

Defined in [`interlens.integrations.control_tower`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/integrations/control_tower.py#L542-L555)

**Returns**

`InterlensGenerateFn` — An adapted participant that pursues the configured side task while Control Tower retains tool execution and
monitoring authority.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `TaskState` | *required* | Current Control Tower sample. Its private side-task goal becomes the policy-only system prompt. |
| `participant_factory` | `str` | *required* | Zero-argument `module:function` participant factory. Use the same factory as the matched honest condition so only the evaluation objective changes. |

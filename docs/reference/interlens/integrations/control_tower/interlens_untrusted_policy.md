# `interlens_untrusted_policy`

Control Tower external untrusted policy backed by a local Interlens participant.

```python
interlens_untrusted_policy(
	state: TaskState,
	participant_factory: str,
	system_prompt: str | None = None,
) -> InterlensGenerateFn
```

Defined in [`interlens.integrations.control_tower`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/integrations/control_tower.py#L519-L539)

Select this function with
`--untrusted-policy interlens.integrations.control_tower:interlens_untrusted_policy`.

**Returns**

`InterlensGenerateFn` — The adapted participant's Inspect-compatible generate function.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `state` | `TaskState` | *required* | Current Control Tower sample state. It establishes the per-sample factory lifetime; task content itself arrives through the generate function's messages. |
| `participant_factory` | `str` | *required* | Zero-argument `module:function` reference returning a fresh local Interlens participant, for example `"my_project.policies:local_qwen"`. |
| `system_prompt` | `str \| None` | `None` | Optional private system prompt. Leave unset for ordinary honest evaluations; set only when a static alternate scaffold is part of the registered experimental condition. |

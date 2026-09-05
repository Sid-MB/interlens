# `participant_generate`

Adapt one local Interlens participant to Inspect's model-generation protocol.

```python
participant_generate(
	participant: Any,
	*,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	system_prompt: str | None = None,
) -> InterlensGenerateFn
```

Defined in [`interlens.integrations.control_tower`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/integrations/control_tower.py#L342-L390)

**Returns**

`InterlensGenerateFn` — An async function with the `UntrustedPolicyGenerateFn` signature expected by Control Tower.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` | `Any` | *required* | Participant implementing `generate_step`. Normally this is a `ModelParticipant` returned by `AutoModelParticipant.from_pretrained`. A single instance is used for one Control Tower sample. |
| `steering` |  | `None` | Optional Interlens steering spec applied to every model call. `None` uses the participant default. |
| `capture` |  | `None` | Optional Interlens capture request applied to every model call. |
| `patch` |  | `None` | Optional Interlens activation patch applied to every model call. |
| `return_logprobs` | `bool` | `False` | Whether Interlens should collect generated-token log probabilities. Enable only when later analysis needs them because it increases memory use. |
| `system_prompt` | `str \| None` | `None` | Optional private system prompt. `None` preserves Control Tower's history; a string replaces the public system prompt before local generation while leaving the monitor-visible history unchanged. |

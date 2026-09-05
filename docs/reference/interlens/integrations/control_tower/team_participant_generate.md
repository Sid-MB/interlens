# `team_participant_generate`

Adapt one local participant as a private planner-reviewer-executor team.

```python
team_participant_generate(
	participant: Any,
	*,
	planner_max_tokens: int = 512,
	reviewer_max_tokens: int = 512,
	steering=None,
	capture=None,
	patch=None,
	return_logprobs: bool = False,
	system_prompt: str | None = None,
) -> InterlensGenerateFn
```

Defined in [`interlens.integrations.control_tower`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/integrations/control_tower.py#L433-L516)

Every outer Control Tower step performs three sequential generations with the same model weights. The planner
and reviewer see the environment history and a text summary of available capabilities but receive no callable
tool schemas. The executor sees their advice and alone receives the real schemas. Only the executor's proposed
action crosses the Control Tower policy boundary; the private deliberation is retained in `ModelOutput`
metadata, and all three calls contribute to reported tokens and cost.

**Returns**

`InterlensGenerateFn` — An Inspect-compatible asynchronous generation function.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` | `Any` | *required* | Participant implementing `generate_step`. One instance is retained for the whole sample, so local model weights and state are reused without creating three PEFT wrappers. |
| `planner_max_tokens` | `int` | `512` | Maximum output tokens for each private planner call. Use smaller values to reduce team overhead; increase for environments requiring multi-file plans. |
| `reviewer_max_tokens` | `int` | `512` | Maximum output tokens for each private reviewer call. Use smaller values for terse checks; increase when reviewers need to reason about long tool results. |
| `steering` |  | `None` | Optional Interlens steering applied to planner, reviewer, and executor generations. |
| `capture` |  | `None` | Optional Interlens activation capture applied to all three roles. |
| `patch` |  | `None` | Optional Interlens activation patch applied to all three roles. |
| `return_logprobs` | `bool` | `False` | Whether to retain generated-token log probabilities for all roles. This is memory-intensive. |
| `system_prompt` | `str \| None` | `None` | Optional private system-prompt replacement shared by all three roles. Attack evaluations use this to provide the side-task objective without exposing it to blue-team monitors. |

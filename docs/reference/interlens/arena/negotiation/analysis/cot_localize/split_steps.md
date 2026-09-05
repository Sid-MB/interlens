# `split_steps`

Split a CoT scratchpad into reasoning steps.

```python
split_steps(scratchpad: str) -> list[str]
```

Defined in [`interlens.arena.negotiation.analysis.cot_localize`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/cot_localize.py#L29-L44)

Default heuristic: numbered/bulleted lines ("1.", "-",
"Step 3:") start new steps, otherwise blank-line-separated paragraphs, otherwise single newlines. A scenario
that emits already-structured steps should pass them in directly rather than re-splitting.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scratchpad` | `str` | *required* |  |

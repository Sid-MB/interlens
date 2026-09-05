# `induced_action_hook`

HOOK (unimplemented): re-derive the action a truncated CoT induces by force-continuing the model from the joined `prefix_steps`; wrap with the oracle's divergence check to form `is_divergent` for `localize_first_divergence`.

```python
induced_action_hook(prefix_steps: list[str])
```

Defined in [`interlens.arena.negotiation.analysis.cot_localize`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/cot_localize.py#L69-L75)

Model generation is out of the metrics layer's scope.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `prefix_steps` | `list[str]` | *required* |  |

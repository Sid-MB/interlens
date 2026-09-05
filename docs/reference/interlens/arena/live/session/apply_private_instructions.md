# `apply_private_instructions`

Append `instructions` to `participant`'s `private_context` as one labelled segment, and return it.

```python
apply_private_instructions(participant: Any, instructions: str) -> Any
```

Defined in [`interlens.arena.live.session`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L87-L103)

The whole override mechanism: a live operator gives one seat a persona or a hidden agenda without editing a
scaffold, and the text folds into that seat's view exactly where its own private material already goes. A
no-op for empty instructions or for a participant with no `private_context` (a policy seat reads no prose).

Shared with :meth:`ScenarioProvider.build_model_seat` implementations so a model seat's override and a
scripted seat's are the same segment in the same place rather than two spellings of the same idea.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `participant` | `Any` | *required* |  |
| `instructions` | `str` | *required* |  |

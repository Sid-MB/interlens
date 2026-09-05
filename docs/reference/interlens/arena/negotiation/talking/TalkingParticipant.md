# `TalkingParticipant`

A :class:`PolicyParticipant` for talking policies: it merges the one-time `declaration` with the bound policy's per-turn `commentary` into the turn's public message, and (for listening policies) parses every `talking_rational` statement in the view into `state.statements` before the policy runs.

```python
TalkingParticipant(*args=(), personas: tuple = (), **kwargs={})
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L519-L577)

**Inherits from:** [PolicyParticipant](../policy_participant/PolicyParticipant.md)

Parameters (beyond :class:`PolicyParticipant`)
----------
personas : tuple[str, ...]
    Seat-ordered public names, used to resolve `name`-keyed statements from LLM seats to seat indices.
    Empty disables name resolution (index-keyed statements still parse).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `args` |  | `()` |  |
| `personas` | `tuple` | `()` |  |
| `kwargs` |  | `{}` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `last_parse_census` | `dict` |  |
| `personas` |  |  |

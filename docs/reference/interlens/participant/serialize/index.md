# `interlens.participant.serialize`

Persist a participant to / from its own constructor kwargs (for `Conversation.save` / `load`).

This is same-type persistence — a participant serializes the recipe it was built from (an HF id + generation
settings, or an API provider + model id) and rebuilds an *equivalent lazy* participant. It is NOT a conversion to
a separate config type (participants ARE their own recipe now); weights are never serialized and reload lazily on
the target device. `private_context` (`ContextItem`s) is inlined; local tools are stored by name and
re-resolved from the tool registry on load.

## Functions

| Name | Summary |
|---|---|
| [`participant_from_dict`](participant_from_dict.md) | Rebuild a (lazy) participant from :func:`participant_to_dict` output. |
| [`participant_to_dict`](participant_to_dict.md) | Serialize participant `p` to a plain dict of its constructor kwargs (no weights). |

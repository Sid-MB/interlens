# `factories`

Module `interlens.factories`

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `ModelLike` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AutoModelParticipant`](AutoModelParticipant.md) | Resolver for creating `Participant` instances automatically from HuggingFace model identifiers, local model paths, or already-loaded `PreTrainedModel`s. |

## Functions

| Name | Summary |
|---|---|
| [`conversation_from_ids`](conversation_from_ids.md) | Deprecated thin alias for :func:`conversation_from_models` / :meth:`Conversation.from_models`, kept for back-compat. |
| [`conversation_from_models`](conversation_from_models.md) | Scaffold a conversation from a tuple of `models` — each an HF id (str) or an already-loaded `PreTrainedModel` (see `ModelLike`). |

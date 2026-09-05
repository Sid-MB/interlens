# `conversation_from_models`

Scaffold a conversation from a tuple of `models` — each an HF id (str) or an already-loaded `PreTrainedModel` (see `ModelLike`).

```python
conversation_from_models(
	models: tuple[ModelLike, ...],
	names: tuple[str, ...] = ('a', 'b'),
	device: str | torch.device = 'cuda',
	dtype: torch.dtype = torch.bfloat16,
	shared_context: str | None = None,
	shared_system_prompt: str | None = None,
	prompt: PromptLike = None,
	**gen_kwargs: Any = {},
) -> Conversation
```

Defined in [`interlens.factories`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L103-L138)

Each becomes a family-correct participant via
`AutoModelParticipant.from_`; `names` gives them their identities. **The order of `models` / `names`
is the speaking order** — the first speaks first unless you pass `first=` to `run` — and `**gen_kwargs`
are forwarded to every participant.

This is the implementation behind :meth:`Conversation.from_models` (which just wraps it). If two ids resolve
to the same HF model the weights are loaded **once** and shared (via `load_model`'s process cache).

Two ways to seed the opening, without touching the transcript by hand:

- `shared_context` — a neutral, `moderator`-voiced turn everyone sees (scenario/topic framing); pair with
  `shared_system_prompt` for system-role instructions. These are the principled framing knobs (serialized
  into a template).
- `prompt` — a *participant*-voiced opener: a `str` is attributed to the LAST participant so the first
  speaker replies to it, a `Message` sets the author explicitly. Use this when the opener should read as
  something a speaker said rather than moderator framing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `models` | `tuple[ModelLike, ...]` | *required* |  |
| `names` | `tuple[str, ...]` | `('a', 'b')` |  |
| `device` | `str \| torch.device` | `'cuda'` |  |
| `dtype` | `torch.dtype` | `torch.bfloat16` |  |
| `shared_context` | `str \| None` | `None` |  |
| `shared_system_prompt` | `str \| None` | `None` |  |
| `prompt` | `PromptLike` | `None` |  |
| `gen_kwargs` | `Any` | `{}` |  |

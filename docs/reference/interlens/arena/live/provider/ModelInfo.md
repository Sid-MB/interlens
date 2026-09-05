# `ModelInfo`

One model the lobby may offer for an `llm` seat.

```python
ModelInfo(
	model_id: str,
	label: str,
	provider: str,
	thinking_modes: tuple[str, ...] = ('off',),
	supports_temperature: bool = True,
	available: bool = True,
	unavailable_reason: str | None = None,
	metered: bool = True,
	default: bool = False,
)
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L105-L156)

Parameters
----------
model_id : str
    The provider's id, exactly as a participant factory wants it (`"claude-fable-5"`, a HF repo id, ...).
label : str
    What the lobby shows a human. Free text.
provider : str
    Which backend serves it (`"anthropic"`, `"openai"`, `"local"`, ...) — drives the "needs an API key"
    warning and whether the seat is metered.
thinking_modes : tuple[str, ...]
    The extended-thinking settings this model actually accepts, in the order the lobby should show them
    (e.g. `("off", "on")`, or `("on",)` for a model that cannot turn thinking off). The lobby offers ONLY
    these: the Claude-5 family rejects several combinations outright (Fable cannot disable thinking, Haiku
    refuses adaptive thinking and effort levels), and a 400 from a live seat mid-game is a wasted session.
supports_temperature : bool
    Whether a temperature may be sent at all. False for the Claude-5 models, which hard-error on any
    temperature — so the lobby hides the control rather than sending a default and failing.
available : bool
    Whether this model can be used right now (API key present, local weights on disk / a GPU visible). An
    unavailable model is still LISTED — greyed out with `unavailable_reason` — because silently omitting it
    looks like the model does not exist.
unavailable_reason : str | None
    Why not, in the user's terms (`"ANTHROPIC_API_KEY is not set"`). `None` when available.
metered : bool
    Whether turns from this model cost money and must count against the session's budget cap.
default : bool
    Whether this is the model a new `llm` seat starts on. The PROVIDER owns that choice — it is the half
    that knows which model this experiment actually wants played — so the lobby never spells a model id of
    its own. Flag at most one; :func:`default_model_id` resolves several (or none) by availability and list
    order rather than raising, since a lobby is the wrong place to discover a misconfigured flag.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *required* |  |
| `label` | `str` | *required* |  |
| `provider` | `str` | *required* |  |
| `thinking_modes` | `tuple[str, ...]` | `('off',)` |  |
| `supports_temperature` | `bool` | `True` |  |
| `available` | `bool` | `True` |  |
| `unavailable_reason` | `str \| None` | `None` |  |
| `metered` | `bool` | `True` |  |
| `default` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `available` | `bool` |  |
| `default` | `bool` |  |
| `label` | `str` |  |
| `metered` | `bool` |  |
| `model_id` | `str` |  |
| `provider` | `str` |  |
| `supports_temperature` | `bool` |  |
| `thinking_modes` | `tuple[str, ...]` |  |
| `unavailable_reason` | `str \| None` |  |

## Methods {#methods}

## `to_json` {#to_json}

```python
to_json(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L151-L156)

The lobby's wire form (see :func:`~interlens.arena.live.events.lobby_state`).

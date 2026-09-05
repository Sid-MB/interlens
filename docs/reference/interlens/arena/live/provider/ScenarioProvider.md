# `ScenarioProvider`

What an experiment must supply for its games to be playable live.

```python
ScenarioProvider()
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L350-L397)

**Inherits from:** `Protocol`

Implement it anywhere — it is a structural protocol, so no import of interlens is needed to satisfy it — and
hand an instance to :func:`~interlens.arena.live.run_live_server`. The listing methods drive the lobby and
are called on every lobby render (keep them cheap or cache them); `prepare` and `build_model_seat` are
called when a game starts and when a seat is swapped.

## Methods {#methods}

## `build_model_seat` {#build_model_seat}

```python
build_model_seat(
	self,
	model_id: str,
	*,
	thinking: str = 'off',
	meter: Any = None,
	extra_instructions: str = '',
) -> Any
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L385-L397)

Construct the participant for one `llm` seat and return it.

`thinking` is one of that model's `thinking_modes`; `meter` is the session's `UsageMeter`, which
the participant must charge so the budget cap actually binds; `extra_instructions`, when non-empty, is
appended to the participant's `private_context` as one labelled segment.

The returned participant must be SAFE TO OWN: the session may set per-seat instructions on it and may
hold several seats on the same model at once, so a provider that caches participants by model id has to
return a wrapper or copy rather than a shared object — otherwise one seat's private instructions leak
into another's view.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *required* |  |
| `thinking` | `str` | `'off'` |  |
| `meter` | `Any` | `None` |  |
| `extra_instructions` | `str` | `''` |  |

## `list_banks` {#list_banks}

```python
list_banks(self) -> list[BankInfo]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L359-L361)

The instance banks the lobby may draw from, in display order.

May be empty (the lobby then says so
rather than offering a broken picker).

## `list_framings` {#list_framings}

```python
list_framings(self) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L363-L366)

The framings/skins available, as `{"framing_id", "label", "description"}` dicts.

A framing rewrites
an instance's surface story (issue names, party names, the cover narrative) without touching its payoff
structure, so it is chosen independently of the bank.

## `list_models` {#list_models}

```python
list_models(self) -> list[ModelInfo]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L368-L370)

Every model an `llm` seat may be assigned, INCLUDING ones that are currently unavailable (each carrying its own reason).

Availability is reported, never silently filtered — see :class:`ModelInfo`.

## `prepare` {#prepare}

```python
prepare(
	self,
	bank: str,
	framing: str,
	instance_id: str | None,
	overrides: dict | None = None,
) -> PreparedGame
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L372-L383)

Assemble one playable game.

`bank` and `framing` are ids from the listings; `instance_id` picks an instance from the bank, and
`None` means "choose one" (the provider decides how — random, or the bank's first). `overrides` is
the lobby's free-form extra configuration (seed, deadline, difficulty, oracle selection) — a dict rather
than fixed parameters because what is tunable is the experiment's business, not the server's.

Raises `ValueError` for an unknown bank/framing/instance, which the server turns into a 400 with the
message shown in the lobby.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bank` | `str` | *required* |  |
| `framing` | `str` | *required* |  |
| `instance_id` | `str \| None` | *required* |  |
| `overrides` | `dict \| None` | `None` |  |

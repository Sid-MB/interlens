# `SessionManager`

The server's session registry. v1 holds ONE active session at a time.

```python
SessionManager(provider: ScenarioProvider, run_dir: Any, rng: random.Random | None = None)
```

Defined in [`interlens.arena.live.session`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L594-L823)

One at a time is a real constraint, not a shortcut: a live game is meant to be watched and played by the
person who started it, budgets are per-session, and a second concurrent game would double an API bill with no
way to tell whose it was. The manager keeps the lobby configuration between games so starting a second game
with the same lineup is one click.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `provider` | [ScenarioProvider](../provider/ScenarioProvider.md) | *required* |  |
| `run_dir` | `Any` | *required* |  |
| `rng` | `random.Random \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `active` | [LiveSession](LiveSession.md) \| None | The running session, or `None` when the server is sitting in the lobby. |
| `provider` |  |  |
| `run_dir` |  |  |

## Methods {#methods}

## `get` {#get}

```python
get(self, sid: str) -> LiveSession
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L646-L649)

The session with this id.

Raises `KeyError` when it is unknown or has been replaced.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sid` | `str` | *required* |  |

## `lobby_state` {#lobby_state}

```python
lobby_state(self) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L696-L731)

The current lobby configuration plus the provider's listings — what the lobby page renders from.

The complete set of keys, since three things render from this one dict (the lobby page, `GET
/api/lobby`, and the `lobby_state` event) and a key that exists in only two of them is a drift waiting
to happen:

- `banks` / `framings` / `models` — the provider's listings, as their `to_json()` dicts. An
  unavailable model is LISTED with its `unavailable_reason`, never filtered out.
- `policies` — the names in `table.POLICY_FACTORIES`, for the rational/oracle picker.
- `seat_kinds` — the kinds a seat may take (:data:`~interlens.arena.live.provider.SEAT_KINDS`).
- `seat_names` — seat order for the chosen bank, so the cards can be labelled before a game exists.
- `bank` / `framing` / `instance_id` / `seats` / `budget_usd` — the current selection.
  `instance_id` is `""` for "let the provider choose", which is also what the lobby may post back.
- `running` / `sid` / `phase` / `episode_id` — whether a session is live and how to reach it.
  `running` is a plain bool so a page can branch on it; `sid` is what `/play` is keyed by.
- `error` — the last refused edit's message, `""` when the last one was accepted.

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L689-L694)

Stop any active session and return the server to the lobby.

## `start` {#start}

```python
start(self, lobby: dict | None = None) -> LiveSession
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L651-L675)

Prepare a game from the lobby configuration and start a session on it.

Raises `ValueError` if a
session is already running (stop it first) or the configuration is invalid.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `lobby` | `dict \| None` | `None` |  |

## `update_lobby` {#update_lobby}

```python
update_lobby(self, patch: dict) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/session.py#L733-L754)

Merge a partial lobby edit (one changed seat, a new bank) and return the updated state.

Validates
against the provider's listings so an unknown model or policy is refused at edit time, not at start.

Recognized keys: `bank`, `framing`, `instance_id` (`""` = let the provider choose),
`budget_usd` (`null` = uncapped, which only a lineup with no metered seat may start),
`overrides`, `shuffle` (`true` permutes the current lineup among the seats — see
:func:`shuffled_seats` — and records the permutation in `last_shuffle`; any later seat edit clears that
record, since a permutation that no longer maps the lineup to a previous one describes nothing), and the
seats. `seats` is the whole list; a single-card edit may instead send
`{"seat_idx": i, "seat": {...}}` (`index` is accepted as a synonym), so a lobby with six seats does
not have to round-trip all six to change one. Both forms are supported — send whichever the page finds
simpler.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `patch` | `dict` | *required* |  |

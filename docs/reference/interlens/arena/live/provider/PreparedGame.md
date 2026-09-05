# `PreparedGame`

One playable game, fully assembled — the provider's answer to a lobby configuration.

```python
PreparedGame(
	instance: Any,
	scenario: Any,
	game: Any,
	arm: str,
	deadline: int,
	cfg: dict = dict(),
	seat_names: tuple[str, ...] = (),
	instance_json: dict = dict(),
	scaffold: Any = None,
	manifest: dict = dict(),
)
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L294-L347)

Everything the session needs to construct a table and run an episode, and nothing about WHO plays: the seats
are configured separately (:class:`SeatConfig`) so the same prepared game can be replayed with a different
lineup, and so a mid-game swap has the game objects already in hand.

Parameters
----------
instance : Any
    The `Instance` to play, already framed (the provider applies the framing before returning).
scenario : Any
    The `Scenario` object (a `ScorableNegotiation` for negotiation play), with its oracle stack attached.
game : Any
    The `GameSpec` behind the instance — the source of the private score sheets, the deal space and the
    discount. The human dock reads its seat's sheet from here, and computable seats are bound against it.
arm : str
    The arm the episode is played under, recorded on it and passed to `scenario.make_state`. REQUIRED, and
    deliberately without a default: the scenario validates it and a value it does not know is fatal on the
    first wave (`ScorableNegotiation` accepts `moves_chat` / `moves_only` / `team` / `solo`, or any
    `team`-prefixed variant, and raises `unknown arm` otherwise). There is no arm every scenario would
    accept, so any default here would be a value that happens to work for one scenario and kills the session
    for the next — better to make the provider name one. `moves_chat` is the usual choice for live
    negotiation, since a live game with no talk channel gives a human nothing to do but submit moves.
deadline : int
    Total rounds `T`. REQUIRED for the same reason: it is bound into every computable seat's concession
    schedule (`policy_seat(deadline=...)`) and shown to the human as the round they are deciding under, so
    a deadline that disagrees with the game is not a cosmetic default but a table playing to the wrong clock
    — and silently, unlike a bad `arm`. Read it off the game (`spec.rounds`) rather than restating it.
cfg : dict
    The episode `cfg` (cell id and sweep configuration) passed to `run_episode`.
seat_names : tuple[str, ...]
    Seat display names in seat order (`arena.schema.PERSONAS` for negotiation). The routing key.
instance_json : dict
    `instance.to_json()` — what the visualizer's geometry is built from, kept beside the object so the
    session does not re-serialize it once per turn.
scaffold : Any
    The framing/scaffold record, when the provider has one, for provenance on the page. Optional.
manifest : dict
    Run-level provenance to hand the page (invocation, oracle list, seat kinds), shaped like a run's
    `manifest.json` so the visualizer reads it with the code it already has.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instance` | `Any` | *required* |  |
| `scenario` | `Any` | *required* |  |
| `game` | `Any` | *required* |  |
| `arm` | `str` | *required* |  |
| `deadline` | `int` | *required* |  |
| `cfg` | `dict` | `dict()` |  |
| `seat_names` | `tuple[str, ...]` | `()` |  |
| `instance_json` | `dict` | `dict()` |  |
| `scaffold` | `Any` | `None` |  |
| `manifest` | `dict` | `dict()` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `arm` | `str` |  |
| `cfg` | `dict` |  |
| `deadline` | `int` |  |
| `game` | `Any` |  |
| `instance` | `Any` |  |
| `instance_json` | `dict` |  |
| `manifest` | `dict` |  |
| `scaffold` | `Any` |  |
| `scenario` | `Any` |  |
| `seat_names` | `tuple[str, ...]` |  |

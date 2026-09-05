# `awaiting_human`

A human seat is blocked on input — everything the control dock renders from.

```python
awaiting_human(
	seat: str,
	seat_idx: int,
	turn_idx: int,
	round_: int,
	phase: str,
	state: dict,
	sheet: dict,
	legal: dict,
	deadline: int,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L173-L200)

`state` is the machine-readable `negotiation_state` block parsed out of the seat's own view (the offer
registry, the standing offer, the round), so the UI reads the same state the seat was conditioned on rather
than scraping the prompt. `sheet` is that seat's PRIVATE score sheet (`{values, threshold}`) — it is
private to this seat and to this browser, which is the point of playing it. `legal` is the verdict on what
may be submitted now (:data:`LEGAL_ACTION_DEFAULTS` names the keys): the server validates anyway, but the
form should not offer a move that will be refused. `deadline` is the game's total round count `T`, for
the "round r of T" the human is deciding under.

`legal` is NORMALIZED here — every key in :data:`LEGAL_ACTION_DEFAULTS` is present in the emitted event,
missing ones taking their "not available" default. So the browser can read `legal.can_reject` directly
instead of guarding for undefined, and a capability a caller forgot to compute fails CLOSED (the control is
not offered) rather than rendering a button that 400s. Extra keys are passed through untouched, so a later
move type does not need this builder changed to reach the page.

`turn_idx` is the one field a PARTICIPANT cannot fill in. The engine passes `turn` to `generate` only
alongside a capture request (`EpisodePool._generate_once` puts it in the kwargs inside the
`if capture is not None` branch), and live play never captures — so a human seat does not know the
episode's turn index and publishes :data:`UNKNOWN_TURN_IDX`. The SESSION, which counts the turns it has
streamed, stamps the real index before the frame goes out, exactly as it does for `turn_started`. Anything
else publishing this event owes the same fix-up: a negative `turn_idx` reaching the browser would point
the dock's "your move on turn N" at a turn that does not exist.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `seat` | `str` | *required* |  |
| `seat_idx` | `int` | *required* |  |
| `turn_idx` | `int` | *required* |  |
| `round_` | `int` | *required* |  |
| `phase` | `str` | *required* |  |
| `state` | `dict` | *required* |  |
| `sheet` | `dict` | *required* |  |
| `legal` | `dict` | *required* |  |
| `deadline` | `int` | *required* |  |

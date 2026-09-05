# `turn_appended`

A committed, persisted turn.

```python
turn_appended(
	turn: dict,
	bubble_html: str,
	rounds_used: int,
	outcome_partial: dict | None = None,
) -> tuple[str, dict]
```

Defined in [`interlens.arena.live.events`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/events.py#L162-L170)

`turn` is the payload turn dict — byte-identical to what a full
`episode_payload` rebuild would produce for it, oracle annotations and occupant included — which is what
lets the client push it straight onto `PAYLOAD.turns`. `bubble_html` is that turn's chat bubble,
server-rendered by the same function the static page uses. `outcome_partial` is the episode's outcome so
far when the scenario has one (a closed deal mid-episode), else `None`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn` | `dict` | *required* |  |
| `bubble_html` | `str` | *required* |  |
| `rounds_used` | `int` | *required* |  |
| `outcome_partial` | `dict \| None` | `None` |  |

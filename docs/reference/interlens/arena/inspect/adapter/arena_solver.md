# `arena_solver`

Play one arena instance (from the sample's metadata) with the evaluated model in every seat.

```python
arena_solver(
	arm: str = 'team',
	communication: str = 'messaging',
	turn_max_tokens: int = 2048,
	messaging_turns: int = 24,
)
```

Defined in [`interlens.arena.inspect.adapter`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/adapter.py#L151-L194)

The default `communication="messaging"` runs the autonomous point-to-point variant — each seat gets its
private framing and the agents self-organize via `send_message`/`read_message` mailboxes with pings and
the priority scheduler (recorded as transcript events), with the finalizer's fenced
`{"answer"}`/`{"proposal"}` JSON scored exactly as in the protocol mode. `"round_robin"` runs the
scenario's published turn protocol through the arena engine — the mode the shipped v0 transcript dataset
was produced under, so use it when comparing against those cells. Scenarios with no sound messaging
reduction (the security dilemma) reject messaging; their tasks pin the protocol via
`Scenario.default_communication`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `arm` | `str` | `'team'` |  |
| `communication` | `str` | `'messaging'` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `messaging_turns` | `int` | `24` |  |

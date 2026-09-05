# `SessionStopped`

Raised inside a blocked :meth:`HumanParticipant.generate` when the session is stopped.

```python
SessionStopped()
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L66-L71)

**Inherits from:** `RuntimeError`

Deliberately an exception rather than a fabricated pass: a stopped session's episode must end as an error,
because "the player was still deciding when the server shut down" and "the player chose to do nothing" are
different facts and only one of them is behaviour.

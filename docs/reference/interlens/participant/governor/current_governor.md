# `current_governor`

The installed process-wide governor, or `None` when the run is ungoverned (the pre-existing behaviour: the client's own `max_in_flight` semaphore is then the only concurrency bound).

```python
current_governor() -> RateLimitGovernor | None
```

Defined in [`interlens.participant.governor`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L439-L442)

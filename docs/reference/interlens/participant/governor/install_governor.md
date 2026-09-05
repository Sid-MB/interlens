# `install_governor`

Install (or with `None`, remove) the process-wide governor and return it.

```python
install_governor(governor: RateLimitGovernor | None = None) -> RateLimitGovernor | None
```

Defined in [`interlens.participant.governor`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/governor.py#L429-L436)

Every hosted-API request
issued afterwards passes through it, from any thread or event loop. Called once by the campaign launcher
before any cell starts; installing replaces any previous governor rather than stacking.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `governor` | [RateLimitGovernor](RateLimitGovernor.md) \| None | `None` |  |

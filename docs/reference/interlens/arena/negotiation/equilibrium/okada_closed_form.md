# `okada_closed_form`

The Okada 1996 unanimity closed form: `{"proposer_keeps": 1 - delta(n-1)/n, "responder_gets": delta/n, "value": 1/n}`.

```python
okada_closed_form(n: int, delta: float) -> dict
```

Defined in [`interlens.arena.negotiation.equilibrium`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L166-L169)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `delta` | `float` | *required* |  |

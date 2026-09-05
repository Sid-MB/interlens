# `schedule_signature`

The full co-step schedule of a conversation: its turn count + the per-position participant signatures.

```python
schedule_signature(conv, turns: int)
```

Defined in [`interlens.runner.batched`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/batched.py#L40-L45)

Convs
that share a signature have an identical speaker/model schedule, so `co_step` can batch each round's
same-position turns across them safely. Grouping specs by this (instead of by turn count alone) makes batched
execution correct for ANY mix of specs — a heterogeneous lineup simply forms its own group.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conv` |  | *required* |  |
| `turns` | `int` | *required* |  |

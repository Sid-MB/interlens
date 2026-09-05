# `config_fingerprint`

Stable SHA256 over `config`, canonicalized (sorted keys, compact separators, non-JSON values repr'd).

```python
config_fingerprint(config: dict | None) -> str
```

Defined in [`interlens.arena.rollouts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L153-L161)

This is the set's protocol identity. Anything that changes what an episode *means* belongs in `config`
(scaffold, framing, info condition, arms, oracle stack, bank hash, model id); anything that merely changes
how it was scheduled (concurrency, chunking, artifact root) must NOT, or a resumed run refuses itself.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `config` | `dict \| None` | *required* |  |

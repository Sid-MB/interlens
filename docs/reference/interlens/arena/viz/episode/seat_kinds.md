# `seat_kinds`

Which seats an LLM played and which a computable policy played.

```python
seat_kinds(episode: dict, manifest: dict | None = None) -> dict
```

Defined in [`interlens.arena.viz.episode`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/episode.py#L80-L135)

Returns `{"kinds": {seat_name: "llm" | "policy"}, "source": str, "detail": str}`. The manifest's recorded
`invocation` is authoritative when present, because it names the table type exactly:
`all_llm` / `all_rational` assign every seat; `mixed` puts the models in the leading seats and fills the
rest with policies; `reverse_mixed` / `advocate_mixed` make exactly `--rational-seat` a policy.

Without a manifest the kinds are INFERRED from generation accounting: a policy seat is pure Python, so every
one of its turns records `n_tokens_out == 0`, while an LLM seat generated text. The inference is reported as
such (`source="inferred"`) so a reader never mistakes it for recorded ground truth.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode` | `dict` | *required* |  |
| `manifest` | `dict \| None` | `None` |  |

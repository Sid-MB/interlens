# `co_step`

Co-step `convs` (a shared turn schedule) in lockstep, batching each round's same-position turns.

```python
co_step(
	convs,
	turns: int | None,
	*,
	max_batch_size: int | None = None,
	group_seed: int = 0,
)
```

Defined in [`interlens.runner.batched`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/runner/batched.py#L82-L131)

Each round: every conversation's current speaker is the same schedule position, so their views are gathered
and generated in one left-padded batch (sub-batched into `max_batch_size` waves). The representative
participant drives the batch — safe because same-schedule participants wrap the *same* cached model + tokenizer.
Message hooks run per conversation before commit.

Stop conditions are honored on the batched path too: each conversation's combined stop (its `run_until` /
ambient budget, resolved once) can cap the round's `max_new_tokens` (the wave uses the conservative min so no
conversation overshoots its budget) and drops a conversation from later rounds once it fires. `turns` may be
`None` for a purely stop-driven run (e.g. a matched-compute `TokenBudget`), bounded by a large safety cap.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `convs` |  | *required* |  |
| `turns` | `int \| None` | *required* |  |
| `max_batch_size` | `int \| None` | `None` |  |
| `group_seed` | `int` | `0` |  |

# `round_ledger`

Per round, every advised seat's turn side by side — the shape an all-advised arm is read in.

```python
round_ledger(turns: dict[str, dict]) -> list[dict]
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L215-L252)

On a one-advised-seat arm a round holds one advised turn and this is the transcript in a narrower column. On
an ALL-advised arm a round holds five, each seat deciding against its own planner at the same table state,
and the question that matters is no longer "did this seat take its advice" but "what did the five of them do
to each other" — which is a question this view lets a reader put, not one it answers.

**It reports arithmetic and asserts no mechanism.** The intuitive account — that simultaneous concessions
cancel where a lone concession transfers — was written down as a prediction with a falsifier and tested on
an all-advised corpus; both prespecified correlations came back null, so it is a conjecture and this view
must not be captioned as showing it. What the view is FOR is being the substrate a design that *assigns* the
number of advised seats would be read against.

Each round reports its rows plus the arithmetic over them: how many seats overrode, and the total own-surplus
those overrides moved. `conceded` sums only the NEGATIVE deltas and `claimed` only the positive ones,
kept apart rather than netted, because a round where two seats each gave up twenty points is not the same
round as one where nobody moved, and a single net figure cannot tell them apart.

`advice_overridden_toward` is defined only where a seat proposed a package of its own (an accept names an
offer, not a deal), so `n_measured` reports the denominator beside the sums rather than letting a round
with one measurable override read like a round with five.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turns` | `dict[str, dict]` | *required* |  |

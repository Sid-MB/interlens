# `turn_signatures`

Every failure signature carried by one stored turn (a `TurnRecord.to_json()` dict); `set()` if healthy.

```python
turn_signatures(
	turn: dict,
	*,
	engine_fabricated: bool | None = None,
	cap_floor: int = 0,
) -> set[str]
```

Defined in [`interlens.arena.engine`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/engine.py#L248-L293)

:func:`gen_failures` answers one question — did the ENGINE fabricate this turn — and a run can be perfectly
clean by that measure while a quarter of its turns say nothing. This separates the causes that wear the same
:data:`EMPTY_TURN_PLACEHOLDER` string, because each needs a different fix:

- `placeholder` — the turn's content IS the placeholder. Always accompanied by exactly one cause below.
- `gen_failed` — the engine fabricated it (no model was ever successfully called). `engine_fabricated`
  is the authority when given; :func:`gen_failures` computes it, reading the v1.2 `gen_failed` stamp and
  falling back to the value signature only on older records. Raising the token cap CANNOT fix this.
- `empty_gen` — generation really happened but reduced to nothing after `strip_think`: the model spent
  its whole budget inside an unterminated `<think>` block and emitted no visible action. This IS model
  behaviour and the fix is a larger cap or thinking disabled. **Measured at 24.4% of turns for a thinking-on
  Qwen3-32B at a 2,048-token cap, against 0.0% with thinking off**, while `fabrication` correctly read
  0.000 throughout — the engine did its job and a quarter of the turns were still silent.
- `truncated` — a genuine cap hit: a truncating `stop_reason`, or output that reached the turn's budget as
  :func:`truncation_budget` resolves it (`cap_floor` is passed straight through, for a legacy run whose real
  budget is only known from its manifest). The token clause is the only one that fires on local runs, which
  never populate `stop_reason`, and it is deliberately NOT applied to a pre-v1.3 hosted-API turn, whose
  stored `cap` is the protocol's number rather than the one the request used.
- `noop_action` / `parse_failed` — behavioural symptoms reported alongside, NOT causes. `noop_action`
  also fires on legitimate no-op play, and on some placeholder turns does not fire at all.

Do NOT screen for any of this with `parse_ok` or "is the content empty". Both are fooled: the placeholder
is a non-empty string that parses into a well-formed no-op, and on a degraded cell `parse_ok` is
*anti*-correlated with turn quality (measured 1.000 on the silent arm against 0.958 on the healthy one,
because placeholders parse flawlessly and real model prose sometimes does not).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `turn` | `dict` | *required* |  |
| `engine_fabricated` | `bool \| None` | `None` |  |
| `cap_floor` | `int` | `0` |  |

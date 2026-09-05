# `Pass`

Take NO formal move this turn — the typed form of the talk-only pass a scenario already accepts as `{"action": "none"}`.

```python
Pass()
```

Defined in [`interlens.arena.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/actions.py#L122-L139)

**Inherits from:** [Action](Action.md)

It is not part of the package-deal move vocabulary :func:`parse_action` validates: a scenario recognizes the
`none`/`pass` wire tag BEFORE it reaches the parser (`ScorableNegotiation.apply`), records the turn as
`atype="none"`, and charges neither a syntax nor a legality error. It exists so a
`PolicyParticipant` can express "stand pat" in the same typed vocabulary as the other moves instead of
being forced into a move it does not want — the alternatives are all worse: `Walk` permanently removes the
seat (and kills the deal outright if it holds a veto), `Reject` needs a live offer id and is illegal in the
forced-final proposal phase, and re-`Propose`-ing a deal already on the table mints a SECOND offer id for
it, splitting the accept votes across two ids so neither can reach unanimity.

One caveat, from the same short-circuit: a MOVES-ONLY game (no talk channel) treats a turn with no formal
action as a syntax error, so a policy that can emit `Pass` belongs in a chat-enabled arm.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `kind` | `str` |  |

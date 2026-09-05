# `scorable`

The repaired `ScorableNegotiation` as an Inspect task, generated through the game-preset registry (:mod:`interlens.arena.negotiation.games`).

```python
scorable(
	game: str = 'scorable',
	level: int = 0,
	n_instances: int = 10,
	seed0: int = 1,
	arm: str = 'moves_chat',
	turn_max_tokens: int = 2048,
	token_limit: int | None = None,
	messaging_turns: int = 24,
) -> Task
```

Defined in [`interlens.arena.inspect.tasks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/inspect/tasks.py#L205-L238)

`game` picks the preset — `scorable` (the default
multi-party multi-issue game, at difficulty `level`), `ultimatum`, `divide_dollar`, or
`bilateral_multiissue` — and the preset's protocol cfg (single-shot / fixed-proposer / majority) rides in
each sample's `cfg` so `inspect view` renders the right protocol. The arena solver plays every seat with
the evaluated model; `arm` is `moves_chat` / `moves_only` / `team` (`solo` = the single-agent
control). Run e.g. `inspect eval interlens.arena.inspect/scorable --model anthropic/claude-sonnet-5
-T game=ultimatum -T arm=moves_only`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` | `str` | `'scorable'` |  |
| `level` | `int` | `0` |  |
| `n_instances` | `int` | `10` |  |
| `seed0` | `int` | `1` |  |
| `arm` | `str` | `'moves_chat'` |  |
| `turn_max_tokens` | `int` | `2048` |  |
| `token_limit` | `int \| None` | `None` |  |
| `messaging_turns` | `int` | `24` |  |

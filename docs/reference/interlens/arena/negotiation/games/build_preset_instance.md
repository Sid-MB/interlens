# `build_preset_instance`

Build a solver-verified arena :class:`~interlens.arena.schema.Instance` from a preset, plus the scenario `protocol_cfg` to play it under -- the one-call bridge from a preset name to a runnable game.

```python
build_preset_instance(
	name: str,
	*,
	level: int = 0,
	seed: int = 0,
	instance_name: str = 'scorable_negotiation',
	**kwargs={},
) -> tuple[Instance, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L260-L283)

Reuses :func:`~interlens.arena.negotiation.generate.build_instance` for the `(GameSpec, analysis) ->
Instance` wrap (`payload = GameSpec.to_json()`, `solution` = the analysis dict, exact ceiling/floor), so
a preset instance is indistinguishable from a generated one to the scenario, oracle, annotation, and atlas
layers. `seed` is threaded to the preset factory (used by randomized presets like `bilateral_multiissue`
/ `scorable`, ignored by the deterministic `ultimatum` / `divide_dollar`) and stamped on the Instance;
`level` is the Instance difficulty tag and (for `scorable`) the generator ladder level. `kwargs` are the
preset's knobs.

Returns `(instance, protocol_cfg)` -- pass `protocol_cfg` as the scenario `cfg` (or merged into it) so
the shared `ScorableNegotiation` state machine runs the preset's protocol variant.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | *required* |  |
| `level` | `int` | `0` |  |
| `seed` | `int` | `0` |  |
| `instance_name` | `str` | `'scorable_negotiation'` |  |
| `kwargs` |  | `{}` |  |

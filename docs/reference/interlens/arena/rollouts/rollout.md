# `rollout`

Run `instances x seeds x arms` into the rollout set at `out` (creating or resuming it) and return it.

```python
rollout(
	*,
	scenario: Scenario | ScenarioFactory,
	instances: Sequence[Instance],
	participant,
	out: str | Path,
	model: str | None = None,
	arms: Sequence[str] = ('team',),
	seeds: Sequence[int] = (0,),
	cfg: dict | None = None,
	config: dict | None = None,
	engine: str = 'auto',
	concurrency: int = 16,
	meter: UsageMeter | None = None,
	estimated_cost: float | None = None,
	allow_mismatch: bool = False,
	gen_config: dict | None = None,
	invocation: Sequence[str] | None = None,
	artifacts: dict | None = None,
) -> RolloutSet
```

Defined in [`interlens.arena.rollouts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L525-L631)

Swapping the model is one argument (`participant`), swapping the game is one argument (`scenario`);
everything else is bookkeeping this function does for you: skip the (instance, seed, arm) triples already on
disk, point the pool's store at the set so episodes persist as they finish, then append + update the manifest.

Parameters
----------
scenario : Scenario | ScenarioFactory
        The game. A plain `Scenario` is shared by every episode; a callable `(instance) -> Scenario` is
        called per instance (for a per-game oracle stack).
instances : Sequence[Instance]
        The bank. Saved into `<out>/instances/` so analysis can resolve every `instance_id`.
participant : Participant | ParticipantFactory
        Who plays. A participant object is SHARED across episodes (correct for stateless model weights, and the
        precondition for batched co-stepping); a callable `(instance, arm, seed) -> Participant` is called per
        episode (required for policy seats, whose belief/offer state is per-episode mutable).
out : str | Path
        The rollout-set directory. Existing sets are resumed; the config fingerprint must match.
model : str | None
        Model identity for the manifest. Defaults to `config["model"]` when present.
arms, seeds : Sequence
        The protocol arms and episode seeds; one episode per (instance, arm, seed).
cfg : dict | None
        The per-episode situational config handed to the scenario and stored on each episode as `cell_cfg`.
config : dict | None
        The set's protocol identity (see :func:`config_fingerprint`). Pass everything that defines the condition;
        a resumed set refuses to run if it disagrees.
engine : str
        `"auto"` (default) uses :class:`BatchedEpisodePool` co-stepping when `participant` is a single shared
        object exposing `generate_batch` (a local model — the 5-20x path) and the async
        :class:`EpisodePool` otherwise; `"batched"` / `"async"` force one. A per-episode factory can never be
        batched, since the whole point of co-stepping is one shared model.
concurrency : int
        Max concurrent episodes for the async pool (API width is the client's own cap). Ignored when batched.
meter : UsageMeter | None
        Shared spend ledger for hosted-API seats; with `estimated_cost` the pool reserves before each episode,
        so a dollar cap stops the run instead of merely describing it afterwards.
allow_mismatch : bool
        Forwarded to :meth:`RolloutSet.append` — see its docstring; leaves a permanent stamp.
gen_config : dict | None
        Provider/sampling provenance recorded on every episode.
invocation : Sequence[str] | None
        The command line to record (defaults to `sys.argv`).
artifacts : dict | None
        Artifact links to record on the manifest (transcript dir, HF dataset URL, ...).

Raises
------
RolloutConfigMismatch
        If `out` exists under a different protocol config and `allow_mismatch` is False. Raised BEFORE any
        episode runs, so a mis-pointed resume costs nothing.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scenario` | [Scenario](../scenario/Scenario.md) \| ScenarioFactory | *required* |  |
| `instances` | Sequence[[Instance](../schema/Instance.md)] | *required* |  |
| `participant` |  | *required* |  |
| `out` | `str \| Path` | *required* |  |
| `model` | `str \| None` | `None` |  |
| `arms` | `Sequence[str]` | `('team',)` |  |
| `seeds` | `Sequence[int]` | `(0,)` |  |
| `cfg` | `dict \| None` | `None` |  |
| `config` | `dict \| None` | `None` |  |
| `engine` | `str` | `'auto'` |  |
| `concurrency` | `int` | `16` |  |
| `meter` | [UsageMeter](../../usage/UsageMeter.md) \| None | `None` |  |
| `estimated_cost` | `float \| None` | `None` |  |
| `allow_mismatch` | `bool` | `False` |  |
| `gen_config` | `dict \| None` | `None` |  |
| `invocation` | `Sequence[str] \| None` | `None` |  |
| `artifacts` | `dict \| None` | `None` |  |

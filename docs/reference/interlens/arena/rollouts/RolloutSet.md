# `RolloutSet`

A directory of episodes plus the manifest that says what produced them.

```python
RolloutSet(
	root: str | Path,
	*,
	config: dict | None = None,
	model: str | None = None,
	scenario: str | None = None,
	create: bool = True,
)
```

Defined in [`interlens.arena.rollouts`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L169-L506)

Layout:

```python
<root>/rollout_manifest.json   # schema, model, scenario, config + fingerprint, keys, invocations
<root>/episodes/               # an EpisodeStore tree (one JSON per episode)
<root>/instances/              # the exact Instance JSONs the episodes were played on
```

Open-or-create: constructing on an existing root reads its manifest; on a fresh root it writes one from
`config`/`model`/`scenario`. It is safe to construct concurrently from several processes only in the
sense that :class:`EpisodeStore` writes are atomic — the manifest is last-writer-wins, so drive one set from
one process.

Parameters
----------
root : str | Path
        The set's directory. Created (with parents) if missing.
config : dict | None
        The protocol config for this set. Required when creating; on an existing set it is CHECKED against the
        manifest's fingerprint (see :meth:`append`) and otherwise ignored — the manifest is the authority.
model : str | None
        Model identity recorded in the manifest (`"anthropic:claude-opus-5"`, a local HF id, `"policy:..."`).
        Recorded only; it should also appear inside `config` if it defines the condition.
scenario : str | None
        Scenario name recorded in the manifest.
create : bool
        Create the directory and manifest when absent (default). `False` raises on a missing set, which is
        what an analysis-side reader wants.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `root` | `str \| Path` | *required* |  |
| `config` | `dict \| None` | `None` |  |
| `model` | `str \| None` | `None` |  |
| `scenario` | `str \| None` | `None` |  |
| `create` | `bool` | `True` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `fingerprint` | `str` | The manifest's config fingerprint — the protocol identity every append is held to. |
| `instances_dir` |  |  |
| `manifest` | `dict` |  |
| `manifest_path` |  |  |
| `root` |  |  |
| `store` |  |  |

## Methods {#methods}

## `append` {#append}

```python
append(
	self,
	episodes: Sequence[Episode | dict],
	*,
	config: dict | None = None,
	allow_mismatch: bool = False,
	invocation: Sequence[str] | None = None,
	artifacts: dict | None = None,
) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L267-L346)

Add `episodes` to the set, deduped on :data:`RolloutKey`, and update the manifest.

Episodes already written into this set's own store (the normal case — :func:`rollout` points the pool's
store here) are recognized by `episode_id` and not rewritten; episodes from elsewhere (merging chunk
directories, importing a foreign run) are saved in. Either way an episode whose key is already present
is SKIPPED, never duplicated.

`config` is checked against the manifest's fingerprint first: any difference raises
:class:`RolloutConfigMismatch` and NOTHING is written, because a set that quietly mixes protocols is
worse than a failed append. `allow_mismatch=True` proceeds, but stamps every accepted episode's
`cell_cfg["rollout_config_mismatch"]` with the offending fingerprint and records the divergence (both
fingerprints and the differing keys) in `manifest["mismatched_appends"]`.

Returns `{"added": int, "skipped": int, "keys": [(instance_id, seed, arm, episode_id), ...],
"mismatch": bool}` — the accepted rows, in the shape the manifest records them.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episodes` | Sequence[[Episode](../schema/Episode.md) \| dict] | *required* |  |
| `config` | `dict \| None` | `None` |  |
| `allow_mismatch` | `bool` | `False` |  |
| `invocation` | `Sequence[str] \| None` | `None` |  |
| `artifacts` | `dict \| None` | `None` |  |

## `episodes` {#episodes}

```python
episodes(self) -> list[dict]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L231-L233)

Every stored episode record, as raw dicts (sorted by store path).

## `keys` {#keys}

```python
keys(self) -> set[RolloutKey]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L235-L239)

The :data:`RolloutKey` of every episode ON DISK.

Read from the episodes themselves rather than the
manifest, so a set whose manifest is stale (a crash between the store write and the manifest write)
still resumes correctly — the episodes are the ground truth.

## `load_instances` {#load_instances}

```python
load_instances(self) -> list[Instance]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L247-L256)

The instances this set was played on, as saved by :meth:`save_instances` (`[]` if none yet).

A set's bank is its own record. Reuse it rather than regenerating: :func:`~interlens.arena.schema.new_id`
is uuid-based, not seed-derived, so re-generating "the same" instances mints NEW `instance_id`\ s and
every stored key stops matching — the set would silently replay everything it already has.

## `missing` {#missing}

```python
missing(
	self,
	instances: Sequence[Instance],
	seeds: Sequence[int],
	arms: Sequence[str],
) -> list[RolloutKey]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L241-L245)

The planned keys of `instances x seeds x arms` that are not yet on disk — what a resume must run.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instances` | Sequence[[Instance](../schema/Instance.md)] | *required* |  |
| `seeds` | `Sequence[int]` | *required* |  |
| `arms` | `Sequence[str]` | *required* |  |

## `record_artifacts` {#record_artifacts}

```python
record_artifacts(self, **links: str = {}) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L348-L351)

Record artifact locations on the manifest (`transcripts=...`, `hf_dataset=...`, `report=...`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `links` | `str` | `{}` |  |

## `save_instances` {#save_instances}

```python
save_instances(self, instances: Iterable[Instance]) -> Path
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L258-L264)

Persist the exact instances played, one JSON each, so analysis can resolve `instance_id` -> game.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `instances` | Iterable[[Instance](../schema/Instance.md)] | *required* |  |

## `summary` {#summary}

```python
summary(self, *, placeholder_budget: float = PLACEHOLDER_BUDGET) -> dict
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L359-L464)

A HEALTH summary of the set, computed from the stored episode records alone.

Deliberately minimal and scenario-agnostic — counts, `status` breakdown, arm/model breakdown, the
fraction of closed/successful episodes, the mean of `outcome['primary']`, token/dollar usage, and
TWO independent contamination gates. Rich, protocol-defined baskets (normalized surplus, among-deals
statistics, clustered intervals) belong to the experiment's analyzers, which own those definitions;
this exists to answer "did the rollouts run, and is any of this text real?" before anyone analyses it.

The two gates are separate because each is blind to the other's failure:

- **fabrication** (:func:`~interlens.arena.engine.gen_failures`) — turns no model ever produced.
- **placeholder budget** (:func:`~interlens.arena.engine.turn_signatures`) — turns that SAID nothing.
  A model can burn its entire per-turn budget inside an unterminated `<think>` block, and the
  placeholder it gets substituted is a non-empty string that parses into a well-formed no-op. So
  `fabrication` reads a correct 0.000, `parse_ok` reads 1.000, an empty-content check reads 0.0%,
  and a quarter of the turns are silent anyway (measured 24.4% on a thinking-on Qwen3-32B cell).

`placeholder_rate_by_round` is reported because this failure is **late-episode by construction** —
context grows with the transcript, so the budget is exhausted in later rounds (measured 5.8% at round 1
rising to ~35% by round 2-4). A short smoke run, or a preview of an episode's opening turns, reads near
0% and under-detects it; :meth:`summary_text` therefore prints the worst round alongside the pooled rate.

Parameters
----------
placeholder_budget : float
        Fraction of turns that may be placeholders before `placeholder_budget_exceeded` is set (default
        :data:`PLACEHOLDER_BUDGET`). It is a flag, never a raise: the episodes are real evidence, and the
        documented response to a silent cell is to record the rate — and to treat it as a NEW protocol,
        since raising the cap changes the protocol string and breaks pairing with the old cells.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `placeholder_budget` | `float` | `PLACEHOLDER_BUDGET` |  |

## `summary_text` {#summary_text}

```python
summary_text(self, *, placeholder_budget: float = PLACEHOLDER_BUDGET) -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/rollouts.py#L466-L506)

One-line-per-fact rendering of :meth:`summary` for a driver script's stdout.

Both contamination gates always print, including when they are clean — a gate you only see when it
fires is a gate nobody knows to look for.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `placeholder_budget` | `float` | `PLACEHOLDER_BUDGET` |  |

# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Directory-backed **rollout sets**: run more episodes into the same place, safely, and resume.

The arena already has every piece of a rollout: a ``Scenario`` (the game), a ``Participant`` (who plays), an
``EpisodePool``/``BatchedEpisodePool`` (drives them), and an ``EpisodeStore`` (persists them). What it did not
have is the bookkeeping *around* a set of episodes — the part every experiment re-derives: which
(instance, seed, arm) triples are already on disk, whether it is safe to add more to this directory, and what
the set looks like so far. This module is that layer and nothing else. It composes; it re-implements nothing.

Library vs experiment — the boundary this module commits to
-----------------------------------------------------------
**In the library** (here): the identity and safety of a *set of episodes on disk*. Open-or-create a directory,
a manifest describing what produced it (model, scenario, config fingerprint, seeds completed, invocations,
artifact links), a dedupe/resume key, and an append that REFUSES to mix protocols. Also a deliberately minimal
:meth:`RolloutSet.summary` — counts, statuses, success rate, mean primary, the generation-failure audit, spend.
All of it is scenario-agnostic: it reads only fields the arena's own :mod:`~interlens.arena.schema` defines.

**In the experiment**: everything protocol-specific. Which scaffold, framing, oracle stack, instance bank, seat
lineup and arms constitute a cell; how a model id resolves to a participant; and every rich metric (per-party
normalized surplus, among-deals baskets, instance-clustered intervals, paired tables). Those live with the
analyzers that own their definitions — ``summary()`` here is a health check, not a results table, and it stays
that way so the library never grows a dependency on one experiment's notion of a good deal.

Why the append refusal is loud
------------------------------
A rollout set is evidence. Appending episodes played under a *different* protocol into a directory whose
manifest claims one protocol produces a silently mixed corpus that every downstream analysis will average over
without ever knowing. So :meth:`RolloutSet.append` compares a fingerprint of the caller's config against the
manifest's and raises :class:`RolloutConfigMismatch` on any difference. ``allow_mismatch=True`` is the explicit
escape hatch, and it is not a silencer: the mismatched episodes are STAMPED in their own ``cell_cfg`` and the
divergence is recorded in the manifest, so the contamination stays legible forever.

Worked example::

    from interlens.arena.rollouts import rollout
    from interlens.arena.negotiation import games
    from interlens.arena.negotiation.sheets import GameSpec
    from interlens.arena.scenarios.scorable import ScorableNegotiation
    from interlens.arena.table import rational_table

    instances = [games.build_preset_instance("scorable", level=0, seed=s,
                                             instance_name=ScorableNegotiation.name)[0]
                 for s in range(3)]

    def seat_lineup(instance, arm, seed):                      # fresh policy seats per episode
        game = GameSpec.from_json(instance.payload)
        return rational_table(game, ["boulware", "conceder", "bayes-rational"], deadline=game.rounds)

    cfg = {"model": "policy:bayes-rational", "scaffold": "canonical", "info": "full"}
    rs = rollout(scenario=ScorableNegotiation(), instances=instances, participant=seat_lineup,
                 seeds=[0, 1], arms=["moves_chat"], out="runs/pilot", config=cfg)
    print(rs.summary_text())
    # RolloutSet runs/pilot
    #   model=policy:bayes-rational scenario=scorable_negotiation cfg=8f2c1a09b4de
    #   episodes: 6 (6 distinct keys) statuses={'done': 6}
    #   arms: {'moves_chat': 6}
    #   success: 4/6 = 0.667
    #   mean primary: 0.7143 over 6 scored episodes
    #   usage: 0 in / 0 out tokens, $0.00
    #   fabricated turns: 0 (in 0 episodes)

    # later — two more seeds into the SAME set; the first two are skipped, not replayed
    rollout(scenario=ScorableNegotiation(), instances=instances, participant=seat_lineup,
            seeds=[0, 1, 2, 3], arms=["moves_chat"], out="runs/pilot", config=cfg)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from ..usage import UsageMeter
from .engine import BatchedEpisodePool, EpisodePool, gen_failures
from .scenario import Scenario
from .schema import Episode, EpisodeStore, Instance

__all__ = ["MANIFEST_NAME", "RolloutConfigMismatch", "RolloutKey", "RolloutSet",
           "ParticipantFactory", "ScenarioFactory", "config_fingerprint", "rollout"]

# The set's manifest filename. Deliberately NOT ``manifest.json``: an experiment's own run manifests already use
# that name, and a rollout set must be able to sit in the same directory as one without either clobbering it.
MANIFEST_NAME = "rollout_manifest.json"

MANIFEST_SCHEMA = "interlens-rollout-set-v1"

#: One episode's identity within a set: ``(instance_id, seed, arm)``. This is the resume/dedupe key — two
#: episodes sharing it are the same planned rollout, so the second is skipped. It deliberately does NOT include
#: the cell tag: a different cell is a different *condition*, which belongs in its own set (and would trip the
#: config-fingerprint refusal anyway).
RolloutKey = tuple[str, int, str]

#: ``(instance, arm, seed) -> Participant``. Pass a factory when the seat lineup must be built fresh per episode
#: (policy seats hold mutable per-episode belief/offer state and would race if shared) or depends on the game.
ParticipantFactory = Callable[[Instance, str, int], Any]

#: ``(instance) -> Scenario``. Pass a factory when the scenario is instance-dependent (e.g. an oracle stack
#: constructed against that game); pass a plain ``Scenario`` when one object serves every episode.
ScenarioFactory = Callable[[Instance], Scenario]


class RolloutConfigMismatch(RuntimeError):
	"""An append's config fingerprint disagrees with the set's manifest — refused rather than silently mixed."""


def config_fingerprint(config: dict | None) -> str:
	"""Stable SHA256 over ``config``, canonicalized (sorted keys, compact separators, non-JSON values repr'd).

	This is the set's protocol identity. Anything that changes what an episode *means* belongs in ``config``
	(scaffold, framing, info condition, arms, oracle stack, bank hash, model id); anything that merely changes
	how it was scheduled (concurrency, chunking, artifact root) must NOT, or a resumed run refuses itself."""
	return hashlib.sha256(
		json.dumps(config or {}, sort_keys=True, separators=(",", ":"), default=repr).encode()
	).hexdigest()


def _key(ep: dict) -> RolloutKey:
	"""The :data:`RolloutKey` of a stored episode record."""
	return (ep.get("instance_id", ""), int(ep.get("seed", 0)), ep.get("arm", ""))


class RolloutSet:
	"""A directory of episodes plus the manifest that says what produced them.

	Layout::

	    <root>/rollout_manifest.json   # schema, model, scenario, config + fingerprint, keys, invocations
	    <root>/episodes/               # an EpisodeStore tree (one JSON per episode)
	    <root>/instances/              # the exact Instance JSONs the episodes were played on

	Open-or-create: constructing on an existing root reads its manifest; on a fresh root it writes one from
	``config``/``model``/``scenario``. It is safe to construct concurrently from several processes only in the
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
		Model identity recorded in the manifest (``"anthropic:claude-opus-5"``, a local HF id, ``"policy:..."``).
		Recorded only; it should also appear inside ``config`` if it defines the condition.
	scenario : str | None
		Scenario name recorded in the manifest.
	create : bool
		Create the directory and manifest when absent (default). ``False`` raises on a missing set, which is
		what an analysis-side reader wants."""

	def __init__(self, root: str | Path, *, config: dict | None = None, model: str | None = None,
	             scenario: str | None = None, create: bool = True):
		self.root = Path(root)
		self.manifest_path = self.root / MANIFEST_NAME
		if self.manifest_path.exists():
			self.manifest: dict = json.loads(self.manifest_path.read_text())
		elif not create:
			raise FileNotFoundError(f"no rollout set at {self.root} (no {MANIFEST_NAME})")
		else:
			self.root.mkdir(parents=True, exist_ok=True)
			self.manifest = {
				"schema": MANIFEST_SCHEMA,
				"created_at": time.time(),
				"model": model,
				"scenario": scenario,
				"config": dict(config or {}),
				"config_fingerprint": config_fingerprint(config),
				"keys": [],              # every (instance_id, seed, arm) accepted, in append order
				"invocations": [],       # one record per append: argv, when, how many added/skipped
				"artifacts": {},         # free-form links (HF urls, transcript dirs, analysis outputs)
				"mismatched_appends": [],
			}
			self._write()
		self.store = EpisodeStore(self.root / "episodes")
		self.instances_dir = self.root / "instances"

	# ------------------------------------------------------------------ reading --
	@property
	def fingerprint(self) -> str:
		"""The manifest's config fingerprint — the protocol identity every append is held to."""
		return self.manifest["config_fingerprint"]

	def episodes(self) -> list[dict]:
		"""Every stored episode record, as raw dicts (sorted by store path)."""
		return self.store.load_all()

	def keys(self) -> set[RolloutKey]:
		"""The :data:`RolloutKey` of every episode ON DISK. Read from the episodes themselves rather than the
		manifest, so a set whose manifest is stale (a crash between the store write and the manifest write)
		still resumes correctly — the episodes are the ground truth."""
		return {_key(ep) for ep in self.episodes()}

	def missing(self, instances: Sequence[Instance], seeds: Sequence[int], arms: Sequence[str]) -> list[RolloutKey]:
		"""The planned keys of ``instances x seeds x arms`` that are not yet on disk — what a resume must run."""
		have = self.keys()
		return [k for inst in instances for arm in arms for seed in seeds
		        if (k := (inst.instance_id, int(seed), arm)) not in have]

	def load_instances(self) -> list[Instance]:
		"""The instances this set was played on, as saved by :meth:`save_instances` (``[]`` if none yet).

		A set's bank is its own record. Reuse it rather than regenerating: :func:`~interlens.arena.schema.new_id`
		is uuid-based, not seed-derived, so re-generating "the same" instances mints NEW ``instance_id``\\ s and
		every stored key stops matching — the set would silently replay everything it already has."""
		if not self.instances_dir.is_dir():
			return []
		return [Instance.from_json(json.loads(f.read_text()))
		        for f in sorted(self.instances_dir.glob("*.json"))]

	def save_instances(self, instances: Iterable[Instance]) -> Path:
		"""Persist the exact instances played, one JSON each, so analysis can resolve ``instance_id`` -> game."""
		self.instances_dir.mkdir(parents=True, exist_ok=True)
		for inst in instances:
			(self.instances_dir / f"{inst.instance_id}.json").write_text(
				json.dumps(inst.to_json(), ensure_ascii=False))
		return self.instances_dir

	# ------------------------------------------------------------------ writing --
	def append(self, episodes: Sequence[Episode | dict], *, config: dict | None = None,
	           allow_mismatch: bool = False, invocation: Sequence[str] | None = None,
	           artifacts: dict | None = None) -> dict:
		"""Add ``episodes`` to the set, deduped on :data:`RolloutKey`, and update the manifest.

		Episodes already written into this set's own store (the normal case — :func:`rollout` points the pool's
		store here) are recognized by ``episode_id`` and not rewritten; episodes from elsewhere (merging chunk
		directories, importing a foreign run) are saved in. Either way an episode whose key is already present
		is SKIPPED, never duplicated.

		``config`` is checked against the manifest's fingerprint first: any difference raises
		:class:`RolloutConfigMismatch` and NOTHING is written, because a set that quietly mixes protocols is
		worse than a failed append. ``allow_mismatch=True`` proceeds, but stamps every accepted episode's
		``cell_cfg["rollout_config_mismatch"]`` with the offending fingerprint and records the divergence (both
		fingerprints and the differing keys) in ``manifest["mismatched_appends"]``.

		Returns ``{"added": int, "skipped": int, "keys": [(instance_id, seed, arm, episode_id), ...],
		"mismatch": bool}`` — the accepted rows, in the shape the manifest records them."""
		mismatch = False
		if config is not None and config_fingerprint(config) != self.fingerprint:
			differing = sorted(set(config) | set(self.manifest["config"]))
			differing = [k for k in differing if config.get(k) != self.manifest["config"].get(k)]
			if not allow_mismatch:
				raise RolloutConfigMismatch(
					f"append refused: config fingerprint {config_fingerprint(config)[:12]} != set "
					f"{self.fingerprint[:12]} (differing keys: {differing}). This set was built under a "
					f"different protocol; append to a NEW set, or pass allow_mismatch=True to stamp these "
					f"episodes as mixed.")
			mismatch = True
			self.manifest["mismatched_appends"].append(
				{"at": time.time(), "set_fingerprint": self.fingerprint,
				 "appended_fingerprint": config_fingerprint(config), "differing_keys": differing,
				 "appended_config": dict(config)})

		# Two facts decide each record, and both are needed. ``on_disk`` (key -> episode_ids present in the
		# store) catches a genuine duplicate: a second episode of a key someone already played. ``registered``
		# (episode_ids the manifest has already accounted for) makes the call idempotent — :func:`rollout`
		# points the pool's store AT this set, so the episodes handed here are already on disk under their own
		# ids, and without the id check every one of them would look like a duplicate of itself.
		on_disk: dict[RolloutKey, set[str]] = {}
		for stored_ep in self.episodes():
			on_disk.setdefault(_key(stored_ep), set()).add(stored_ep.get("episode_id", ""))
		registered = {row[3] for row in self.manifest["keys"] if len(row) > 3}
		added: list[tuple] = []          # (*RolloutKey, episode_id) — the manifest row shape
		skipped = 0
		for ep in episodes:
			record = ep.to_json() if isinstance(ep, Episode) else ep
			key, episode_id = _key(record), record.get("episode_id", "")
			if episode_id in registered or (key in on_disk and episode_id not in on_disk[key]):
				skipped += 1
				continue
			if mismatch:
				stamp = {"rollout_config_mismatch": config_fingerprint(config)}
				record = {**record, "cell_cfg": {**(record.get("cell_cfg") or {}), **stamp}}
				if isinstance(ep, Episode):
					ep.cell_cfg = record["cell_cfg"]
			stored = _StoredRecord(record)
			if mismatch or not self.store.path(stored).exists():
				self.store.save(stored)
			on_disk.setdefault(key, set()).add(episode_id)
			registered.add(episode_id)
			added.append((*key, episode_id))
		self.manifest["keys"].extend([list(k) for k in added])
		self.manifest["invocations"].append(
			{"at": time.time(), "argv": list(invocation) if invocation is not None else list(sys.argv),
			 "added": len(added), "skipped": skipped, "mismatch": mismatch})
		if artifacts:
			self.manifest["artifacts"].update(artifacts)
		self._write()
		return {"added": len(added), "skipped": skipped, "keys": added, "mismatch": mismatch}

	def record_artifacts(self, **links: str) -> None:
		"""Record artifact locations on the manifest (``transcripts=...``, ``hf_dataset=...``, ``report=...``)."""
		self.manifest["artifacts"].update(links)
		self._write()

	def _write(self) -> None:
		tmp = self.manifest_path.with_suffix(".tmp")
		tmp.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=1))
		tmp.replace(self.manifest_path)

	# ------------------------------------------------------------------ summary --
	def summary(self) -> dict:
		"""A HEALTH summary of the set, computed from the stored episode records alone.

		Deliberately minimal and scenario-agnostic — counts, ``status`` breakdown, arm/model breakdown, the
		fraction of closed/successful episodes, the mean of ``outcome['primary']``, the engine-fabrication audit
		(:func:`~interlens.arena.engine.gen_failures`, which also screens pre-stamp episodes), and token/dollar
		usage. Rich, protocol-defined baskets (normalized surplus, among-deals statistics, clustered intervals)
		belong to the experiment's analyzers, which own those definitions; this exists to answer "did the
		rollouts run, and is any of this text not model behaviour?" before anyone analyses anything."""
		eps = self.episodes()
		statuses: dict[str, int] = {}
		by_arm: dict[str, int] = {}
		by_model: dict[str, int] = {}
		primaries: list[float] = []
		n_success = n_fab_turns = n_fab_eps = 0
		tokens_in = tokens_out = 0
		usd = 0.0
		for ep in eps:
			statuses[ep.get("status", "missing")] = statuses.get(ep.get("status", "missing"), 0) + 1
			by_arm[ep.get("arm", "?")] = by_arm.get(ep.get("arm", "?"), 0) + 1
			by_model[ep.get("model", "?")] = by_model.get(ep.get("model", "?"), 0) + 1
			outcome = ep.get("outcome") or {}
			n_success += bool(outcome.get("success"))
			if isinstance(outcome.get("primary"), (int, float)):
				primaries.append(float(outcome["primary"]))
			fails = gen_failures(ep)
			n_fab_turns += len(fails)
			n_fab_eps += bool(fails)
			tokens_in += ep.get("tokens_in", 0)
			tokens_out += ep.get("tokens_out", 0)
			usd += ep.get("cost_usd", 0.0)
		return {
			"root": str(self.root),
			"model": self.manifest.get("model"),
			"scenario": self.manifest.get("scenario"),
			"config_fingerprint": self.fingerprint,
			"n_episodes": len(eps),
			"n_keys": len({_key(ep) for ep in eps}),
			"status_counts": dict(sorted(statuses.items())),
			"by_arm": dict(sorted(by_arm.items())),
			"by_model": dict(sorted(by_model.items())),
			"success_rate": (n_success / len(eps)) if eps else None,
			"n_success": n_success,
			"mean_primary": (sum(primaries) / len(primaries)) if primaries else None,
			"n_scored": len(primaries),
			# Any nonzero fabrication means part of this set is text no model produced. It is surfaced here, not
			# only in the run log, because a set is appended to and read long after the run that made it.
			"fabricated_turns": n_fab_turns,
			"episodes_with_fabricated_turns": n_fab_eps,
			"tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": round(usd, 6),
			"n_mismatched_appends": len(self.manifest.get("mismatched_appends", [])),
		}

	def summary_text(self) -> str:
		"""One-line-per-fact rendering of :meth:`summary` for a driver script's stdout."""
		s = self.summary()
		lines = [f"RolloutSet {s['root']}",
		         f"  model={s['model']} scenario={s['scenario']} cfg={s['config_fingerprint'][:12]}",
		         f"  episodes: {s['n_episodes']} ({s['n_keys']} distinct keys) statuses={s['status_counts']}",
		         f"  arms: {s['by_arm']}"]
		if s["success_rate"] is not None:
			lines.append(f"  success: {s['n_success']}/{s['n_episodes']} = {s['success_rate']:.3f}")
		if s["mean_primary"] is not None:
			lines.append(f"  mean primary: {s['mean_primary']:.4f} over {s['n_scored']} scored episodes")
		lines.append(f"  usage: {s['tokens_in']:,} in / {s['tokens_out']:,} out tokens, ${s['cost_usd']:.2f}")
		flag = "" if not s["fabricated_turns"] else "  <-- NOT model behaviour; exclude before analysing"
		lines.append(f"  fabricated turns: {s['fabricated_turns']} "
		             f"(in {s['episodes_with_fabricated_turns']} episodes){flag}")
		if s["n_mismatched_appends"]:
			lines.append(f"  MIXED: {s['n_mismatched_appends']} append(s) accepted under allow_mismatch")
		return "\n".join(lines)


class _StoredRecord:
	"""A raw episode dict wearing the duck type :class:`EpisodeStore` saves: attribute access for the layout
	fields (``model``/``cell``/``arm``/``level``/``episode_id``) and a ``to_json`` that returns the record
	VERBATIM. Re-parsing into an :class:`Episode` would silently drop any field this schema version does not
	know about, which is exactly wrong when importing episodes written by another run."""

	def __init__(self, record: dict):
		self._record = record

	def __getattr__(self, name: str):
		return self._record.get(name)

	def to_json(self) -> dict:
		return self._record


def rollout(*, scenario: Scenario | ScenarioFactory, instances: Sequence[Instance], participant,
            out: str | Path, model: str | None = None, arms: Sequence[str] = ("team",),
            seeds: Sequence[int] = (0,), cfg: dict | None = None, config: dict | None = None,
            engine: str = "auto", concurrency: int = 16, meter: UsageMeter | None = None,
            estimated_cost: float | None = None, allow_mismatch: bool = False,
            gen_config: dict | None = None, invocation: Sequence[str] | None = None,
            artifacts: dict | None = None) -> RolloutSet:
	"""Run ``instances x seeds x arms`` into the rollout set at ``out`` (creating or resuming it) and return it.

	Swapping the model is one argument (``participant``), swapping the game is one argument (``scenario``);
	everything else is bookkeeping this function does for you: skip the (instance, seed, arm) triples already on
	disk, point the pool's store at the set so episodes persist as they finish, then append + update the manifest.

	Parameters
	----------
	scenario : Scenario | ScenarioFactory
		The game. A plain ``Scenario`` is shared by every episode; a callable ``(instance) -> Scenario`` is
		called per instance (for a per-game oracle stack).
	instances : Sequence[Instance]
		The bank. Saved into ``<out>/instances/`` so analysis can resolve every ``instance_id``.
	participant : Participant | ParticipantFactory
		Who plays. A participant object is SHARED across episodes (correct for stateless model weights, and the
		precondition for batched co-stepping); a callable ``(instance, arm, seed) -> Participant`` is called per
		episode (required for policy seats, whose belief/offer state is per-episode mutable).
	out : str | Path
		The rollout-set directory. Existing sets are resumed; the config fingerprint must match.
	model : str | None
		Model identity for the manifest. Defaults to ``config["model"]`` when present.
	arms, seeds : Sequence
		The protocol arms and episode seeds; one episode per (instance, arm, seed).
	cfg : dict | None
		The per-episode situational config handed to the scenario and stored on each episode as ``cell_cfg``.
	config : dict | None
		The set's protocol identity (see :func:`config_fingerprint`). Pass everything that defines the condition;
		a resumed set refuses to run if it disagrees.
	engine : str
		``"auto"`` (default) uses :class:`BatchedEpisodePool` co-stepping when ``participant`` is a single shared
		object exposing ``generate_batch`` (a local model — the 5-20x path) and the async
		:class:`EpisodePool` otherwise; ``"batched"`` / ``"async"`` force one. A per-episode factory can never be
		batched, since the whole point of co-stepping is one shared model.
	concurrency : int
		Max concurrent episodes for the async pool (API width is the client's own cap). Ignored when batched.
	meter : UsageMeter | None
		Shared spend ledger for hosted-API seats; with ``estimated_cost`` the pool reserves before each episode,
		so a dollar cap stops the run instead of merely describing it afterwards.
	allow_mismatch : bool
		Forwarded to :meth:`RolloutSet.append` — see its docstring; leaves a permanent stamp.
	gen_config : dict | None
		Provider/sampling provenance recorded on every episode.
	invocation : Sequence[str] | None
		The command line to record (defaults to ``sys.argv``).
	artifacts : dict | None
		Artifact links to record on the manifest (transcript dir, HF dataset URL, ...).

	Raises
	------
	RolloutConfigMismatch
		If ``out`` exists under a different protocol config and ``allow_mismatch`` is False. Raised BEFORE any
		episode runs, so a mis-pointed resume costs nothing."""
	config = dict(config or {})
	rs = RolloutSet(out, config=config, model=model or config.get("model"),
	                scenario=(scenario.name if isinstance(scenario, Scenario) else None))
	if config_fingerprint(config) != rs.fingerprint and not allow_mismatch:
		differing = [k for k in sorted(set(config) | set(rs.manifest["config"]))
		             if config.get(k) != rs.manifest["config"].get(k)]
		raise RolloutConfigMismatch(
			f"{rs.root} was built under a different protocol (differing keys: {differing}); use a new --out or "
			f"pass allow_mismatch=True")
	rs.save_instances(instances)

	# Resume is unconditional and needs no flag: a key already on disk is a rollout already paid for. To
	# re-play one, delete its episode — then it is missing, and this runs it.
	todo = rs.missing(instances, seeds, arms)
	by_id = {inst.instance_id: inst for inst in instances}
	jobs = []
	for instance_id, seed, arm in todo:
		inst = by_id[instance_id]
		jobs.append({"scenario": scenario(inst) if callable(scenario) else scenario,
		             "instance": inst, "arm": arm, "seed": seed, "cfg": dict(cfg) if cfg else None,
		             "gen_config": gen_config,
		             "participant": participant(inst, arm, seed) if callable(participant) else participant,
		             "estimated_cost": estimated_cost})
	if not jobs:
		return rs
	if not rs.manifest.get("scenario"):
		# a scenario FACTORY has no name until it has built one; take it from the first job rather than
		# leaving the manifest's scenario field null
		rs.manifest["scenario"] = getattr(jobs[0]["scenario"], "name", None)

	batched = engine == "batched" or (engine == "auto" and not callable(participant)
	                                  and hasattr(participant, "generate_batch"))
	if engine not in ("auto", "batched", "async"):
		raise ValueError(f"engine must be 'auto', 'batched' or 'async', got {engine!r}")
	if batched:
		if callable(participant):
			raise ValueError("engine='batched' needs ONE shared participant object; a per-episode factory "
			                 "cannot be co-stepped (batching exists to share a single local model)")
		pool = BatchedEpisodePool(rs.store)
		episodes = pool.run_pool(jobs)
		rs.manifest["fabrication"] = pool.fabrication_report()
	else:
		episodes = asyncio.run(EpisodePool(rs.store, meter=meter, max_concurrent=concurrency).run_pool(jobs))
	if meter is not None:
		rs.manifest["usage"] = meter.snapshot()
	rs.append(episodes, config=config, allow_mismatch=allow_mismatch, invocation=invocation,
	          artifacts=artifacts)
	return rs

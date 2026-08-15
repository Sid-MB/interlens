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

"""The arena's record schema: one JSON shape for every episode.

Every episode — regardless of scenario, arm, cell, or model — serializes to one JSON record with the same
top-level fields, so datasets and analyses join cleanly across runs. ``Instance`` is a generated, solver-verified
problem (with its exact ceiling/floor and hidden solution); ``Episode`` is one play-through of an instance;
``EpisodeStore`` is the crash-safe on-disk layout. The schema is shared with the arena experiments that
produced the public transcripts dataset, so stored episodes from those runs re-score under this package
(see ``replay.py``).
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Episode record schema. v1.1 changed one stored shape: an oracle verdict's ``action_values`` in
# ``round_checkpoints`` is a ``{action_key: value}`` OBJECT rather than a ``[{action, value}]`` list (see
# ``OracleVerdict.to_json``). Reading is backward compatible — ``OracleVerdict.from_json`` accepts both — so
# v1.0 episodes still load and replay; the bump records which shape a file was WRITTEN with.
#
# v1.2 added ``TurnRecord.gen_failed`` / ``gen_failure``: an explicit stamp for a turn whose text the ENGINE
# fabricated after generation failed, rather than leaving that only inferable from a fragile value signature.
# The version is the reliable way to ask "can I trust ``gen_failed == False`` on this file?" — on a v1.1-or-older
# episode the field is simply absent, which is not the same as "generation succeeded", so screen those with
# ``engine.gen_failures`` (it falls back to the legacy signature).
SCHEMA_VERSION = "v1.2"

# Neutral seat names, assigned in order (a scenario with n seats uses the first n).
PERSONAS = ["Avery", "Blake", "Casey", "Devon", "Ember", "Flynn", "Greer", "Hollis"]


def new_id(prefix: str) -> str:
	"""A fresh episode/instance id. Random (uuid4-based), deliberately NOT seed-derived: two runs of the same
	seed produce identical payloads but distinct ids."""
	return f"{prefix}-{uuid.uuid4().hex[:10]}"


@dataclass
class Instance:
	"""One generated problem instance, solver-verified at generation time.

	``ceiling`` is the best achievable primary score (computed exactly by the generator's solver), ``floor`` a
	reference floor policy's score, and ``solution`` the exact optimum — never shown to models, used for
	scoring and audits."""

	instance_id: str
	scenario: str
	level: int              # index into the scenario's difficulty ladder (0 = base)
	seed: int
	payload: dict           # scenario-specific: score sheets / shards / dynamics
	ceiling: float
	floor: float
	solution: dict

	def to_json(self) -> dict:
		return dataclasses.asdict(self)

	@staticmethod
	def from_json(d: dict) -> "Instance":
		d = dict(d)
		# the arena experiments' stored instances predate the env->scenario rename
		if "env" in d and "scenario" not in d:
			d["scenario"] = d.pop("env")
		return Instance(**d)


@dataclass
class SeatRequest:
	"""One pending generation: a seat that must speak now, with the exact view its model is conditioned on."""

	episode_id: str
	seat: str               # persona name
	view: list[dict]        # role/content messages (system first), family-agnostic
	phase: str              # e.g. "turn", "final_proposal", "final_answer", "provisional"
	round: int
	max_tokens: int = 2048  # per-turn output cap; a smaller default silently starves thinking models
	meta: dict = field(default_factory=dict)   # scenario-private routing info
	provisional: bool = False                  # forked: the response never enters state or any transcript


@dataclass
class TurnRecord:
	idx: int
	round: int
	phase: str
	seat: str
	content: str            # think-stripped visible content
	parsed_action: Any      # the turn's parsed action — a SCENARIO-DEFINED structure (raw fenced JSON, an
	                        # Action.to_json() dict, or a scenario's normalized action record); typed Any so each
	                        # scenario owns its shape. parse_ok records whether it was well-formed for that scenario.
	parse_ok: bool
	n_tokens_out: int = 0
	n_tokens_in: int = 0
	stop_reason: str | None = None
	cap: int = 0            # max_tokens this turn was generated under (0 = unrecorded)
	raw: str | None = None  # raw completion incl. reasoning, when different from content
	# The turn's reasoning record, first-class: whatever reasoning the provider returned (Anthropic thinking
	# blocks incl. summarized ones; local <think> streams), with provenance marking completeness —
	# "none" (no reasoning produced) | "withheld_or_summarized" (produced, but the provider returned a
	# summary/redaction or nothing readable) | "full" (complete stream recorded verbatim). Flows into the
	# episode JSON via to_json() and from there into any exported dataset rows built from episodes.
	reasoning: str | None = None
	reasoning_provenance: str = "none"
	# Hidden reasoning tokens the provider billed for this turn (Anthropic
	# ``usage.output_tokens_details.thinking_tokens``; 0 when unreported or thinking was disabled). On models
	# whose reasoning text is sealed this is the ONLY per-turn evidence that thinking actually happened, so it
	# is recorded independently of `reasoning`: a turn can legitimately have reasoning_tokens > 0 and
	# reasoning=None. Also the clean on/off discriminator for a thinking-condition audit.
	reasoning_tokens: int = 0
	# The exact rendered view (list of {role, content} messages) the seat was conditioned on for this turn — the
	# ground-truth prompt, so a transcript is faithful even after prompt code drifts (reconstruction-by-replay
	# breaks the moment it does). The engine records it by default (``EpisodePool(record_views=...)`` to disable);
	# ``None`` on turns/episodes recorded before this field existed, so old episodes load unchanged.
	view: list[dict] | None = None
	# Did the ENGINE fabricate this turn's text because generation failed outright? ``True`` means no model was
	# ever successfully called for this turn: the batched driver exhausted its splits and retries and substituted
	# ``engine.EMPTY_TURN_PLACEHOLDER`` so the pool could keep moving (``gen_failure`` carries the last
	# exception's repr). Such a turn is NOT model behaviour and must be excluded from any behavioural measurement.
	#
	# This flag exists because the failure is otherwise near-invisible: the placeholder is a non-empty string that
	# parses into a well-formed no-op, so a run in which nothing was ever generated reports ``parse_ok=True`` and
	# non-empty content on every turn. It is also the ONLY way to distinguish an engine fabrication from the other
	# producer of the same placeholder — a model that genuinely returned empty text (``engine.record_turn``
	# substitutes the same string), which IS model behaviour and a completely different problem to chase.
	# ``False``/``None`` on episodes recorded before these fields existed; use ``engine.gen_failures`` to screen
	# those, since it falls back to the legacy signature.
	gen_failed: bool = False
	gen_failure: str | None = None
	# Did an API-side refusal precede this turn, and did the re-render ladder recover it? ``None`` on the
	# overwhelming majority of turns (nothing was refused). Otherwise ``arena.refusal.recovery_record``'s dict:
	# ``{"outcome": "recovered"|"terminal", "rung": <1-based rung that cleared it or None>, "attempts": [...]}``.
	# A ``recovered`` turn IS model behaviour — it conditions on the same content, re-rendered — while a
	# ``terminal`` one is a turn no model produced and is counted as silence, so the two must never be pooled.
	refusal_recovery: dict | None = None


@dataclass
class Episode:
	"""One complete play-through: turns, forked provisional checkpoints, outcome, and usage accounting."""

	episode_id: str
	scenario: str
	arm: str                # "team" | "solo" | variant tags like "team-greedy"
	model: str
	level: int
	instance_id: str
	seed: int
	seats: list[dict]       # [{name, role, ...}]
	cell: str = "base"      # sweep-cell id when the run varies situational config
	cell_cfg: dict = field(default_factory=dict)
	turns: list[TurnRecord] = field(default_factory=list)
	# The episode's per-turn oracle log: each item is an ``arena.oracles.OracleRecord.to_json()`` dict — either
	# a forked provisional probe ({round, seat, provisional_action, score, content}) or an inline oracle
	# annotation (adds oracle/chosen_value/best_value/divergence/verdict). Stored as dicts (not the dataclass)
	# so old records load unchanged; the field name stays for record compatibility.
	round_checkpoints: list[dict] = field(default_factory=list)
	outcome: dict = field(default_factory=dict)
	rounds_used: int = 0
	tokens_in: int = 0
	tokens_out: int = 0
	cost_usd: float = 0.0
	gen_config: dict = field(default_factory=dict)   # provider/model/sampling/caps provenance
	status: str = "running"     # running | done | error | budget_stopped
	error: str | None = None
	started_at: float = field(default_factory=time.time)
	ended_at: float | None = None
	schema_version: str = SCHEMA_VERSION

	def to_json(self) -> dict:
		return dataclasses.asdict(self)

	def usage(self) -> dict:
		"""This episode's usage summary: tokens in/out (total and per seat) and dollar cost."""
		by_seat: dict[str, dict] = {}
		for t in self.turns:
			s = by_seat.setdefault(t.seat, {"tokens_out": 0, "tokens_in": 0, "turns": 0})
			s["tokens_out"] += t.n_tokens_out
			s["tokens_in"] += t.n_tokens_in
			s["turns"] += 1
		return {"tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
		        "cost_usd": round(self.cost_usd, 6), "by_seat": by_seat}


class JsonRecordStore:
	"""A directory tree of JSON records, one file per record, written atomically.

	The persistence shared by every arena record store: a ``root``, an atomic ``save`` (write a sibling ``.tmp``
	then ``os.replace``, so a crash mid-write leaves the previous file intact rather than a truncated one), and a
	sorted recursive ``load_all``. Subclasses supply only what actually differs — :meth:`path` (the on-disk
	layout) and, optionally, ``indent`` (pretty-print) — so a new store is a few lines and inherits the crash
	safety instead of re-deriving it.

	Records are duck-typed: anything with a ``to_json()`` method can be saved."""

	indent: int | None = None       # None = compact (large machine-read records); an int pretty-prints

	def __init__(self, root: str | Path):
		self.root = Path(root)

	def path(self, record) -> Path:
		"""The file ``record`` is stored at, creating its parent directory. Subclasses define the layout."""
		raise NotImplementedError

	def save(self, record) -> Path:
		"""Write ``record.to_json()`` atomically to :meth:`path` and return that path."""
		p = self.path(record)
		tmp = p.with_suffix(".tmp")
		tmp.write_text(json.dumps(record.to_json(), ensure_ascii=False, indent=self.indent))
		os.replace(tmp, p)
		return p

	def load_all(self, pattern: str = "**/*.json") -> list[dict]:
		"""Every stored record under ``root`` matching ``pattern``, as raw dicts, in sorted path order."""
		return [json.loads(f.read_text()) for f in sorted(self.root.glob(pattern))]


class EpisodeStore(JsonRecordStore):
	"""Per-episode JSON persistence, written atomically on every update so a crash loses at most one turn.

	Layout: ``{root}/{scenario}/{cell}/{arm}/{model_short}/L{level}/{episode_id}.json``."""

	def path(self, ep: Episode) -> Path:
		model_short = ep.model.split("/")[-1].replace(".", "-")
		cell = ep.cell or "base"
		p = self.root / ep.scenario / cell / ep.arm / model_short / f"L{ep.level}"
		p.mkdir(parents=True, exist_ok=True)
		return p / f"{ep.episode_id}.json"

	def load_all(self, scenario: str | None = None) -> list[dict]:
		"""Every stored episode, or only those of one ``scenario`` (the top layout level)."""
		return super().load_all(f"{scenario}/**/*.json" if scenario else "**/*.json")

	def summary(self) -> str:
		"""A printable run-usage summary aggregated over every stored episode: episode counts, token totals,
		and dollar cost, broken down per (model, arm) — plus cost-per-success where outcomes carry ``success``."""
		rows: dict[tuple, dict] = {}
		for e in self.load_all():
			key = (e["model"], e["arm"])
			r = rows.setdefault(key, {"episodes": 0, "done": 0, "success": 0,
			                          "tokens_in": 0, "tokens_out": 0, "usd": 0.0})
			r["episodes"] += 1
			r["done"] += e["status"] == "done"
			r["success"] += bool((e.get("outcome") or {}).get("success"))
			r["tokens_in"] += e.get("tokens_in", 0)
			r["tokens_out"] += e.get("tokens_out", 0)
			r["usd"] += e.get("cost_usd", 0.0)
		lines = []
		for (model, arm), r in sorted(rows.items()):
			cps = f", ${r['usd'] / r['success']:.2f}/success" if r["success"] and r["usd"] else ""
			lines.append(f"  {model} [{arm}]: {r['done']}/{r['episodes']} done, {r['success']} successes, "
			             f"{r['tokens_in']:,} in / {r['tokens_out']:,} out tokens — ${r['usd']:.2f}{cps}")
		return "Episodes:\n" + "\n".join(lines) if lines else "Episodes: (none stored)"


def save_instances(instances: list[Instance], root: str | Path, name: str | None = None) -> Path:
	"""Persist an instance pool as one JSON file (``{scenario}_L{level}.json`` unless ``name`` overrides)."""
	root = Path(root)
	root.mkdir(parents=True, exist_ok=True)
	stem = name or f"{instances[0].scenario}_L{instances[0].level}"
	p = root / f"{stem}.json"
	p.write_text(json.dumps([i.to_json() for i in instances], ensure_ascii=False, indent=1))
	return p


def load_instances(root: str | Path, scenario: str, level: int | None = None,
                   name: str | None = None) -> list[Instance]:
	"""Load an instance pool saved by ``save_instances`` (or by the arena experiments — the pre-rename ``env``
	key is migrated on read)."""
	stem = name or f"{scenario}_L{level}"
	p = Path(root) / f"{stem}.json"
	return [Instance.from_json(d) for d in json.loads(p.read_text())]

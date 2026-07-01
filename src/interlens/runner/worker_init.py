# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

# Hooks run at the start of every spawned worker process. Spawned workers re-import the entry module but
# inherit NO parent runtime state, so anything resolved by name in a worker (custom tools, analyzers, config
# kinds, stop conditions, context policies) must be (re)registered here — not imperatively in the parent before
# spawn. Symptom if you get this wrong: works single-process, empty registry in the pool.
_WORKER_INIT_HOOKS: list = []


def register_worker_init(fn) -> object:
	"""Register a zero-arg callable to run once at worker startup (e.g. to populate the tool/analyzer registries)."""
	_WORKER_INIT_HOOKS.append(fn)
	return fn


def run_worker_init() -> None:
	for hook in _WORKER_INIT_HOOKS:
		hook()

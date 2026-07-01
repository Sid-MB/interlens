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

from __future__ import annotations

# name -> analyze callable. `analyze` runs *inside* the worker while models are resident, so it can sample /
# branch / read activations on the live conversation; only its serializable return value crosses back.
#
# Spawned workers inherit no parent state, so an analyzer that must run in the pool has to be resolvable *by
# name* here (registered at import time), not passed as a lambda/closure over parent locals. In-process runs
# can also pass a callable directly.
_ANALYZERS: dict[str, object] = {}


def register_analyzer(name: str, fn) -> object:
	_ANALYZERS[name] = fn
	return fn


def resolve_analyzer(analyze):
	"""Accept either a callable (in-process) or a registered name (spawn-safe) and return the callable."""
	if analyze is None or callable(analyze):
		return analyze
	if analyze in _ANALYZERS:
		return _ANALYZERS[analyze]
	raise KeyError(f"analyzer {analyze!r} not registered (have: {sorted(_ANALYZERS)})")

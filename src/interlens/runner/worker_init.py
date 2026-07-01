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

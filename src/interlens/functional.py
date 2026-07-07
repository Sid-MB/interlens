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

"""Copy-on-write functional-update support shared by ``Participant`` and ``Conversation``.

Both are dataclasses that the user builds up incrementally (``conv.turns(6).data(ds).analyzer(grade)``) and
replicates cheaply (one recipe → N per-row copies in a rollout). The `Functional` mixin gives them a single
uniform update primitive — ``obj.set(**changes) -> new obj`` — plus optional per-field *dot-modifier sugar*
(``conv.turns(6)``) that reads with no argument and returns a modified copy with one.

Why ``copy.copy`` + an explicit ``_after_set`` hook rather than ``dataclasses.replace``: a live participant
carries heavy shared state (the loaded ``_model``/``_tokenizer``) and volatile per-conversation state (KV cache,
a pending capture). We want the copy to **share** the heavy objects by reference (zero GPU cost — the whole point
of copy-on-write here) but start with **fresh** volatile state. ``copy.copy`` shallow-copies the instance dict
(so heavy refs are shared automatically) and, crucially, does NOT re-run ``__init__``/``__post_init__`` (which for
a participant would try to re-derive device from the model, and for a conversation would re-seed/re-validate),
leaving us to reset exactly the volatile fields in ``_after_set``. The result is precise control over what is
shared vs. what is reset — which ``replace`` cannot express when the sharing/reset split cuts across init and
non-init state.
"""
from __future__ import annotations

import dataclasses

# Sentinel distinguishing "read the value" (``field()``) from "set to None" (``field(None)``) on an accessor.
_UNSET = object()


class _SugarAccessor:
	"""Descriptor implementing a dot-modifier: ``obj.field`` returns a callable where ``field()`` reads the current
	value and ``field(v)`` returns a copy-on-write clone with the value changed (``obj.set(field=v)``).

	The value is stored under the private name ``_field`` (a real dataclass field); this descriptor occupies the
	public name ``field``. Because the descriptor is a bare class attribute with no type annotation, ``@dataclass``
	ignores it — only the annotated ``_field`` becomes a dataclass field. Placed on the class by
	``sugar_fields``."""

	def __init__(self, name: str):
		self.public = name
		self.storage = f"_{name}"

	def __set_name__(self, owner, name: str) -> None:
		self.public = name
		self.storage = f"_{name}"

	def __get__(self, obj, owner=None):
		if obj is None:
			return self
		storage, public = self.storage, self.public

		def accessor(value=_UNSET):
			if value is _UNSET:
				return getattr(obj, storage)
			return obj.set(**{public: value})

		return accessor


def sugar_fields(*names: str):
	"""Class decorator declaring copy-on-write dot-modifier sugar for ``names``. Each ``name`` becomes an accessor
	(``obj.name()`` reads, ``obj.name(v)`` returns a modified copy) backed by the dataclass field ``_name``. The
	public names are also accepted by ``set(**changes)``; the underscored storage names are hidden from it."""

	def decorate(cls):
		sugared = set(getattr(cls, "_SUGARED", frozenset())) | set(names)
		cls._SUGARED = frozenset(sugared)
		for name in names:
			setattr(cls, name, _SugarAccessor(name))
		return cls

	return decorate


class Functional:
	"""Mixin giving a dataclass copy-on-write updates via ``set(**changes)``.

	``set`` shallow-copies the instance (heavy refs like a loaded model are shared, not reloaded), applies the
	changes, then calls ``_after_set`` to reset volatile per-instance state on the copy. Sugared field names
	(declared via ``sugar_fields``) are accepted under their public spelling and routed to their ``_``-prefixed
	storage. Unknown fields raise ``TypeError``. The original is never mutated."""

	_SUGARED: frozenset = frozenset()

	def set(self, **changes):
		"""Return a modified shallow copy: the same object with ``changes`` applied and volatile state reset. The
		receiver is untouched (copy-on-write); heavy state (a loaded model, an API client) is shared by reference.
		Unknown field names raise ``TypeError``.

		The copy is a raw instance-dict clone (NOT ``copy.copy``), so it deliberately bypasses ``__getstate__`` —
		which exists to DROP the loaded model/client on *pickle* (spawn boundary). A ``.set()`` clone, by contrast,
		is in-process and must KEEP those shared references (that is the whole point of copy-on-write here)."""
		allowed = self._settable_names()
		new = self.__class__.__new__(self.__class__)
		new.__dict__.update(self.__dict__)
		for key, value in changes.items():
			if key not in allowed:
				raise TypeError(f"{type(self).__name__}.set() got an unexpected field {key!r}; "
				                f"settable fields are {sorted(allowed)}")
			setattr(new, f"_{key}" if key in self._SUGARED else key, value)
		new._after_set(self)
		return new

	@classmethod
	def _settable_names(cls) -> set[str]:
		"""The public field names accepted by ``set`` — dataclass fields, but with each sugared ``_name`` storage
		field presented under its public ``name``."""
		names: set[str] = set()
		if dataclasses.is_dataclass(cls):
			for f in dataclasses.fields(cls):
				if f.name.startswith("_") and f.name[1:] in cls._SUGARED:
					names.add(f.name[1:])
				else:
					names.add(f.name)
		return names | set(cls._SUGARED)

	def _after_set(self, original) -> None:
		"""Hook called on the freshly copied object (``original`` is the receiver of ``set``). Subclasses reset
		volatile per-instance state that must not be shared with the original (KV cache, transcript, …). Default
		no-op."""

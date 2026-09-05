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

# [interlens-refgen] session ed74b25d — 2026-09-05

"""Walk the griffe object tree into a plain, path-resolved model of the reference site.

This module answers three questions and nothing else (no Markdown is produced here):

**What gets a page?** Every non-private module (one per ``.py`` file, ``__main__`` excluded), and every
public class and module-level function inside them. Methods and attributes do *not* get their own page —
they live on their class's page under an anchor, Apple-developer-docs style.

**Where does it go?** Paths are chosen so the downstream site's URL equals the file path. Both packages
and plain modules become a *directory* with an ``index.md`` (``interlens/runner/devices/index.md``), which
is what lets a module's symbols sit beneath it as siblings of its index. A symbol page is then
``<module dir>/<SymbolName>.md``. See :class:`ModuleNode` for the accessors.

**What is it called?** macOS (where this is authored) is case-insensitive, so a class ``Foo`` and a
function ``foo`` in one module would fight over one file. :func:`_assign_filenames` detects that
case-insensitively within each directory and disambiguates the *function* with a ``-fn`` suffix (and, for
the pathological case of a symbol literally named ``index``, a ``-cls``/``-fn`` suffix, since ``index.md``
is reserved for the module page). Collisions are reported so they never happen silently.

Alias hazards
-------------
Touching a griffe ``Alias`` can raise ``AliasResolutionError`` — ``interlens/__init__.py`` re-exports
``annotations`` (from ``__future__``), ``import_module`` and ``TYPE_CHECKING``, none of which resolve to
anything documentable. Worse, ``.is_module`` is True for an alias that *points at* a module (``from . import
surplus as S``), which would duplicate that module under a second path. So we never trust ``.is_module``:
submodule recursion tests ``isinstance(member, Module)``, and every other alias access is wrapped in
:func:`resolve_alias`, which returns ``None`` instead of raising.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from griffe import Alias, Attribute, Class, Function, Module, Object

REF_ROOT = "reference"  # docs-relative root of the generated tree; also the first path segment of every page id


def is_public(name: str) -> bool:
	"""Public = no leading underscore. Mirrors the old mkdocstrings ``filters: ["!^_"]`` exactly, which also
	means ``__init__`` is excluded from the Methods list (it is merged into the class signature instead)."""
	return not name.startswith("_")


def resolve_alias(obj: Object | Alias) -> Object | None:
	"""Return the object an alias ultimately points at, or ``None`` if it cannot be resolved.

	Unresolvable aliases are not an error condition here: re-exported stdlib/typing names and
	``from __future__ import annotations`` all land in this bucket and are simply not documentable.
	"""
	if not isinstance(obj, Alias):
		return obj
	try:
		return obj.final_target
	except Exception:  # AliasResolutionError, CyclicAliasError, KeyError — every flavour means "not documentable"
		return None


@dataclass
class ModuleNode:
	"""One documented module (package or plain module) plus its public surface and output paths."""

	obj: Module
	parts: tuple[str, ...]  #: dotted path split, e.g. ``("interlens", "runner", "devices")``
	is_package: bool
	children: list["ModuleNode"] = field(default_factory=list)
	#: ``(exported name, target object)`` for every public alias this module resolves — the link index.
	aliases: list[tuple[str, Object]] = field(default_factory=list)
	classes: list[Class] = field(default_factory=list)
	functions: list[Function] = field(default_factory=list)
	#: public module-level attributes — constants and type aliases (``DEFAULT_REGISTRY``, ``ModelLike``).
	attributes: list[Attribute] = field(default_factory=list)
	#: ``(exported name, target object)`` for public aliases re-exported by a *package* ``__init__``.
	reexports: list[tuple[str, Object]] = field(default_factory=list)
	#: symbol name -> page file stem (usually the name itself; see :func:`_assign_filenames`).
	stems: dict[str, str] = field(default_factory=dict)

	@property
	def dotted(self) -> str:
		return ".".join(self.parts)

	@property
	def dir(self) -> str:
		"""Docs-relative directory holding this module's index page and its symbol pages."""
		return "/".join((REF_ROOT, *self.parts))

	@property
	def page(self) -> str:
		"""Docs-relative, extension-less page id of the module index (``index`` dropped, per the schema)."""
		return self.dir

	def symbol_page(self, name: str) -> str:
		"""Docs-relative, extension-less page id of a symbol defined in this module."""
		return f"{self.dir}/{self.stems[name]}"

	def symbol_file(self, name: str) -> str:
		return f"{self.symbol_page(name)}.md"

	@property
	def index_file(self) -> str:
		return f"{self.dir}/index.md"


@dataclass
class Site:
	"""The whole reference: the module tree plus the lookup tables the renderers need."""

	root: ModuleNode
	modules: list[ModuleNode]  #: depth-first, sorted; every documented module exactly once
	#: canonical path -> page id, for every symbol that owns a page. Used for cross-links and hover cards.
	pages_by_path: dict[str, str]
	#: canonical path -> ``ModuleNode`` that defines it, so a link source can compute a relative path.
	owner_by_path: dict[str, ModuleNode]
	#: canonical path -> sorted public alias paths reaching it (``interlens.Conversation`` -> the real class).
	exported_as: dict[str, list[str]]
	#: (module dotted path, kept name, dropped name) triples, for the generator's log line.
	collisions: list[tuple[str, str, str]]


def _members(mod: Module, kind: type) -> list:
	"""Public, locally-*defined* members of ``mod`` of the given griffe type, sorted by name.

	Aliases are skipped deliberately: ``factories.py`` does ``from .conversation import Conversation``, and
	listing that as a class of ``interlens.factories`` would create a second page for the same class. Only
	the defining module documents a symbol; packages surface the rest through their Re-exported table.
	"""
	out = []
	for name, member in sorted(mod.members.items()):
		if not is_public(name) or isinstance(member, (Alias, Module)):
			continue
		if isinstance(member, kind):
			out.append(member)
	return out


def _aliases(mod: Module) -> list[tuple[str, Object]]:
	"""Public aliases of ``mod`` that resolve to a documentable interlens class/function/attribute.

	Used for two different things. As a module's **Re-exported** table this is restricted to packages, since
	a plain module's ``from .conversation import Conversation`` is an implementation detail whereas a
	package ``__init__``'s re-exports *are* its advertised API. As a **link index** it is collected from
	every module, because that is how an annotation resolves: ``conversation.py`` writes
	``participants: tuple[Participant, ...]`` and griffe reports the canonical path
	``interlens.participant.Participant`` — the alias path, not the class's own
	``interlens.participant.participant.Participant`` — so without the alias entries those cross-links
	would silently not render.
	"""
	out: list[tuple[str, Object]] = []
	for name, member in sorted(mod.members.items()):
		if not is_public(name) or not isinstance(member, Alias):
			continue
		target = resolve_alias(member)
		if target is None or isinstance(target, Module):
			continue
		if not target.path.startswith("interlens.") or not isinstance(target, (Class, Function, Attribute)):
			continue
		out.append((name, target))
	return out


def _assign_filenames(node: ModuleNode, collisions: list[tuple[str, str, str]]) -> None:
	"""Pick a unique, case-insensitively distinct file stem for each symbol page in ``node``'s directory.

	Classes are assigned first (they are the more prominent page and keep the plain name), then functions.
	``index`` is pre-reserved for the module page. A loser gets a kind suffix — ``-fn`` for a function,
	``-cls`` for a class — which keeps the URL readable and, unlike a numeric suffix, stays stable as the
	module grows.
	"""
	taken = {"index"}
	for kind_suffix, members in (("-cls", node.classes), ("-fn", node.functions)):
		for member in members:
			stem = member.name
			if stem.lower() in taken:
				stem = f"{member.name}{kind_suffix}"
				collisions.append((node.dotted, member.name, stem))
			taken.add(stem.lower())
			node.stems[member.name] = stem


def build_site(package: Module) -> Site:
	"""Walk ``package`` and return the fully path-resolved :class:`Site`."""
	modules: list[ModuleNode] = []
	collisions: list[tuple[str, str, str]] = []

	def walk(mod: Module, parts: tuple[str, ...]) -> ModuleNode:
		filepath = mod.filepath
		is_package = not isinstance(filepath, list) and filepath.name == "__init__.py"
		node = ModuleNode(obj=mod, parts=parts, is_package=is_package)
		node.classes = _members(mod, Class)
		node.functions = _members(mod, Function)
		# Module-level attributes get no page of their own: they are listed on, and anchored to, the module
		# index, exactly as class attributes are listed on their class page.
		node.attributes = _members(mod, Attribute)
		node.aliases = _aliases(mod)
		if is_package:
			node.reexports = node.aliases
		_assign_filenames(node, collisions)
		modules.append(node)
		for name, member in sorted(mod.members.items()):
			# `isinstance(..., Module)`, never `.is_module`: the latter is True for aliases to modules.
			if is_public(name) and isinstance(member, Module):
				node.children.append(walk(member, (*parts, name)))
		return node

	root = walk(package, (package.name,))

	pages_by_path: dict[str, str] = {}
	owner_by_path: dict[str, ModuleNode] = {}
	for node in modules:
		pages_by_path[node.dotted] = node.page
		owner_by_path[node.dotted] = node
		for member in (*node.classes, *node.functions):
			pages_by_path[member.path] = node.symbol_page(member.name)
			owner_by_path[member.path] = node
	# Second pass, `setdefault` so a real definition always wins: every alias path an annotation might name.
	for node in modules:
		for name, target in node.aliases:
			page = pages_by_path.get(target.path)
			if page:
				pages_by_path.setdefault(f"{node.dotted}.{name}", page)

	exported: dict[str, set[str]] = {}
	for node in modules:
		for name, target in node.reexports:
			exported.setdefault(target.path, set()).add(f"{node.dotted}.{name}")

	return Site(
		root=root,
		modules=modules,
		pages_by_path=pages_by_path,
		owner_by_path=owner_by_path,
		exported_as={path: sorted(names) for path, names in sorted(exported.items())},
		collisions=collisions,
	)


def public_methods(cls: Class) -> list[Function]:
	"""Public, locally-defined methods of ``cls``, excluding properties (those are Attributes in griffe)."""
	return [m for m in _members(cls, Function) if "property" not in m.labels]


def public_attributes(cls: Class) -> list[Attribute]:
	"""Public, locally-defined attributes of ``cls`` — dataclass fields, class vars, and properties alike."""
	return _members(cls, Attribute)

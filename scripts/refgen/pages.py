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

"""Render the Markdown pages: the reference root, one index per module, one page per class/function.

Page shapes follow Apple's developer docs: a symbol gets its *own* page opening with its signature and a
one-line summary, and its members live on that page under stable anchors rather than on pages of their
own. Concretely:

*Module index* — ``# `runner` `` (the *leaf* name, so the downstream site's title-derived nav does not read
``interlens`` > ``interlens.runner``) / a ``Module `interlens.runner``` subtitle carrying the full dotted
path / module docstring / ``## Modules`` (packages only) /
``## Re-exported`` (packages that re-export) / ``## Classes`` / ``## Functions``.

*Class page* — heading, summary, ```` ```python ```` signature (class name + ``__init__`` parameters, as
mkdocstrings' ``merge_init_into_class`` used to show), a **Defined in** line pointing at the module index
and at the exact source lines on GitHub, base classes (linked when they are interlens classes), the
docstring, a Parameters table, ``## Attributes {#attributes}``, then ``## Methods {#methods}`` followed by
one ``## `name` {#name}`` block per method.

*Function page* — the same body as a method, standing alone.

The explicit ``{#id}`` header attributes are load-bearing: ``symbols.json`` publishes ``anchor`` values that
the downstream site turns into deep links and hover-card targets, so the ids must be exactly the symbol
names and must not be left to a slugifier's discretion.

Everything here is a pure function from griffe objects to strings; file I/O lives in
:mod:`refgen.generate`.
"""
from __future__ import annotations

import posixpath
from dataclasses import dataclass

from griffe import Class, Function

from . import docstrings as ds
from .model import ModuleNode, Site, public_attributes, public_methods
from .signatures import annotation_markdown, relative_link, signature_block

INTRO = (
	"Every public class and function in `interlens`, one page each, generated from the source. "
	"Start from a module below, or jump straight to a symbol — pages carry their full signature, "
	"parameters, and a link to the exact lines that define them."
)


@dataclass(frozen=True)
class SourceLinker:
	"""Turns a griffe object into a permalink to the lines that define it on GitHub.

	``repo_url`` and the branch are read from ``mkdocs.yml`` by the generator rather than hard-coded, so
	the repository stays declared in exactly one place.
	"""

	repo_url: str
	root: object  #: repo root ``Path``, used to make ``filepath`` repo-relative (never absolute in output)
	branch: str = "main"

	def __call__(self, obj) -> str:
		try:
			path = obj.filepath.relative_to(self.root).as_posix()
		except (AttributeError, ValueError):
			return ""
		lines = f"#L{obj.lineno}-L{obj.endlineno}" if obj.lineno and obj.endlineno else ""
		return f"{self.repo_url}/blob/{self.branch}/{path}{lines}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
	if not rows:
		return ""
	out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
	out += ["| " + " | ".join(row) + " |" for row in rows]
	return "\n".join(out)


def _join(blocks: list[str]) -> str:
	"""One page from its blocks: blank line between, exactly one trailing newline (byte-stable output)."""
	return "\n\n".join(b.strip() for b in blocks if b and b.strip()) + "\n"


def _defined_in(obj, node: ModuleNode, source: SourceLinker, *, module_href: str = "index.md") -> str:
	url = source(obj)
	link = f" · [source]({url})" if url else ""
	return f"Defined in [`{node.dotted}`]({module_href}){link}"


def _bases(cls: Class, site: Site, from_dir: str) -> str:
	if not cls.bases:
		return ""
	rendered = ", ".join(annotation_markdown(base, site, from_dir) for base in cls.bases)
	return f"**Inherits from:** {rendered}"


def _callable_body(obj: Function, site: Site, from_dir: str, *, drop_self: bool) -> str:
	"""Docstring prose + Parameters table + Returns/Raises, shared by function pages and method blocks."""
	return _join([
		ds.render_sections(obj, site, from_dir, skip=("parameters", "other parameters"), drop_summary=True),
		ds.parameters_table(obj, site, from_dir, drop_self=drop_self),
	])


def render_module(node: ModuleNode, site: Site, source: SourceLinker) -> str:
	"""The module/package index page."""
	# The H1 is the *leaf* name only: the downstream site builds its navigation tree out of page titles, so a
	# full dotted title would read `interlens` > `interlens.context` > `interlens.context.context_policy` once
	# nested. The dotted path is not lost — it moves to the subtitle line directly under the H1.
	kind = "Package" if node.is_package else "Module"
	blocks = [f"# `{node.parts[-1]}`", f"{kind} `{node.dotted}`", ds.text_of(node.obj)]

	if node.children:
		rows = [
			f"- [`{child.parts[-1]}`]({posixpath.relpath(child.index_file, node.dir)})"
			+ (f" — {ds.summary(child.obj)}" if ds.summary(child.obj) else "")
			for child in sorted(node.children, key=lambda c: c.parts[-1])
		]
		blocks.append("## Modules\n\n" + "\n".join(rows))

	if node.reexports:
		rows = []
		for name, target in node.reexports:
			page = site.pages_by_path.get(target.path)
			if page:
				href = relative_link(page, node.dir)
			else:
				# A re-exported module-level attribute (a constant or type alias) has no page of its own —
				# point at the Attributes table on its module's index instead of leaving it unlinked.
				owner = site.owner_by_path.get(target.parent.path if target.parent else "")
				href = f"{posixpath.relpath(owner.index_file, node.dir)}#attributes" if owner else ""
			link = f"[`{name}`]({href})" if href else f"`{name}`"
			rows.append([link, f"`{target.parent.path}`", ds.cell(ds.summary(target))])
		blocks.append("## Re-exported\n\n" + _table(["Name", "Defined in", "Summary"], rows))

	if node.attributes:
		rows = [
			[f"`{a.name}`", annotation_markdown(a.annotation, site, node.dir), ds.cell(ds.summary(a))]
			for a in node.attributes
		]
		blocks.append("## Attributes {#attributes}\n\n" + _table(["Name", "Type", "Summary"], rows))

	for title, members in (("Classes", node.classes), ("Functions", node.functions)):
		rows = [
			[f"[`{m.name}`]({relative_link(node.symbol_page(m.name), node.dir)})", ds.cell(ds.summary(m))]
			for m in members
		]
		table = _table(["Name", "Summary"], rows)
		if table:
			blocks.append(f"## {title}\n\n" + table)

	return _join(blocks)


def render_class(cls: Class, node: ModuleNode, site: Site, source: SourceLinker) -> str:
	"""One class page, with its attributes and methods inlined under explicit anchors."""
	from_dir = node.dir
	blocks = [
		f"# `{cls.name}`",
		ds.summary(cls),
		signature_block(cls),
		_defined_in(cls, node, source),
		_bases(cls, site, from_dir),
		ds.render_sections(cls, site, from_dir, skip=("parameters", "other parameters"), drop_summary=True),
	]

	init = cls.members.get("__init__")
	if isinstance(init, Function):
		blocks.append(ds.parameters_table(init, site, from_dir, drop_self=True))

	attributes = public_attributes(cls)
	if attributes:
		rows = [
			[f"`{a.name}`", annotation_markdown(a.annotation, site, from_dir), ds.cell(ds.summary(a))]
			for a in attributes
		]
		blocks.append("## Attributes {#attributes}\n\n" + _table(["Name", "Type", "Summary"], rows))

	methods = public_methods(cls)
	if methods:
		blocks.append("## Methods {#methods}")
		for method in methods:
			url = source(method)
			blocks += [
				f"## `{method.name}` {{#{method.name}}}",
				signature_block(method),
				f"[source]({url})" if url else "",
				ds.summary(method),
				_callable_body(method, site, from_dir, drop_self=True),
			]

	return _join(blocks)


def render_function(func: Function, node: ModuleNode, site: Site, source: SourceLinker) -> str:
	"""One module-level function page — the method block, promoted to a page of its own."""
	return _join([
		f"# `{func.name}`",
		ds.summary(func),
		signature_block(func),
		_defined_in(func, node, source),
		_callable_body(func, site, node.dir, drop_self=False),
	])


def render_root(site: Site) -> str:
	"""``docs/reference/index.md``: the whole module tree as nested lists of links with summaries."""
	lines: list[str] = []

	def walk(node: ModuleNode, depth: int) -> None:
		href = posixpath.relpath(node.index_file, start="reference")
		summary = ds.summary(node.obj)
		# Four spaces per level, not tabs: CommonMark/Pandoc nest a sub-list on the parent's content column.
		# Leaf name, not the dotted path: the list already nests, so the prefix is visible in the ancestry.
		lines.append("    " * depth + f"- [`{node.parts[-1]}`]({href})" + (f" — {summary}" if summary else ""))
		for child in sorted(node.children, key=lambda c: c.parts[-1]):
			walk(child, depth + 1)

	walk(site.root, 0)
	return _join(["# API Reference", INTRO, "\n".join(lines)])

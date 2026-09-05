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

"""Build ``docs/reference/symbols.json`` — the machine-readable index of the whole public API.

The downstream sidmb site consumes this to auto-link bare identifiers inside code blocks across the entire
``/docs/interlens`` subsite and to render hover cards, so the schema is a **contract**: keys are stable,
``page`` is docs-relative and extension-less (``index`` dropped, so it is exactly the URL suffix under
``/docs/interlens/``), and ``anchor`` names the ``{#id}`` this generator writes into the page.

One entry per module, class, module-level function, method, and public attribute::

    {"path": "interlens.conversation.Conversation.run", "kind": "method",
     "page": "reference/interlens/conversation/Conversation", "anchor": "run",
     "summary": "...", "signature": "run(self, ...) -> Transcript", "params": [...], "returns": {...}}

Methods and attributes share their class's ``page`` and are distinguished by ``anchor`` — attributes all
point at ``attributes`` because they live in one table rather than under individual headings.

``exportedAs`` is what makes ``interlens.Conversation`` (the lazy re-export in the package ``__init__``)
resolve to the class's real page; it is computed once in :mod:`refgen.model` by resolving every package
alias. Output is sorted by ``path`` and written with a fixed indent so the file is byte-stable.
"""
from __future__ import annotations

import json

from griffe import Class, ExprName, Function

from . import docstrings as ds
from .model import ModuleNode, Site, public_attributes, public_methods
from .signatures import annotation_text, public_parameters, signature

SCHEMA_VERSION = 1


def _base_path(base) -> str:
	"""A base class as its **canonical** path (``interlens.functional.Functional``) when griffe can resolve
	it, so consumers can join it against a ``class`` entry's ``path``; otherwise the source text as written."""
	if isinstance(base, ExprName):
		try:
			return base.canonical_path
		except Exception:
			return base.name
	text = annotation_text(base)
	if base is not None and not isinstance(base, str):
		names = [e for e in base.iterate(flat=True) if isinstance(e, ExprName)]
		if len(names) == 1 and str(base) == names[0].name:
			try:
				return names[0].canonical_path
			except Exception:
				pass
	return text


def _params(obj: Function, *, drop_self: bool) -> list[dict]:
	"""``params`` entries: declared name/annotation/default plus the docstring description when present."""
	described = ds.parameter_descriptions(obj)
	items = public_parameters(obj.parameters, drop_self=drop_self)
	return [
		{
			"name": p.name,
			"annotation": annotation_text(p.annotation),
			"default": str(p.default) if p.default is not None else None,
			"description": described.get(p.name, ""),
		}
		for p in items
	]


def _class_entry(cls: Class, node: ModuleNode, site: Site) -> dict:
	init = cls.members.get("__init__")
	members = [m.path for m in public_methods(cls)] + [a.path for a in public_attributes(cls)]
	return {
		"path": cls.path,
		"kind": "class",
		"page": node.symbol_page(cls.name),
		"summary": ds.plain_summary(cls),
		"signature": signature(cls),
		"params": _params(init, drop_self=True) if isinstance(init, Function) else [],
		"returns": None,
		"bases": [_base_path(base) for base in cls.bases],
		"exportedAs": site.exported_as.get(cls.path, []),
		"members": sorted(members),
	}


def _function_entry(func: Function, node: ModuleNode, site: Site, *, kind: str, page: str, anchor=None) -> dict:
	entry = {
		"path": func.path,
		"kind": kind,
		"page": page,
		"summary": ds.plain_summary(func),
		"signature": signature(func),
		"params": _params(func, drop_self=False),
		"returns": ds.returns_entry(func, site, node.dir),
	}
	if kind == "function":
		entry["exportedAs"] = site.exported_as.get(func.path, [])
	if anchor is not None:
		# Insert `anchor` right after `page`, matching the documented key order for method entries.
		entry = {**{k: entry[k] for k in ("path", "kind", "page")}, "anchor": anchor,
		         **{k: v for k, v in entry.items() if k not in ("path", "kind", "page")}}
	return entry


def build(site: Site) -> dict:
	"""The complete ``symbols.json`` payload for a :class:`~refgen.model.Site`."""
	entries: list[dict] = []
	for node in site.modules:
		entries.append({
			"path": node.dotted,
			"kind": "module",
			"page": node.page,
			"summary": ds.plain_summary(node.obj),
		})
		for attribute in node.attributes:
			entries.append({
				"path": attribute.path,
				"kind": "attribute",
				"page": node.page,
				"anchor": "attributes",
				"summary": ds.plain_summary(attribute),
				"annotation": annotation_text(attribute.annotation),
			})
		for cls in node.classes:
			page = node.symbol_page(cls.name)
			entries.append(_class_entry(cls, node, site))
			for method in public_methods(cls):
				entries.append(
					_function_entry(method, node, site, kind="method", page=page, anchor=method.name)
				)
			for attribute in public_attributes(cls):
				entries.append({
					"path": attribute.path,
					"kind": "attribute",
					"page": page,
					"anchor": "attributes",
					"summary": ds.plain_summary(attribute),
					"annotation": annotation_text(attribute.annotation),
				})
		for func in node.functions:
			entries.append(
				_function_entry(func, node, site, kind="function", page=node.symbol_page(func.name))
			)

	return {
		"version": SCHEMA_VERSION,
		"language": "python",
		"package": site.root.dotted,
		"symbols": sorted(entries, key=lambda e: (e["path"], e["kind"])),
	}


def dumps(payload: dict) -> str:
	"""Serialise deterministically: fixed indent, no ASCII escaping, one trailing newline."""
	return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


__all__ = ["build", "dumps", "SCHEMA_VERSION"]

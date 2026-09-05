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

"""The driver: load the package with griffe, render every page, and write the tree.

This is the only module in :mod:`refgen` that touches the filesystem, which is what makes the reference
testable — :func:`generate` takes an output directory, so ``tests/test_reference_docs.py`` can render into
a temp dir and diff it byte-for-byte against the committed ``docs/reference/`` to prove the two never drift.

``griffe.load(..., allow_inspection=False)`` is deliberate: inspection would *import* ``interlens``, which
means importing ``torch`` and ``transformers``, in a docs build that has neither. Everything is read from
source text, and ``src/interlens/factories.pyi`` is merged into ``factories.py`` by griffe rather than
becoming a second module (verified: the stub yields no duplicate page).

The output directory is wiped first so pages for renamed or deleted symbols cannot linger — a stale page
would otherwise survive forever now that the tree is committed rather than regenerated into a temp dir.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import griffe

from . import markup, nav, pages, symbols
from .model import build_site

PACKAGE = "interlens"


@dataclass(frozen=True)
class Result:
	"""What :func:`generate` produced, for the caller's log line and for tests."""

	pages: int
	symbols: int
	modules: int
	collisions: list[tuple[str, str, str]]


def load(root: Path) -> griffe.Module:
	"""Statically load ``interlens`` from ``root/src`` with Google-style docstring parsing.

	Docstrings are normalised (:func:`refgen.markup.normalize_object_tree`) the moment they land and before
	anything reads a parsed section, so every renderer downstream sees Markdown rather than the RST
	inline literals and ``::`` literal blocks the sources are written with.
	"""
	module = griffe.load(
		PACKAGE,
		search_paths=[str(root / "src")],
		docstring_parser="google",
		allow_inspection=False,
	)
	markup.normalize_object_tree(module)
	return module


def generate(root: Path, out_dir: Path, *, splice_nav: bool = True) -> Result:
	"""Render the whole reference into ``out_dir`` (normally ``docs/reference``).

	``splice_nav`` is off for tests, which render into a temp dir and must not rewrite ``mkdocs.yml``.
	"""
	config = root / "mkdocs.yml"
	site = build_site(load(root))
	source = pages.SourceLinker(repo_url=nav.repo_url(config), root=root)

	shutil.rmtree(out_dir, ignore_errors=True)
	written = 0

	def write(relative: str, text: str) -> None:
		nonlocal written
		path = out_dir / relative
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(text, encoding="utf-8")
		written += 1

	write("index.md", pages.render_root(site))
	for node in site.modules:
		# `node.dir`/`node.symbol_file` are docs-relative (`reference/...`); strip that prefix to land inside
		# out_dir, which *is* the reference root. Keeps page ids and file paths derived from one source.
		def local(docs_path: str) -> str:
			return docs_path.split("/", 1)[1]

		write(local(node.index_file), pages.render_module(node, site, source))
		for cls in node.classes:
			write(local(node.symbol_file(cls.name)), pages.render_class(cls, node, site, source))
		for func in node.functions:
			write(local(node.symbol_file(func.name)), pages.render_function(func, node, site, source))

	payload = symbols.build(site)
	(out_dir / "symbols.json").write_text(symbols.dumps(payload), encoding="utf-8")

	if splice_nav:
		nav.splice(config, nav.nav_lines(site))

	return Result(
		pages=written,
		symbols=len(payload["symbols"]),
		modules=len(site.modules),
		collisions=site.collisions,
	)

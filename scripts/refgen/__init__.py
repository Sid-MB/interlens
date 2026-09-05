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

"""``refgen``: build a *real*, committed Markdown API reference for ``interlens`` from static analysis.

Why this exists
---------------
The reference used to be generated at **build time**: ``scripts/gen_ref_pages.py`` wrote one-line
mkdocstrings stubs (``::: interlens.runner``) into a gitignored ``docs/reference/``, and only a
mkdocstrings-capable renderer could expand them. The docs now live at https://sidmb.com/docs/interlens,
produced by a *different* repo that syncs this repo's ``docs/`` folder and renders every Markdown file
through Quarto/Pandoc. Stubs are meaningless there, and gitignored files never even reach the sync — so
the reference silently vanished. ``refgen`` therefore does the whole job here, once, and commits the
result: plain Markdown that any renderer can serve, plus a machine-readable index the downstream site
uses to auto-link identifiers and render hover cards.

Design
------
Static only. We read the source with `griffe` and never import ``interlens`` (which would drag in
``torch``/``transformers`` and a GPU-shaped environment into a docs build).

The pipeline is five stages, one module each, deliberately kept small and pure so each can be reasoned
about — and unit-tested — on its own:

1. :mod:`refgen.model` — walk the griffe tree into a plain :class:`~refgen.model.Site` of module nodes,
   decide every output path, and resolve case-insensitive filename collisions. Nothing here formats text.
2. :mod:`refgen.signatures` — turn griffe ``Parameters``/annotations into signature strings, and render
   annotations either as plain text (for fenced code blocks) or as cross-linked Markdown (for tables).
3. :mod:`refgen.markup` — normalise the RST habits the sources are written with (``literal`` spans and
   ``::`` literal blocks) into Markdown, on the raw docstring text before griffe parses it, so every
   consumer downstream sees one dialect.
4. :mod:`refgen.docstrings` — render parsed Google-style docstring sections into Markdown (Args → table,
   Returns/Raises → table, everything else → prose under a bold label). Per-symbol sub-sections are
   labels rather than headings on purpose: the site builds its page outline from headings, and a
   twenty-method class would otherwise contribute twenty "Parameters" entries to it. Only the generator's
   own structure (``## Attributes``/``## Methods``/the ``## `name` `` blocks) is a heading.
5. :mod:`refgen.pages` and :mod:`refgen.symbols` — emit the Markdown pages and ``symbols.json`` from the
   model. :mod:`refgen.nav` splices the module-index pages into ``mkdocs.yml``'s nav block.

Determinism is a hard requirement: the downstream site syncs by content, so regenerating on an unchanged
tree must produce byte-identical output. Every iteration is sorted, nothing embeds a timestamp or an
absolute path, and ``tests/test_reference_docs.py`` re-runs the generator into a temp dir and diffs it
against the committed tree so the two cannot drift.
"""
from __future__ import annotations

from .generate import generate

__all__ = ["generate"]

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

"""Auto-generate the API reference pages + nav from the ``interlens`` package, for the Zensical docs build.

This replaces the old mkdocs-gen-files/literate-nav pipeline (Zensical does not run those plugins). Instead of
build-time virtual files, it does two things that must happen BEFORE ``zensical build``:

1. Writes one real markdown stub per module under ``docs/reference/`` (gitignored — regenerated on every run),
   each holding a single mkdocstrings ``:::`` directive that Zensical's native mkdocstrings module renders.
   Package ``__init__.py`` files become the ``index.md`` of their section, so clicking a package heading lands
   on the re-exported public surface (Zensical's built-in index-page handling, was the section-index plugin).
2. Splices the matching nav tree into ``mkdocs.yml`` between the BEGIN/END marker comments below, so the
   sidebar mirrors the package layout with no manual upkeep (was literate-nav's job). The splice is a plain
   text replacement between markers — comments and everything else in mkdocs.yml are left untouched.

It also invokes ``gen_llms_txt.py`` so the whole pre-build generation is one command. Run it before every
build; Vercel does this in ``vercel.ts``'s buildCommand (``.github/workflows/docs.yml`` is the manual
fallback). Locally::

    python scripts/gen_ref_pages.py && zensical serve
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep scripts/ free of __pycache__ clutter
sys.path.insert(0, str(Path(__file__).resolve().parent))  # so this works from any cwd, not just scripts/
import gen_llms_txt

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
REF_DIR = ROOT / "docs" / "reference"
CONFIG = ROOT / "mkdocs.yml"

# Marker lines in mkdocs.yml (must match exactly, including indentation) that delimit the generated nav block.
BEGIN = "      # BEGIN generated reference nav — run scripts/gen_ref_pages.py to refresh; do not edit by hand"
END = "      # END generated reference nav"

INDEX_KEY = "__index__"  # tree key holding a package's own index page (its __init__.py stub)


def build_tree() -> dict:
	"""Walk ``src`` and return a nested dict mirroring the package layout.

	Each package maps to a sub-dict (with its ``__init__`` page under ``INDEX_KEY``); each module maps to its
	stub page's docs-relative path. Stub files are written as a side effect. ``__main__`` modules are skipped —
	CLI entrypoints have no useful API surface.
	"""
	tree: dict = {}
	for path in sorted(SRC.rglob("*.py")):
		parts = path.relative_to(SRC).with_suffix("").parts
		if parts[-1] == "__main__":
			continue
		is_pkg = parts[-1] == "__init__"
		if is_pkg:
			parts = parts[:-1]
		if not parts:  # a top-level src/__init__.py (none today) — nothing to document
			continue

		doc_path = Path("reference", *parts, "index.md") if is_pkg else Path("reference", *parts).with_suffix(".md")
		identifier = ".".join(parts)
		stub = ROOT / "docs" / doc_path
		stub.parent.mkdir(parents=True, exist_ok=True)
		stub.write_text(f"# `{identifier}`\n\n::: {identifier}\n")

		node = tree
		for part in parts[:-1]:
			node = node.setdefault(part, {})
		if is_pkg:
			node.setdefault(parts[-1], {})[INDEX_KEY] = doc_path.as_posix()
		else:
			node[parts[-1]] = doc_path.as_posix()
	return tree


def emit_nav(tree: dict, indent: int) -> list[str]:
	"""Render the tree as mkdocs.yml nav lines. A package's index page is emitted first, title-less, so
	Zensical treats it as the section's landing page; children follow alphabetically (packages and modules
	interleaved, matching the old literate-nav ordering)."""
	lines = []
	index = tree.get(INDEX_KEY)
	if index:
		lines.append(f"{' ' * indent}- {index}")
	for name in sorted(k for k in tree if k != INDEX_KEY):
		sub = tree[name]
		if isinstance(sub, dict):
			lines.append(f"{' ' * indent}- {name}:")
			lines.extend(emit_nav(sub, indent + 4))
		else:
			lines.append(f"{' ' * indent}- {name}: {sub}")
	return lines


def splice_nav(nav_lines: list[str]) -> None:
	"""Replace the lines between the BEGIN/END markers in mkdocs.yml with the freshly generated nav."""
	lines = CONFIG.read_text().splitlines()
	try:
		start, stop = lines.index(BEGIN), lines.index(END)
	except ValueError:
		raise SystemExit(f"gen_ref_pages: BEGIN/END nav markers not found in {CONFIG}")
	lines[start + 1 : stop] = nav_lines
	CONFIG.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
	shutil.rmtree(REF_DIR, ignore_errors=True)  # drop stale pages for renamed/deleted modules
	tree = build_tree()
	splice_nav(emit_nav(tree, indent=6))
	pages = gen_llms_txt.generate()
	print(f"gen_ref_pages: wrote {sum(1 for _ in REF_DIR.rglob('*.md'))} pages + llms.txt ({pages} pages), nav spliced into mkdocs.yml")

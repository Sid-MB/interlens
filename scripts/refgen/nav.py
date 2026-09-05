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

"""Splice the generated reference nav into ``mkdocs.yml``, and read the repo/site config back out of it.

The mkdocs/Zensical site is no longer the published home of the docs (that moved to sidmb.com), but it is
still the local preview and the fallback build, so the nav is kept working. It lists **module index pages
only**: adding ~700 symbol pages would make the sidebar unusable, and they are all one click away from
their module page anyway. Editing is a plain text replacement between two marker comments, so every
comment and hand-written section of ``mkdocs.yml`` survives untouched.

``mkdocs.yml`` also stays the single source of truth for ``repo_url`` — :func:`repo_url` reads it so the
GitHub source links on every page are not a second hard-coded copy of the repository address.
"""
from __future__ import annotations

import re
from pathlib import Path

from .model import ModuleNode, Site

BEGIN = "      # BEGIN generated reference nav — run scripts/gen_ref_pages.py to refresh; do not edit by hand"
END = "      # END generated reference nav"


def repo_url(config: Path) -> str:
	"""``repo_url`` from ``mkdocs.yml`` (trailing slash stripped), used to build source permalinks."""
	match = re.search(r"^repo_url:\s*(\S+)", config.read_text(), re.MULTILINE)
	if match is None:
		raise SystemExit(f"refgen: no `repo_url:` found in {config}")
	return match[1].rstrip("/")


def nav_lines(site: Site, indent: int = 6) -> list[str]:
	"""The nav block: the reference root, then the module tree as nested sections of index pages."""
	lines = [f"{' ' * indent}- reference/index.md"]

	def emit(node: ModuleNode, level: int) -> None:
		pad = " " * (indent + level * 4)
		if not node.children:  # a leaf module is one entry, not a section wrapping a single page
			lines.append(f"{pad}- {node.parts[-1]}: {node.index_file}")
			return
		lines.append(f"{pad}- {node.parts[-1]}:")
		lines.append(f"{pad}    - {node.index_file}")  # title-less: the section's landing page
		for child in sorted(node.children, key=lambda c: c.parts[-1]):
			emit(child, level + 1)

	emit(site.root, 0)
	return lines


def splice(config: Path, lines: list[str]) -> None:
	"""Replace everything between the BEGIN/END markers in ``mkdocs.yml`` with ``lines``."""
	text = config.read_text().splitlines()
	try:
		start, stop = text.index(BEGIN), text.index(END)
	except ValueError:
		raise SystemExit(f"refgen: BEGIN/END nav markers not found in {config}")
	text[start + 1 : stop] = lines
	config.write_text("\n".join(text) + "\n")

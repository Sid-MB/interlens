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

"""Regenerate the committed API reference under ``docs/reference/`` (plus ``llms.txt``).

Entrypoint only — the work lives in :mod:`refgen` (see its ``__init__`` for the design). The name is kept
because ``vercel.ts`` and ``.github/workflows/docs.yml`` invoke it, but what it does changed completely:

- **Was**: write one-line mkdocstrings stubs (``::: interlens.runner``) into a *gitignored*
  ``docs/reference/``, to be expanded at build time by Zensical's mkdocstrings module.
- **Is**: write real, committed Markdown — one page per module, class, and module-level function — plus
  ``docs/reference/symbols.json``. The published docs now live at https://sidmb.com/docs/interlens, built
  by a separate repo that syncs this ``docs/`` folder and renders it through Quarto/Pandoc; it can neither
  expand mkdocstrings directives nor see gitignored files, so both had to go.

Its output is **committed**: run this whenever the public API changes and commit the diff.
``tests/test_reference_docs.py`` fails the build if the committed tree drifts from the source.

    uv run --with griffe --no-project python scripts/gen_ref_pages.py

The mkdocs/Zensical nav splice (module index pages only) and ``gen_llms_txt`` still run, so the local
``zensical serve`` preview keeps working unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep scripts/ free of __pycache__ clutter
sys.path.insert(0, str(Path(__file__).resolve().parent))  # so this works from any cwd, not just scripts/

import gen_llms_txt
from refgen import generate

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
	result = generate(ROOT, ROOT / "docs" / "reference")
	for module, name, stem in result.collisions:
		print(f"gen_ref_pages: filename collision in {module}: `{name}` -> {stem}.md")
	llms_pages = gen_llms_txt.generate()
	print(
		f"gen_ref_pages: wrote {result.pages} pages ({result.modules} modules) + symbols.json "
		f"({result.symbols} symbols) + llms.txt ({llms_pages} pages), nav spliced into mkdocs.yml"
	)

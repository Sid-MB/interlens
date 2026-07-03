"""Auto-generate the API reference tree from the ``interlens`` package at build time.

Run by the ``mkdocs-gen-files`` plugin (see ``mkdocs.yml``). For every module under ``src/interlens`` it writes a
virtual ``reference/<path>.md`` containing a single mkdocstrings ``:::`` directive, and accumulates a literate-nav
``reference/SUMMARY.md`` so the API section's navigation mirrors the package layout with no manual upkeep. Package
``__init__.py`` files become the ``index.md`` of their section (paired with the ``section-index`` plugin), so clicking
a package heading lands on the re-exported public surface. Nothing is written to disk in the repo — the pages exist
only inside the built site.
"""
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
root = Path(__file__).parent.parent
src = root / "src"

for path in sorted(src.rglob("*.py")):
	module_path = path.relative_to(src).with_suffix("")
	doc_path = path.relative_to(src).with_suffix(".md")
	full_doc_path = Path("reference", doc_path)

	parts = tuple(module_path.parts)
	if parts[-1] == "__init__":            # package → its section landing page
		parts = parts[:-1]
		doc_path = doc_path.with_name("index.md")
		full_doc_path = full_doc_path.with_name("index.md")
	elif parts[-1] == "__main__":          # skip CLI entrypoints — no useful API surface
		continue
	if not parts:                          # the top-level src/__init__ (none here) — nothing to document
		continue

	nav[parts] = doc_path.as_posix()
	with mkdocs_gen_files.open(full_doc_path, "w") as fd:
		identifier = ".".join(parts)
		fd.write(f"# `{identifier}`\n\n::: {identifier}\n")
	mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
	nav_file.writelines(nav.build_literate_nav())

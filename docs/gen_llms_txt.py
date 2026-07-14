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

"""Emit ``llms.txt`` and ``llms-full.txt`` into ``docs/`` (replaces the mkdocs-llmstxt plugin).

Zensical doesn't run mkdocs-llmstxt, so this standalone script reproduces its output BEFORE the build. The
files are written into ``docs/`` (gitignored) rather than the built site because Zensical copies non-markdown
files verbatim to the site root — that way they exist under ``zensical serve`` too, not just ``build``:

- ``docs/llms.txt``      → the https://llmstxt.org index: site title, one-line description, and per-section
  links to the page URLs (titles are read from each page's first ``#`` heading).
- ``docs/llms-full.txt`` → the concatenated markdown bodies of the same pages, with ``--8<--`` snippet
  includes expanded (so the README lands in full where ``docs/index.md`` includes it) — one self-contained
  file an LLM can ingest without crawling.

Only the hand-written pages (overview + examples) are included, mirroring the old plugin config; the API
reference is huge, generated, and better consumed via the objects.inv / rendered pages.

Runs as part of the single pre-build step — ``docs/gen_ref_pages.py`` invokes it (see there), so CI and
local serve only ever run that one script.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Single source of truth: the published URL is mkdocs.yml's `site_url` (also what Zensical uses for
# canonical links and the sitemap) — read it from there rather than duplicating the constant here.
_site_url = re.search(r"^site_url:\s*(\S+)", (ROOT / "mkdocs.yml").read_text(), re.MULTILINE)
if _site_url is None:
	raise SystemExit("gen_llms_txt: no `site_url:` found in mkdocs.yml")
SITE_URL = _site_url[1].rstrip("/") + "/"

DESCRIPTION = (
	"interlens is a harness for multi-agent (model-to-model) conversations with first-class interpretability "
	"— activation capture, steering, activation patching, and token logprobs — all hooked into the same "
	"generation path as real turns, scaling from one dialogue to thousands of checkpointed multi-GPU rollouts."
)

# Section title → docs-relative pages, in reading order (mirrors the old mkdocs-llmstxt `sections` config).
SECTIONS = {
	"Overview": ["index.md"],
	"Examples (simple to advanced)": sorted(p.relative_to(DOCS).as_posix() for p in (DOCS / "examples").glob("*.md")),
}

SNIPPET = re.compile(r'^-{2}8<-{2} "(?P<file>[^"]+)"$', re.MULTILINE)


def expand(page: str) -> str:
	"""Return a page's markdown with ``--8<-- "file"`` include lines replaced by the file's content
	(resolved against the repo root, matching pymdownx.snippets' ``base_path: ["."]``)."""
	text = (DOCS / page).read_text()
	return SNIPPET.sub(lambda m: (ROOT / m["file"]).read_text(), text)


def title_of(markdown: str, fallback: str) -> str:
	"""First ``#`` heading of the page, or the filename if it has none."""
	m = re.search(r"^# (.+)$", markdown, re.MULTILINE)
	return m[1].replace("`", "").strip() if m else fallback


def url_of(page: str) -> str:
	"""The page's published URL under directory-style routing (``index.md`` → its directory root)."""
	route = re.sub(r"(^|/)index\.md$", r"\1", page)
	return SITE_URL + re.sub(r"\.md$", "/", route)


def generate() -> int:
	"""Write ``docs/llms.txt`` + ``docs/llms-full.txt``; returns the number of pages covered."""
	index = [f"# interlens\n\n> {DESCRIPTION}\n"]
	full = []
	for section, pages in SECTIONS.items():
		index.append(f"## {section}\n")
		for page in pages:
			body = expand(page)
			index.append(f"- [{title_of(body, page)}]({url_of(page)})")
			full.append(body.strip())
		index.append("")
	(DOCS / "llms.txt").write_text("\n".join(index).strip() + "\n")
	(DOCS / "llms-full.txt").write_text("\n\n---\n\n".join(full) + "\n")
	return sum(len(p) for p in SECTIONS.values())


if __name__ == "__main__":
	print(f"gen_llms_txt: wrote llms.txt + llms-full.txt ({generate()} pages)")

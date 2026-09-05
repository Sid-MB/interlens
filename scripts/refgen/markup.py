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

"""Normalise reStructuredText habits out of docstrings *before* griffe parses them.

The interlens docstrings were written with Sphinx muscle memory even though the parser is Google-style and
the renderer is Markdown, so two RST constructs leak straight through to the page:

``code``
	RST's inline-literal marker. Markdown reads the outer pair as an empty code span, so the site shows
	stray backticks around every identifier.

a paragraph ending in ``::``
	RST's literal block: the trailing ``::`` means "a code block follows, indented". Markdown has no such
	rule, so the block renders as an indented (four-space) code chunk *if* it happens to be indented
	enough, and as a mangled continuation of the paragraph otherwise — and the doubled colon is always
	visible.

Rewriting the **raw docstring text** rather than griffe's parsed sections is what keeps this to one small
module: every consumer (page bodies, summaries, table cells, ``symbols.json`` descriptions) reads through
the parsed sections or through :func:`refgen.docstrings.text_of`, and all of them ultimately read
``docstring.value``. :func:`normalize_object_tree` rewrites that value once, right after the griffe load
and before anything touches the cached ``parsed`` property, so there is exactly one place where the
RST-to-Markdown rules live and no post-processing pass that has to re-find code spans in rendered tables.

Fenced code blocks are held out of the inline pass: a ``` fence's own backticks must not be mistaken for
an inline-literal pair, and prose rules have no business inside someone's example code.
"""
from __future__ import annotations

import re

#: An RST inline literal: exactly two backticks, not part of a longer run (which would be a fence).
_INLINE_LITERAL = re.compile(r"(?<!`)``(?!`)((?:(?!\n[ \t]*\n).)+?)(?<!`)``(?!`)", re.DOTALL)

#: A ``` or ~~~ fence line, used to hold example code out of the inline rewrite. The trailing ``[^`~]*$`` is
#: what distinguishes a real fence from prose that merely *starts* with backticks — a docstring quoting a
#: fence inline (```` ``` ```tool_code ``` ````) would otherwise flip the whole rest of the docstring into
#: "inside a code block" and leave every literal after it unconverted.
_FENCE = re.compile(r"^[ \t]*(```+|~~~+)[^`~]*$")

#: ``**bold**`` emphasis, stripped from plain-text summary fields. Only the asterisk form: ``__x__`` is far
#: more often a dunder (``__post_init__``) than emphasis in a Python API's prose.
_BOLD = re.compile(r"(?<!\*)\*\*(?!\s)(.+?)(?<!\s)\*\*(?!\*)", re.DOTALL)

#: An inline code span, of any backtick run length — its contents are code and never emphasis markup.
_CODE_SPAN = re.compile(r"(`+)(?:.+?)\1", re.DOTALL)


def _indent_of(line: str) -> int:
	"""Width of ``line``'s leading whitespace (griffe has already expanded tabs when it cleaned the value)."""
	return len(line) - len(line.lstrip())


def _split_fences(text: str) -> list[tuple[bool, list[str]]]:
	"""Split ``text`` into ``(is_fenced, lines)`` runs so prose rules can skip fenced code blocks."""
	runs: list[tuple[bool, list[str]]] = []
	fenced = False
	for line in text.split("\n"):
		is_fence = bool(_FENCE.match(line))
		if fenced:
			runs[-1][1].append(line)
			fenced = not is_fence
		elif is_fence:
			runs.append((True, [line]))
			fenced = True
		else:
			if not runs or runs[-1][0]:
				runs.append((False, []))
			runs[-1][1].append(line)
	return runs


def inline_literals(text: str) -> str:
	"""``x`` → `x` in prose, leaving fenced code blocks untouched."""
	out: list[str] = []
	for fenced, lines in _split_fences(text):
		chunk = "\n".join(lines)
		out.append(chunk if fenced else _INLINE_LITERAL.sub(lambda m: f"`{m[1]}`", chunk))
	return "\n".join(out)


def literal_blocks(text: str) -> str:
	"""RST literal blocks → fenced ```python blocks.

	A line ending in ``::`` introduces the block; the block is every following line indented deeper than
	that introducing line (blank lines included), which is exactly RST's own rule. The block is dedented to
	its own minimum indent and re-emitted at the *introducing* line's indent, so a literal block written
	inside a Google section (under ``Args:``, say) stays inside that section when griffe parses it.

	``foo::`` becomes ``foo:``; a paragraph consisting of ``::`` alone disappears, as in RST.
	"""
	lines = text.split("\n")
	out: list[str] = []
	index = 0
	fenced = False
	while index < len(lines):
		line = lines[index]
		if _FENCE.match(line):
			fenced = not fenced
		if fenced or not line.rstrip().endswith("::"):
			out.append(line)
			index += 1
			continue

		intro_indent = _indent_of(line)
		# Find the block: skip blanks, then take every line indented deeper than the introducing line.
		scan = index + 1
		while scan < len(lines) and not lines[scan].strip():
			scan += 1
		block_start = scan
		while scan < len(lines) and (not lines[scan].strip() or _indent_of(lines[scan]) > intro_indent):
			scan += 1
		# Trailing blank lines belong to the document, not to the block.
		block_end = scan
		while block_end > block_start and not lines[block_end - 1].strip():
			block_end -= 1
		block = lines[block_start:block_end]
		if not block:  # `::` with nothing indented under it — just fix the doubled colon
			out.append(line.rstrip()[:-1])
			index += 1
			continue

		head = line.rstrip()[:-1]  # `turn::` -> `turn:`
		if head.strip() != ":":  # a lone `::` paragraph is a pure marker in RST and prints nothing
			out.append(head)
		pad = " " * intro_indent
		strip = min(_indent_of(b) for b in block if b.strip())
		out += ["", f"{pad}```python"] + [f"{pad}{b[strip:]}" if b.strip() else "" for b in block] + [f"{pad}```"]
		out += lines[block_end:scan]  # the blank lines we trimmed off the block
		index = scan
	return "\n".join(out)


#: An ATX Markdown heading written by hand inside a docstring.
_HEADING = re.compile(r"^[ \t]*(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")


def demote_headings(text: str) -> str:
	"""Hand-written ``## Heading`` lines inside a docstring → bold label lines.

	A heading in a *symbol's* docstring lands inside that symbol's section of a page — on a class page it
	sits under one method among twenty — so it has no honest place in the page's heading hierarchy and only
	adds an entry to the site's "On this page" outline that the reader cannot navigate meaningfully. The
	generator owns the page's headings; docstring prose gets labels.
	"""
	out: list[str] = []
	for fenced, lines in _split_fences(text):
		if fenced:
			out += lines
			continue
		for index, line in enumerate(lines):
			match = _HEADING.match(line)
			if not match:
				out.append(line)
				continue
			# A heading is block-level and needs no blank line under it; a bold label does, or it joins
			# the paragraph that follows.
			out.append(f"**{match[2]}**")
			if index + 1 < len(lines) and lines[index + 1].strip():
				out.append("")
	return "\n".join(out)


def normalize(text: str) -> str:
	"""Rewrite one docstring from RST habits into the Markdown the site actually renders."""
	return inline_literals(literal_blocks(text))


def plain(text: str) -> str:
	"""Drop ``**bold**`` emphasis, keeping `inline code` — and everything inside it — untouched.

	``symbols.json`` summaries are shown by the downstream hover card as plain text with inline code only,
	so a stray ``**`` there is rendered literally rather than as emphasis. Code spans are held out because
	``**`` inside one is Python (``f(**kwargs)``), not markup.
	"""
	out: list[str] = []
	index = 0
	for span in _CODE_SPAN.finditer(text):
		out.append(_strip_bold(text[index : span.start()]))
		out.append(span[0])
		index = span.end()
	out.append(_strip_bold(text[index:]))
	return "".join(out)


def _strip_bold(text: str) -> str:
	previous = None
	while previous != text:  # nested/adjacent emphasis needs more than one pass
		previous = text
		text = _BOLD.sub(lambda m: m[1], text)
	return text


def normalize_object_tree(root) -> None:
	"""Apply :func:`normalize` to every docstring in a griffe tree, in place.

	Must run before anything reads ``Docstring.parsed`` (a ``cached_property``); the cache is cleared
	anyway so the function stays safe to call twice. Aliases are skipped — their docstring belongs to the
	target object, which is visited on its own.
	"""
	seen: set[int] = set()

	def visit(obj) -> None:
		if id(obj) in seen or getattr(obj, "is_alias", False):
			return
		seen.add(id(obj))
		docstring = getattr(obj, "docstring", None)
		if docstring is not None and docstring.value:
			docstring.__dict__.pop("parsed", None)
			docstring.value = normalize(docstring.value)
		for member in getattr(obj, "members", {}).values():
			visit(member)

	visit(root)


__all__ = ["normalize", "normalize_object_tree", "plain"]

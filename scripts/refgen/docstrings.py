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

"""Render parsed Google-style docstring sections into Markdown.

griffe hands back a list of typed sections (``text``, ``parameters``, ``returns``, ``raises``,
``examples``, ``admonition``, ...). We dispatch on the section kind rather than re-parsing text, so the
rules stay in one table:

===============  ===========================================================================
``text``         passed through verbatim — the docstrings here are already Markdown prose
``parameters``   table: Name | Type | Default | Description
``returns``      table when there is more than one entry or an entry is named; otherwise prose
``yields``       same as ``returns``
``raises``       table: Exception | Description
``examples``     left as code — reformatting someone's worked example only ever damages it
anything else    a bold **label** with the section's items beneath it
===============  ===========================================================================

Two subtleties worth knowing:

*Summaries.* Every page and every table row needs a one-liner. :func:`summary` takes the first paragraph,
collapses its wrapping (these docstrings wrap at ~110 columns mid-sentence, so "the first line" is usually
half a thought), then trims to the first real sentence end — skipping ``e.g.``-style abbreviations and
periods inside ``inline code``. A symbol with no docstring gets ``""``, never a placeholder.

*Tables.* Descriptions are free-form Markdown that may span lines and contain pipes. :func:`cell` collapses
them to a single line and escapes ``|``; anything genuinely block-level (a fenced example inside an
``Args:`` entry) would break the table, so fences are collapsed to inline code.
"""
from __future__ import annotations

import re

from . import markup
from .signatures import annotation_markdown, annotation_text, public_parameters

#: Trailing-period words that do *not* end a sentence, so :func:`summary` keeps reading past them.
_ABBREVIATIONS = ("e.g.", "i.e.", "cf.", "etc.", "vs.", "approx.", "resp.", "al.", "Fig.", "Eq.")

#: The same list, anchored to a word boundary: a plain ``endswith`` made "Register a complete deal." look
#: like the "et al." abbreviation (and "the capital." like "approx." would, once such a word appears), so
#: every such summary silently swallowed its second sentence.
_ABBREVIATION_RE = re.compile(
	r"(?:^|[^\w.])(?:" + "|".join(re.escape(abbr) for abbr in _ABBREVIATIONS) + r")$", re.IGNORECASE
)


def _ends_with_abbreviation(head: str) -> bool:
	"""Does ``head`` end in an abbreviation's period rather than a sentence's?"""
	return _ABBREVIATION_RE.search(head) is not None


def text_of(obj) -> str:
	"""The full docstring text of a griffe object (``""`` when it has none), with indentation cleaned."""
	return obj.docstring.value.strip() if obj.docstring is not None else ""


def summary(obj) -> str:
	"""One-line summary of a griffe object: the first sentence of its docstring, or ``""``.

	Deliberately empty rather than "No description available" — 34 public interlens symbols have no
	docstring, and an honest blank cell reads better than 34 identical apologies (and lets the downstream
	site decide what to show).
	"""
	body = text_of(obj)
	if not body:
		return ""
	paragraph = " ".join(line.strip() for line in body.split("\n\n")[0].splitlines()).strip()
	return _first_sentence(paragraph)


def _first_sentence(paragraph: str) -> str:
	"""Trim a collapsed paragraph at its first genuine sentence end (``. ``/``! ``/``? `` + capital)."""
	for match in re.finditer(r"[.!?](?=\s)", paragraph):
		head = paragraph[: match.end()]
		if _ends_with_abbreviation(head):
			continue
		if head.count("`") % 2:  # the period lives inside an unclosed inline-code span
			continue
		rest = paragraph[match.end() :].lstrip()
		if rest and not (rest[0].isupper() or rest[0] in "`*_[("):
			continue
		return head
	return paragraph


def plain_summary(obj) -> str:
	""":func:`summary`, with ``**bold**`` markers dropped — the form ``symbols.json`` publishes.

	The downstream hover card renders a summary as plain text plus inline code, so emphasis markup that is
	perfectly fine in a page body would show up there as literal asterisks.
	"""
	return markup.plain(summary(obj))


def _labelled(title: str, body: str) -> str:
	"""A docstring sub-section: a bold label line over its body, deliberately *not* a heading.

	Per-symbol sections (Parameters/Returns/Raises/…) repeat on every method of a class page, and the site
	builds its "On this page" outline from every heading in the document — so emitting them as ``###``
	filled a twenty-method class's outline with twenty identical "Parameters" entries. A bold label reads
	the same in the rendered page and leaves the outline holding only the ``##`` symbol names.
	"""
	return f"**{title}**\n\n{body}" if body.strip() else ""


def cell(text: str) -> str:
	"""Squeeze arbitrary Markdown into one table cell: single line, pipes escaped, fences inlined."""
	text = (text or "").strip()
	text = re.sub(r"```+\w*\n(.*?)\n```+", lambda m: f"`{' '.join(m[1].split())}`", text, flags=re.DOTALL)
	text = " ".join(text.split())
	return text.replace("|", "\\|")


def _table(headers: list[str], rows: list[list[str]]) -> str:
	"""A GitHub-flavoured Markdown table; returns ``""`` for no rows so callers can skip empty sections."""
	if not rows:
		return ""
	lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
	lines += ["| " + " | ".join(row) + " |" for row in rows]
	return "\n".join(lines)


def parameters_table(obj, site, from_dir: str, *, drop_self: bool = False) -> str:
	"""The Parameters table for a callable, built from the **signature** and annotated from the docstring.

	Driving this off ``obj.parameters`` rather than off the docstring's ``Args:`` section is a deliberate
	inversion of mkdocstrings' default: only 13 callables in interlens write an ``Args:`` block, so a
	docstring-driven table would leave the other several hundred pages with no parameter list at all. The
	signature is always complete and always correct; the docstring, when it exists, only supplies prose.
	Callers therefore pass ``skip=("parameters",)`` to :func:`render_sections` to avoid printing it twice.
	"""
	described = parameter_descriptions(obj)
	params = public_parameters(obj.parameters, drop_self=drop_self)
	rows = [
		[
			f"`{param.name}`",
			annotation_markdown(param.annotation, site, from_dir),
			f"`{param.default}`" if param.default is not None else "*required*",
			cell(described.get(param.name, "")),
		]
		for param in params
	]
	table = _table(["Name", "Type", "Default", "Description"], rows)
	return _labelled("Parameters", table) if table else ""


def _returns(section, site, from_dir: str, title: str) -> str:
	entries = list(section.value)
	# A single, unnamed return reads far better as a sentence than as a one-row table.
	if len(entries) == 1 and not entries[0].name:
		entry = entries[0]
		annotation = annotation_markdown(entry.annotation, site, from_dir)
		prefix = f"{annotation} — " if annotation else ""
		return _labelled(title, f"{prefix}{entry.description.strip()}")
	rows = [
		[f"`{e.name}`" if e.name else "", annotation_markdown(e.annotation, site, from_dir), cell(e.description)]
		for e in entries
	]
	return _labelled(title, _table(["Name", "Type", "Description"], rows))


def _raises(section, site, from_dir: str) -> str:
	rows = [[annotation_markdown(e.annotation, site, from_dir), cell(e.description)] for e in section.value]
	return _labelled("Raises", _table(["Exception", "Description"], rows))


def _attributes(section, site, from_dir: str) -> str:
	rows = [
		[f"`{e.name}`", annotation_markdown(e.annotation, site, from_dir), cell(e.description)]
		for e in section.value
	]
	return _labelled("Attributes", _table(["Name", "Type", "Description"], rows))


def _examples(section, *_args) -> str:
	"""``Examples:`` bodies are emitted untouched — griffe splits them into (kind, text) chunks where the
	code chunks are already fenced-block material and the prose chunks are Markdown."""
	chunks = []
	for kind, value in section.value:
		chunks.append(str(value).strip() if str(kind).endswith("text") else f"```python\n{str(value).strip()}\n```")
	return _labelled("Examples", "\n\n".join(c for c in chunks if c))


def _admonition(section, *_args) -> str:
	return _labelled(section.title or "Note", str(section.value.description).strip())


def _fallback(section, *_args) -> str:
	"""Any section kind we have not special-cased: a bold label over its stringified items."""
	value = section.value
	items = value if isinstance(value, list) else [value]
	body = "\n".join(f"- {cell(str(getattr(i, 'description', i)))}" for i in items)
	return _labelled(str(section.kind.value).replace("_", " ").title(), body)


def strip_summary(body: str, lead: str) -> str:
	"""Drop the leading summary sentence from a docstring body, tolerating the source's line wrapping.

	Pages print the summary as their standalone abstract (Apple-docs style) and then the discussion; without
	this the first sentence would appear twice in a row. The comparison is whitespace-insensitive because
	``summary`` collapses the wrap that the source line break introduced.
	"""
	if not lead:
		return body
	collapsed = " ".join(body.split())
	if not collapsed.startswith(lead):
		return body
	# Walk the original text consuming exactly as many non-space characters as the summary holds.
	remaining = len("".join(lead.split()))
	index = 0
	while remaining and index < len(body):
		if not body[index].isspace():
			remaining -= 1
		index += 1
	return body[index:].lstrip()


def render_sections(obj, site, from_dir: str, *, skip: tuple[str, ...] = (), drop_summary: bool = False) -> str:
	"""Render a griffe object's whole docstring to Markdown.

	``skip`` drops section kinds the page renders itself — a class page builds its Attributes table from
	real members (which have annotations and source links), so a hand-written ``Attributes:`` section in
	the docstring would only duplicate it. ``drop_summary`` removes the opening sentence, which the page has
	already printed as its abstract.
	"""
	if obj.docstring is None:
		return ""
	blocks: list[str] = []
	lead = summary(obj) if drop_summary else ""
	for section in obj.docstring.parsed:
		kind = section.kind.value
		if kind in skip:
			continue
		if kind == "text":
			# Demote hand-written headings: prose belongs to one symbol's block, so it must not put an
			# entry in the page outline that competes with the `##` symbol names the generator emits.
			text = markup.demote_headings(str(section.value).strip())
			if lead:
				text, lead = strip_summary(text, lead), ""
			blocks.append(text)
		elif kind == "returns":
			blocks.append(_returns(section, site, from_dir, "Returns"))
		elif kind == "yields":
			blocks.append(_returns(section, site, from_dir, "Yields"))
		elif kind == "receives":
			blocks.append(_returns(section, site, from_dir, "Receives"))
		elif kind == "raises" or kind == "warns":
			blocks.append(_raises(section, site, from_dir))
		elif kind == "attributes":
			blocks.append(_attributes(section, site, from_dir))
		elif kind == "examples":
			blocks.append(_examples(section))
		elif kind == "admonition":
			blocks.append(_admonition(section))
		else:
			blocks.append(_fallback(section))
	return "\n\n".join(b for b in blocks if b.strip())


def returns_entry(obj, site, from_dir: str) -> dict | None:
	"""The ``returns`` field for ``symbols.json``: the declared annotation plus the docstring's description."""
	annotation = annotation_text(obj.returns) if getattr(obj, "returns", None) is not None else ""
	description = ""
	if obj.docstring is not None:
		for section in obj.docstring.parsed:
			if section.kind.value in ("returns", "yields") and section.value:
				description = " ".join(str(section.value[0].description).split())
				if not annotation and section.value[0].annotation is not None:
					annotation = annotation_text(section.value[0].annotation)
				break
	if not annotation and not description:
		return None
	return {"annotation": annotation, "description": description}


def parameter_descriptions(obj) -> dict[str, str]:
	"""``parameter name -> description`` harvested from the docstring's ``Args:`` section (may be empty)."""
	out: dict[str, str] = {}
	if obj.docstring is None:
		return out
	for section in obj.docstring.parsed:
		if section.kind.value in ("parameters", "other parameters"):
			for param in section.value:
				out[param.name] = " ".join(str(param.description).split())
	return out

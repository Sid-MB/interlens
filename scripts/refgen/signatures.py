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

"""Signatures, annotations, and cross-links.

Two jobs that share one piece of machinery (griffe's annotation expressions):

*Signatures* — reconstructed from ``griffe`` parameters rather than from source text, so they normalise
formatting, survive multi-line ``def``s, and pick up ``.pyi`` stub overrides. A class's signature is its
name plus its ``__init__`` parameters, which is what mkdocstrings' ``merge_init_into_class`` used to show
and what a reader actually wants at the top of a class page. Dataclasses come free: griffe synthesises
their ``__init__`` from the fields.

*Cross-links* — an annotation is an ``Expr`` tree whose ``ExprName`` leaves carry a ``canonical_path``
(``interlens.stop.StopCondition``). :func:`annotation_markdown` walks those leaves and swaps in a relative
Markdown link whenever the path names something with a page, keeping the link text as the bare name.
Crucially this is only ever used in *tables*: Pandoc cannot put a link inside a fenced code block, so
:func:`annotation_text` (plain) is what feeds the ```` ```python ```` signature blocks, and the downstream
site re-links those itself from ``symbols.json``.

Defaults are griffe's own source text (``p.default`` is the literal snippet, e.g. ``Transcript()``), and
``p.default is None`` — not the *string* ``"None"`` — is what means "no default".
"""
from __future__ import annotations

import posixpath

from griffe import Class, ExprName, Function, Parameter, ParameterKind

WRAP_WIDTH = 90  #: signatures longer than this are exploded to one parameter per line in code blocks


def _param_text(param: Parameter, annotate: bool) -> str:
	"""One parameter as it appears inside the parentheses, including its ``*``/``**`` marker."""
	prefix = {ParameterKind.var_positional: "*", ParameterKind.var_keyword: "**"}.get(param.kind, "")
	out = f"{prefix}{param.name}"
	if annotate and param.annotation is not None:
		out += f": {annotation_text(param.annotation)}"
	if param.default is not None:
		# PEP 8: spaces around `=` only when the parameter carries an annotation.
		out += f" = {param.default}" if (annotate and param.annotation is not None) else f"={param.default}"
	return out


def public_parameters(params, *, drop_self: bool = False) -> list[Parameter]:
	"""The parameters a reader should see: ``self``/``cls`` optionally dropped, private ones always.

	Private parameters are not a hypothetical: ``@dataclass`` classes such as ``Conversation`` carry
	``_turns``/``_data``/``_seed`` fields that griffe faithfully synthesises into ``__init__``. They are
	private for the same reason the dot-modifiers exist (``conv.turns(4)`` is the supported spelling), so
	they are filtered here exactly as every other underscore-prefixed name is.
	"""
	items = [p for p in params if not p.name.startswith("_")]
	if drop_self and items and items[0].name in ("self", "cls"):
		items = items[1:]
	return items


def parameter_texts(params, *, drop_self: bool = False, annotate: bool = True) -> list[str]:
	"""All parameters as text, with the ``/`` and ``*`` separators PEP 570/3102 require inserted."""
	items = public_parameters(params, drop_self=drop_self)
	out: list[str] = []
	seen_positional_only = False
	star_needed = False
	for param in items:
		if param.kind is ParameterKind.positional_only:
			seen_positional_only = True
		else:
			if seen_positional_only:
				out.append("/")
				seen_positional_only = False
			if param.kind is ParameterKind.keyword_only and star_needed is False and not any(
				p.kind is ParameterKind.var_positional for p in items
			):
				out.append("*")
				star_needed = True
		out.append(_param_text(param, annotate))
	if seen_positional_only:
		out.append("/")
	return out


def signature(obj: Class | Function, *, drop_self: bool = False) -> str:
	"""Single-line signature without the ``def``/``class`` keyword — the form stored in ``symbols.json``.

	For a class this is ``Name(<__init__ params minus self>)``; for a function/method it is
	``name(<params>) -> <return annotation>`` with ``self`` kept, so the page reflects the real declaration.
	"""
	if isinstance(obj, Class):
		init = obj.members.get("__init__")
		params = parameter_texts(init.parameters, drop_self=True) if isinstance(init, Function) else []
		return f"{obj.name}({', '.join(params)})"
	params = parameter_texts(obj.parameters, drop_self=drop_self)
	returns = f" -> {annotation_text(obj.returns)}" if obj.returns is not None else ""
	return f"{obj.name}({', '.join(params)}){returns}"


def signature_block(obj: Class | Function) -> str:
	"""The fenced ```` ```python ```` signature block, wrapped one-parameter-per-line when it runs long."""
	one_line = signature(obj)
	if len(one_line) <= WRAP_WIDTH:
		return f"```python\n{one_line}\n```"
	head, _, tail = one_line.partition("(")
	body, _, close = tail.rpartition(")")
	params = _split_top_level(body)
	lines = "\n".join(f"\t{p}," for p in params)
	return f"```python\n{head}(\n{lines}\n){close}\n```"


def _split_top_level(text: str) -> list[str]:
	"""Split a parameter list on commas that are not nested inside brackets, braces, or quotes."""
	parts, depth, quote, current = [], 0, "", ""
	for ch in text:
		if quote:
			current += ch
			if ch == quote:
				quote = ""
			continue
		if ch in "\"'":
			quote = ch
		elif ch in "([{":
			depth += 1
		elif ch in ")]}":
			depth -= 1
		elif ch == "," and depth == 0:
			parts.append(current.strip())
			current = ""
			continue
		current += ch
	if current.strip():
		parts.append(current.strip())
	return parts


def annotation_text(annotation) -> str:
	"""An annotation as plain text (no links) — safe for fenced code blocks and JSON."""
	return "" if annotation is None else str(annotation)


def _canonical(name: ExprName) -> str | None:
	try:
		return name.canonical_path
	except Exception:  # unresolvable forward reference / third-party name; render it unlinked
		return None


def relative_link(target_page: str, from_dir: str) -> str:
	"""Relative Markdown href from a page living in ``from_dir`` to the page id ``target_page``."""
	return posixpath.relpath(f"{target_page}.md", start=from_dir)


def annotation_markdown(annotation, site, from_dir: str) -> str:
	"""An annotation rendered for a Markdown *table*, with interlens names linked to their pages.

	``annotation`` may be an ``Expr`` (from the signature) or a plain string (from a docstring's ``Args:``
	type column, which the Google parser hands back verbatim); strings are passed through as code.
	"""
	if annotation is None:
		return ""
	if isinstance(annotation, str):
		return f"`{annotation}`"
	out: list[str] = []
	linked = False
	for element in annotation.iterate(flat=True):
		if isinstance(element, ExprName):
			page = site.pages_by_path.get(_canonical(element) or "")
			if page:
				linked = True
				out.append(f"[{element.name}]({relative_link(page, from_dir)})")
				continue
			out.append(element.name)
		else:
			out.append(str(element))
	# Backticks and links cannot coexist (Pandoc renders code spans literally), so an annotation that has
	# nothing to link stays a clean code span, and one that does becomes plain text carrying the links.
	# `|` is escaped unconditionally: `str | None` inside a code span still splits a GFM table cell.
	rendered = "".join(out)
	return (f"`{rendered}`" if not linked else rendered).replace("|", "\\|")

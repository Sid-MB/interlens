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

"""Per-row templating for data-driven rollouts.

A `Conversation` run over a benchmark shares ONE recipe but needs a DIFFERENT scenario per dataset row. Any
templated string field on the conversation (``shared_context``, ``shared_system_prompt``) or its participants
(``system_prompt``, private context) may be a *template value* that is resolved against each row at rollout
expansion time (once, deterministically — so job *i* always maps to row *i* and resume stays correct).

A template value is any of:
  - a plain ``str`` — used as-is (no substitution);
  - ``dataset_field("question")`` — pulls ``row["question"]``;
  - a ``callable(row) -> str`` — arbitrary per-row computation;
  - a ``tuple``/``list`` of the above — resolved part-by-part and concatenated (the <3.14 way to interleave
    literal text with fields: ``("Solve:\\n\\n", dataset_field("question"))``);
  - a PEP 750 template string (``t"...{dataset_field('question')}..."``) on Python 3.14+ — interpolated
    ``DatasetField``s resolve from the row, everything else formats normally.

``resolve(value, row)`` performs the substitution; ``has_fields(value)`` reports whether a value depends on the
row at all (so a conversation with no data-dependent fields can be run directly, and one WITH them refuses to run
un-expanded — see ``Conversation``)."""
from __future__ import annotations

from dataclasses import dataclass

try:  # PEP 750 template strings (Python 3.14+); optional so the library runs on 3.11–3.13.
	from string.templatelib import Template as _Template, Interpolation as _Interpolation
except ImportError:  # pragma: no cover - version-dependent
	_Template = _Interpolation = None


@dataclass(frozen=True)
class DatasetField:
	"""A placeholder for ``row[name]`` in a templated field, created by :func:`dataset_field`. Frozen + tiny so it
	serializes and pickles trivially across a spawn boundary."""

	name: str


def dataset_field(name: str) -> DatasetField:
	"""Reference a dataset column in a templated field: ``shared_context=("Solve:\\n\\n", dataset_field("question"))``
	resolves ``row["question"]`` for each row at rollout expansion. See the module docstring for all template forms."""
	return DatasetField(name)


def has_fields(value) -> bool:
	"""Whether ``value`` depends on the dataset row (contains a ``DatasetField``, a callable, or a t-string). A
	conversation whose framing has no fields can be run directly; one that has them must be expanded over data."""
	if isinstance(value, DatasetField) or callable(value):
		return True
	if isinstance(value, (tuple, list)):
		return any(has_fields(v) for v in value)
	if _Template is not None and isinstance(value, _Template):
		return True
	return False


def resolve(value, row: dict):
	"""Resolve a template ``value`` against one dataset ``row`` (a mapping) to a concrete value.

	Non-templated values (plain ``str``/``None``/other) pass through unchanged; ``DatasetField`` → ``row[name]``;
	a callable → ``value(row)``; a tuple/list → each part resolved and string-joined; a t-string → interpolated
	with ``DatasetField`` interpolations pulled from the row."""
	if isinstance(value, DatasetField):
		return row[value.name]
	if _Template is not None and isinstance(value, _Template):
		return _resolve_template_string(value, row)
	if isinstance(value, (tuple, list)):
		return "".join(str(resolve(v, row)) for v in value)
	if callable(value):
		return value(row)
	return value


def _resolve_template_string(template, row: dict) -> str:  # pragma: no cover - 3.14+ only
	"""Render a PEP 750 t-string: literal segments verbatim, interpolations formatted — but an interpolation whose
	value is a ``DatasetField`` is pulled from the row first."""
	out: list[str] = []
	for part in template:
		if isinstance(part, str):
			out.append(part)
		else:  # Interpolation
			val = part.value
			val = row[val.name] if isinstance(val, DatasetField) else val
			out.append(format(val, part.format_spec) if part.format_spec else str(val))
	return "".join(out)

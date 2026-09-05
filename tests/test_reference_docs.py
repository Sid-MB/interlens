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

"""The committed API reference must match the source.

``docs/reference/`` is generated but *committed* (the published docs at https://sidmb.com/docs/interlens
are built by another repo that syncs this folder from git), which introduces exactly one failure mode the
old build-time pipeline did not have: the tree silently going stale after someone renames a class, moves a
module, or edits a docstring. This test closes that hole by regenerating into a temp dir and diffing
byte-for-byte — which also proves the generator is deterministic, since a byte-identical rerun is the whole
premise of the downstream content sync.

It is fast (a few seconds: one static griffe pass, no imports of interlens/torch) and skips itself when
griffe is not installed, so a bare ``pytest`` run in a torch-only environment is unaffected. When it fails,
the fix is always the same: rerun the generator and commit the diff.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMMITTED = ROOT / "docs" / "reference"

pytest.importorskip("griffe", reason="docs group not installed (pip install --group docs)")
sys.path.insert(0, str(ROOT / "scripts"))
from refgen import generate  # noqa: E402  (must follow the importorskip + sys.path setup)

REGENERATE = "uv run --with griffe --no-project python scripts/gen_ref_pages.py"


def _files(directory: Path) -> dict[str, bytes]:
	"""Every generated file under ``directory``, keyed by its path relative to the reference root."""
	return {
		path.relative_to(directory).as_posix(): path.read_bytes()
		for path in sorted(directory.rglob("*"))
		if path.is_file()
	}


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory) -> dict[str, bytes]:
	out = tmp_path_factory.mktemp("reference")
	generate(ROOT, out, splice_nav=False)  # never rewrite mkdocs.yml from a test
	return _files(out)


def test_reference_is_committed():
	assert COMMITTED.is_dir(), f"docs/reference/ is missing — run: {REGENERATE}"


def test_reference_matches_source(regenerated):
	"""Same set of pages, and identical bytes in each — no drift, and a deterministic generator."""
	committed = _files(COMMITTED)

	missing = sorted(set(regenerated) - set(committed))
	extra = sorted(set(committed) - set(regenerated))
	assert not missing, f"{len(missing)} page(s) missing from docs/reference/ (e.g. {missing[:5]}) — run: {REGENERATE}"
	assert not extra, f"{len(extra)} stale page(s) in docs/reference/ (e.g. {extra[:5]}) — run: {REGENERATE}"

	differing = sorted(name for name, body in regenerated.items() if committed[name] != body)
	assert not differing, f"{len(differing)} page(s) out of date (e.g. {differing[:5]}) — run: {REGENERATE}"

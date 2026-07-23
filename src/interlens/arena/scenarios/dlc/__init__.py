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

"""Task adapters for the distributed long-context scenario, ported from the RLM paper's benchmarks.

Each adapter defines one task's question format, answer parsing, and exact grading for
``DistributedLongContext``; ``interlens.arena.scenarios.dlc.build`` builds the corresponding instance banks
from the benchmarks' own sources (pinned revisions; no benchmark data ships in this repo).

- ``SniahAdapter`` — RULER-style single needle-in-a-haystack (exact match on the magic number).
- ``OolongPairsAdapter`` — OOLONG-Pairs pairwise aggregation (F1 over the emitted pair set; the task whose
  full enumeration models decline — see the ``capitulated`` outcome class).
- ``CodeQAAdapter`` — LongBench-v2 repo-understanding multiple choice (exact choice match).
- ``BCPAdapter`` — BrowseComp-Plus multi-hop QA. Grading is two-phase: the scenario records the submitted
  answer un-judged (``primary=0``, ``judged=False``); apply the official grader template
  (``bcp.GRADER_TEMPLATE``, pinned verbatim from the benchmark repo) with an LLM judge post-hoc.
"""

from .bcp import BCPAdapter, GRADER_TEMPLATE
from .codeqa import CodeQAAdapter
from .oolong_pairs import OolongPairsAdapter
from .sniah import SniahAdapter

ADAPTERS = {a.task: a for a in (SniahAdapter, OolongPairsAdapter, CodeQAAdapter, BCPAdapter)}


def dlc_scenario(task: str, name: str | None = None):
	"""A ``DistributedLongContext`` scenario for one task, e.g. ``dlc_scenario("sniah")``."""
	from ..longcontext import DistributedLongContext
	return DistributedLongContext(ADAPTERS[task](), name=name)


__all__ = ["SniahAdapter", "OolongPairsAdapter", "CodeQAAdapter", "BCPAdapter",
           "GRADER_TEMPLATE", "ADAPTERS", "dlc_scenario"]

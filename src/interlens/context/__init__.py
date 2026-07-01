# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from .context_policy import ContextPolicy
from .error_policy import ErrorPolicy
from .drop_oldest_policy import DropOldestPolicy
from .sliding_window_policy import SlidingWindowPolicy
from .summarize_policy import SummarizePolicy

# Registry for (de)serializing policies by ``kind`` (their class name), so templates round-trip.
_POLICIES = {c.__name__: c for c in (ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy)}


def context_policy_from_dict(data: dict) -> ContextPolicy:
	params = {k: v for k, v in data.items() if k != "kind"}
	return _POLICIES[data["kind"]](**params)


__all__ = [
	"ContextPolicy",
	"ErrorPolicy",
	"DropOldestPolicy",
	"SlidingWindowPolicy",
	"SummarizePolicy",
	"context_policy_from_dict",
]

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

from .devices import available_devices
from .spec import ConversationSpec
from .pool import run_conversations, RunResult, RunReport
from .rollout import rollout
from .analyzer_registry import register_analyzer, resolve_analyzer
from .worker_init import register_worker_init, run_worker_init

__all__ = [
	"available_devices",
	"ConversationSpec",
	"run_conversations",
	"RunResult",
	"RunReport",
	"rollout",
	"register_analyzer",
	"resolve_analyzer",
	"register_worker_init",
	"run_worker_init",
]

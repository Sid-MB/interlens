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

"""Pluggable communication topologies: who speaks next, and who sees what. See ``policy.py``."""

from .policy import CommunicationPolicy, DirectPipingPolicy, RoundRobinPolicy
from .messaging import Mail, MessagingPolicy, ReadMessageTool, SendMessageTool, parse_json_actions

__all__ = [
	"CommunicationPolicy",
	"RoundRobinPolicy",
	"DirectPipingPolicy",
	"MessagingPolicy",
	"Mail",
	"SendMessageTool",
	"ReadMessageTool",
	"parse_json_actions",
]

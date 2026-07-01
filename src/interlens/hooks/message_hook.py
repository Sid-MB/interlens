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

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..message import Message
	from ..conversation import Conversation


class HookAction(str, Enum):
	APPROVE = "approve"  # let the message through unchanged
	DENY = "deny"        # drop the turn (it is not committed)
	EDIT = "edit"        # replace the message with a provided one


@dataclass
class MessageHookResult:
	action: HookAction
	message: "Message | None" = None  # the replacement, for EDIT

	@classmethod
	def approve(cls) -> "MessageHookResult":
		return cls(HookAction.APPROVE)

	@classmethod
	def deny(cls) -> "MessageHookResult":
		return cls(HookAction.DENY)

	@classmethod
	def edit(cls, message) -> "MessageHookResult":
		return cls(HookAction.EDIT, message)


class MessageHook(ABC):
	"""Middleware that inspects each freshly generated message *before* it is committed to the transcript, and
	may approve / deny / edit it.

	This is the seam for a future LLM-judge that vets or rewrites turns (e.g. safety filtering, format
	enforcement). Hooks live on the live ``Conversation`` (``conversation.message_hooks``) and are NOT serialized
	in the template — they're a runtime policy, not part of the scenario recipe. The default is an empty hook
	list, i.e. today's pass-through behavior.
	"""

	@abstractmethod
	def review(self, message: "Message", conversation: "Conversation") -> MessageHookResult:
		...

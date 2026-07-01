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

from dataclasses import dataclass

from ..template import ConversationTemplate


@dataclass
class ConversationSpec:
	"""A unit of work for the runner: a fully-serializable ``ConversationTemplate`` + a ``job_id`` + turn count.

	Being serializable is what lets a spec cross the process boundary to a spawned GPU worker. ``job_id`` keys
	results and the on-disk checkpoint directory, so a resumed run can tell which specs are already done.
	"""

	template: ConversationTemplate
	job_id: str
	turns: int | None = None

	def to_dict(self) -> dict:
		return {"template": self.template.to_dict(), "job_id": self.job_id, "turns": self.turns}

	@classmethod
	def from_dict(cls, data: dict) -> "ConversationSpec":
		return cls(template=ConversationTemplate.from_dict(data["template"]),
		           job_id=data["job_id"], turns=data.get("turns"))

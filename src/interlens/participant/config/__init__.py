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

from .participant_config import ParticipantConfig, participant_config_from_dict
from .model_participant_config import ModelParticipantConfig
from .api_participant_config import APIParticipantConfig

__all__ = [
	"ParticipantConfig",
	"participant_config_from_dict",
	"ModelParticipantConfig",
	"APIParticipantConfig",
]

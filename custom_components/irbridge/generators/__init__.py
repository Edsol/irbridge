# IRBridge - generate IR codes on-the-fly for climate devices in Home Assistant
# Copyright (C) 2026 Edoardo Soloperto
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from .base import ClimateCapabilities, ClimateGenerator
from .gree_climate import GreeClimateGenerator
from .electra_climate import ElectraClimateGenerator

_REGISTRY: dict[str, type[ClimateGenerator]] = {
    "gree": GreeClimateGenerator,
    "electra": ElectraClimateGenerator,
}


def get_generator(protocol: str) -> ClimateGenerator:
    """Return a ClimateGenerator instance for the given protocol key.

    Raises KeyError if the protocol is not registered.
    """
    cls = _REGISTRY[protocol]
    return cls()


def available_protocols() -> list[str]:
    return list(_REGISTRY.keys())

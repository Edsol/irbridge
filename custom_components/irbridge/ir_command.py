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

"""Adapter: IRBridge raw timings -> infrared_protocols.Command.

HA 2026.4+ ships an ``infrared`` platform whose emitters (ESPHome, Tuya
Local, Broadlink, SMLIGHT, and ``mqtt.infrared`` since 2026.7) all accept
the same object: an ``infrared_protocols.Command``. Its contract is a
carrier frequency plus ``get_raw_timings()`` returning SIGNED microseconds
(positive = mark, negative = space).

IRBridge generators emit unsigned alternating mark/space, so this module
signs them and adds the trailing terminator the wire needs.
"""
from __future__ import annotations

try:
    from infrared_protocols import Command
except ImportError:  # test environment without infrared_protocols
    import abc

    class Command(abc.ABC):  # type: ignore[no-redef]
        """Minimal stand-in mirroring the infrared_protocols contract."""

        modulation: int
        repeat_count: int

        def __init__(self, *, modulation: int, repeat_count: int = 0) -> None:
            self.modulation = modulation
            self.repeat_count = repeat_count

        @abc.abstractmethod
        def get_raw_timings(self) -> list[int]:
            """Signed microsecond timings (positive=mark, negative=space)."""


# Two hardware constraints meet at the emitter, and they pull opposite ways:
# 16-bit blasters (Tuya/ZoSung behind Zigbee2MQTT) reject any timing above
# 65535us, while Broadlink RM4 Pro firmware garbles a stream that does not
# END on a space. A bounded terminator satisfies both -- 50ms fits uint16
# with margin and is dead air to any receiver.
TERMINATOR_SPACE_US = 50_000

DEFAULT_FREQUENCY = 38000


def to_signed(raw: list[int]) -> list[int]:
    """Convert unsigned alternating mark/space to the signed convention.

    Even index = mark (positive), odd index = space (negative). Input that
    is already signed passes through unchanged, since only the sign is
    rewritten and never the magnitude.
    """
    return [
        abs(value) if index % 2 == 0 else -abs(value)
        for index, value in enumerate(raw)
    ]


def normalize_trailing_space(timings: list[int]) -> None:
    """End the array on a bounded space, in place.

    Oversized trailing space -> clamped. Ends on a mark -> a terminator is
    appended. A small trailing space passes untouched.
    """
    if not timings:
        return
    if timings[-1] < 0:
        if -timings[-1] > TERMINATOR_SPACE_US:
            timings[-1] = -TERMINATOR_SPACE_US
        return
    timings.append(-TERMINATOR_SPACE_US)


class RawTimingsCommand(Command):
    """Wraps generated raw timings for the HA infrared platform."""

    def __init__(
        self,
        raw: list[int],
        *,
        frequency: int = DEFAULT_FREQUENCY,
        repeat_count: int = 0,
    ) -> None:
        if not raw:
            raise ValueError("Cannot build an IR command from empty timings")
        timings = to_signed(raw)
        normalize_trailing_space(timings)
        self._timings = timings
        super().__init__(modulation=frequency, repeat_count=repeat_count)

    def get_raw_timings(self) -> list[int]:
        """Signed microsecond timings (positive=mark, negative=space)."""
        return list(self._timings)

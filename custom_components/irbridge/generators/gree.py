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

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Edoardo Soloperto
"""Gree 8-byte IR state encoder for the device previously labelled midea_camera.

Protocol field reference: IRremoteESP8266 ir_Gree.h / ir_Gree.cpp and
ir_Kelvinator.cpp. This implementation builds states directly from the wire
format; it has no dependency on IRremoteESP8266 or Arduino.

The fixed bytes match the tested device (Gree ModelA power bit). Other Gree
models are not automatically covered. See the protocol notes for validation.
"""

from __future__ import annotations

TEMP_MIN = 16
TEMP_MAX = 30
_MODES = {"auto": 0, "cool": 1, "dry": 2, "fan": 3, "fan_only": 3, "heat": 4}
_FANS = {"auto": 0, "low": 1, "mid": 2, "high": 3}


def generate_state(
    mode: str, temp: int, fan: str = "auto", *, power: bool = True,
    swing_v: bool = False,
) -> bytes:
    """Build eight logical bytes, transmitted least significant bit first.

    Auto mode fixes temperature at 25 C; dry mode fixes fan speed at low.
    Off retains the supplied mode/temperature and clears both power bits.
    """
    if mode not in _MODES:
        raise ValueError(f"Unsupported Gree mode: {mode!r}")
    if fan not in _FANS:
        raise ValueError(f"Unsupported Gree fan speed: {fan!r}")
    if isinstance(temp, bool) or not isinstance(temp, int) or not TEMP_MIN <= temp <= TEMP_MAX:
        raise ValueError(f"Gree temperature must be an integer from {TEMP_MIN} to {TEMP_MAX} C")
    temperature = 25 if mode == "auto" else temp
    speed = _FANS["low"] if mode == "dry" else _FANS[fan]
    state = bytearray(8)
    state[0] = _MODES[mode] | (int(power) << 3) | (speed << 4) | (int(swing_v) << 6)
    state[1] = temperature - TEMP_MIN
    state[2] = 0x20 | (0x40 if power else 0)  # Light on; ModelA follows power.
    state[3] = 0x50
    state[4] = 1 if swing_v else 0  # Automatic vertical swing / last position.
    state[5] = 0x20
    # Checksum: low nibbles of bytes 0-3, high nibbles of 4-6, plus 10.
    nibbles = [value & 15 for value in state[:4]] + [value >> 4 for value in state[4:7]]
    state[7] = ((sum(nibbles) + 10) % 16) << 4
    return bytes(state)


def generate_raw(
    mode: str, temp: int, fan: str = "auto", *, power: bool = True,
    swing_v: bool = False,
) -> list[int]:
    """Return mark/space durations in microseconds for a 38 kHz emitter."""
    state = generate_state(mode, temp, fan, power=power, swing_v=swing_v)
    raw = [9000, 4500]
    for index, value in enumerate(state):
        for bit in range(8):
            raw.extend((620, 1600 if value & (1 << bit) else 540))
        if index == 3:
            for bit in (0, 1, 0):
                raw.extend((620, 1600 if bit else 540))
            raw.extend((620, 19980))
    raw.append(620)
    return raw

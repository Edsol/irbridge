# Gree protocol: identification and device verification

The remote stored as `midea_camera` uses a Gree-compatible 8-byte protocol.
The old `midea` generator is retained unchanged for compatibility; its name
and several state interpretations are historical, not a Midea protocol claim.

## Evidence (2026-09-06)

All 51 stored `midea_camera` samples with two four-byte blocks passed the
Gree/Kelvinator nibble checksum after reversing each `bytes_msb` byte into
logical LSB-first representation. This establishes structural agreement;
field meanings were then tested on the physical device over MQTT.

| Logical bytes (LSB-first on the wire) | Requested state | User observation |
|---|---|---|
| `19 08 60 50 00 20 00 D0` | On, cool, 24 C, low fan, swing off | On, cool and 24 C confirmed; fan probably low |
| `79 08 60 50 01 20 00 D0` | On, cool, 24 C, high fan, automatic vertical swing | Expected behavior confirmed |

Exact raw timings and Tuya payloads are retained in the regression fixtures.
The original captures and their labels are preserved, not rewritten.

## Wire format and fields

- Header: 9000 / 4500 microseconds.
- Eight bytes, each transmitted LSB first.
- After byte 3: three bits `010`, a final mark and a roughly 20 ms gap.
- Bit mark: 620 us; zero/one spaces: 540/1600 us; carrier: 38 kHz.
- Byte 0: mode in bits 0-2, power in bit 3, fan in bits 4-5,
  automatic swing in bit 6.
- Byte 1: temperature minus 16 in the low nibble.
- Byte 2: light enabled; ModelA bit follows power for this device profile.
- Byte 3: `50`; byte 5: `20`; byte 6: `00`.
- Byte 4: vertical swing, `01` automatic or `00` last position.
- Byte 7 high nibble: sum of low nibbles of bytes 0-3, high nibbles of
  bytes 4-6, plus 10, modulo 16.

Modes: auto=0, cool=1, dry=2, fan=3, heat=4.
Fan: auto=0, low=1, mid=2, high=3.
Auto mode uses 25 C; dry mode forces low fan, following the reference profile.

## Corrections to the historical analysis

The former MSB byte-0 bit 4 maps to the Gree power bit, not a rolling counter.
The historical `cool_22` generator produces a temperature field of 7, meaning
23 C under Gree. Historical `auto` and `fan` mode interpretations are swapped.
The second block's final nibble is a checksum, not an independent empirical
mode/temperature formula. Historical fan labels also need revalidation.

The old sweep labels therefore cannot be treated as independently verified
physical temperature/mode measurements. Keep them as acquisition history.

## Scope and remaining checks

Implemented: 16-30 C, off/cool/heat/dry/fan/auto, auto/low/mid/high fan,
and vertical swing. Only the two states above have been tested under the
corrected interpretation. Off, heat, dry, fan-only, auto, medium/automatic fan,
other temperatures and swing-off after swing-on still need device checks.
The exact remote model is not established; this profile does not promise
compatibility with every Gree or Midea-branded unit.

## References

Protocol field descriptions and timing/checksum reference:

- [IRremoteESP8266 ir_Gree.h](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Gree.h)
- [IRremoteESP8266 ir_Gree.cpp](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Gree.cpp)
- [IRremoteESP8266 ir_Kelvinator.cpp](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Kelvinator.cpp)

The Python encoder is implemented from these protocol facts and the verified
wire messages, without an Arduino or IRremoteESP8266 runtime dependency.

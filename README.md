# IRBridge

A Home Assistant custom integration that generates IR codes on-the-fly for climate devices, without relying on pre-recorded code databases.

## How it works

IRBridge implements protocol-specific IR code generators in Python. When you change the temperature or mode in Home Assistant, the integration generates the exact IR signal for your device and transmits it via your IR blaster.

```
HA Climate Entity
      ↓
ClimateGenerator (protocol-specific)
      ↓
Raw IR timings (microseconds)
      ↓
IRSender (mqtt_tuya / infrared_entity)
      ↓
IR Blaster → device
```

No cloud, no database, no pre-recorded codes.

## Supported protocols

| Protocol | Devices | Temp | Fan | Swing | Power off |
|----------|---------|------|-----|-------|-----------|
| `midea` | Ferroli, Midea | 16–30°C | auto | — | ✓ |
| `electra` | Beko, AUX, Electrolux, Frigidaire | 16–32°C | auto/high/mid/low | vertical | ✓ |

## Supported senders

| Sender | Description |
|--------|-------------|
| `mqtt_tuya` | Zigbee2MQTT IR blaster (Tuya ZS05, etc.) via MQTT |
| `infrared_entity` | HA native `InfraredEmitterEntity` (ESPHome, future) |

## Installation

1. Copy `custom_components/irbridge` into your HA `custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → IRBridge**.
4. Select protocol, sender, and your IR blaster entity.

## Configuration

The config flow guides you through:

1. **Title** — name for the climate entity (e.g. "Living Room AC")
2. **Protocol** — select the protocol matching your device
3. **Sender** — how to transmit IR signals
4. **Blaster entity** — the `text.*_ir_code_to_send` entity from Zigbee2MQTT

You can reconfigure at any time via **Settings → Devices & Services → IRBridge → Configure**.

## Adding a new protocol

1. Create `generators/<name>.py` with the raw IR generation logic.
2. Create `generators/<name>_climate.py` implementing `ClimateGenerator`:

```python
from .base import ClimateCapabilities, ClimateGenerator
from . import myprotocol

class MyProtocolClimateGenerator(ClimateGenerator):

    @property
    def capabilities(self) -> ClimateCapabilities:
        return ClimateCapabilities(
            temp_min=16,
            temp_max=30,
            fan_modes=["auto", "high", "low"],
            swing_modes=["off", "vertical"],
            hvac_modes=["off", "cool", "heat", "dry", "fan_only", "auto"],
        )

    def generate(self, hvac_mode, temp, fan_mode="auto", swing_mode="off") -> list[int]:
        ...
```

3. Register it in `generators/__init__.py`:

```python
from .myprotocol_climate import MyProtocolClimateGenerator

_REGISTRY: dict[str, type[ClimateGenerator]] = {
    ...
    "myprotocol": MyProtocolClimateGenerator,
}
```

The new protocol appears automatically in the config flow — no other changes needed.

## Project structure

```
irbridge/
└── custom_components/
    └── irbridge/
        ├── __init__.py              # HA entry setup/unload
        ├── manifest.json
        ├── const.py
        ├── config_flow.py           # Setup wizard + options flow
        ├── climate.py               # Protocol-agnostic ClimateEntity
        ├── tuya_codec.py            # Tuya base64 encoder/decoder
        ├── errors.py
        ├── generators/
        │   ├── __init__.py          # Registry: get_generator(), available_protocols()
        │   ├── base.py              # ClimateGenerator ABC + ClimateCapabilities
        │   ├── midea.py             # Midea/Ferroli raw IR generator
        │   ├── midea_climate.py     # Midea ClimateGenerator implementation
        │   ├── electra.py           # Electra/AUX/Beko raw IR generator
        │   └── electra_climate.py   # Electra ClimateGenerator implementation
        └── senders/
            ├── base.py              # IRSender ABC
            ├── mqtt_tuya.py         # MQTT Tuya sender (Zigbee2MQTT)
            └── infrared_entity.py   # HA InfraredEmitterEntity sender (future)
```

## Relationship with ir-lab

IRBridge is developed alongside [ir-lab](../README.md), a research tool for capturing, analyzing and reverse-engineering IR protocols. Protocols are first reverse-engineered in ir-lab using a Zigbee2MQTT IR blaster, then the verified generators are ported to IRBridge.

## Remote entity

Each configured device also exposes a `remote` entity, compatible with [universal-remote-card](https://github.com/Nerwyn/universal-remote-card).

Commands are generated on-the-fly using the same IR generators. Format:

| Command | Example | Description |
|---------|---------|-------------|
| `off` | `off` | Power off |
| `<mode>` | `cool`, `heat` | Mode at current temp |
| `<mode>_<temp>` | `cool_22`, `heat_20` | Mode + temperature |
| `<mode>_<temp>_<fan>` | `cool_22_high` | Mode + temp + fan speed |
| `swing_on` / `swing_off` | `swing_on` | Swing (applied on next command) |

Example universal-remote-card button:
```yaml
service: remote.send_command
data:
  command: cool_22
```

## Roadmap

- [ ] More protocols (LG, Daikin, Samsung, Panasonic, ...)
- [ ] Tuya Cloud fallback for unknown brands
- [ ] IRremoteESP8266 wrapper for broad offline coverage
- [ ] HA native `InfraredEmitterEntity` support (Zigbee2MQTT bridge)
- [ ] Midea swing support (requires sample acquisition)
- [ ] HACS distribution

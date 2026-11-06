<p align="center">
  <img src="custom_components/irbridge/brand/icon@2x.png" alt="IRBridge" width="120">
</p>

# IRBridge

[![Validate](https://github.com/Edsol/irbridge/actions/workflows/validate.yaml/badge.svg)](https://github.com/Edsol/irbridge/actions/workflows/validate.yaml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/Edsol/irbridge?include_prereleases&sort=semver)](https://github.com/Edsol/irbridge/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-custom%20integration-41BDF5.svg?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)

**Your air conditioner in Home Assistant. IR codes generated on demand.**

IRBridge turns a compatible IR-controlled air conditioner into a Home Assistant
climate entity. Choose a temperature, mode or fan speed, and IRBridge calculates
the command and sends it through your IR blaster.

There is no need to record a separate code for every temperature and mode:
supported commands are generated locally from the device's protocol.

## What you get

- **Climate controls** for dashboards and automations, with the temperature
  range, fan modes and swing options supported by your selected protocol.
- **A remote entity** for sending commands such as `cool_22` from scripts or
  remote cards.
- **Setup through the UI:** name your device, choose its protocol and select
  an IR emitter.
- **Local code generation**, with no cloud account or downloaded code database
  required by IRBridge.

For example, selecting **Cool · 22 °C** generates the corresponding IR message
and sends it through the emitter you configured. Changing to 23 °C generates a
new message immediately; no learning session is needed.

## Before you install

- **Home Assistant 2026.7 or newer** — the version that added the `infrared`
  platform to MQTT. The platform itself landed in 2026.4, so an ESPHome or
  SMLIGHT emitter works from there.
- **An IR emitter already configured in Home Assistant**, exposed as an
  `infrared.*` entity. Configure the blaster's own integration first.
- **Zigbee2MQTT 2.13.0 or newer**, if your blaster is a Tuya/Zosung one behind
  Zigbee2MQTT. Earlier versions expose it only as `text.*_ir_code_to_send`,
  which the setup selector cannot see. 2.13.0 added both the infrared discovery
  and the timings-to-Tuya conversion the emitter needs.
- **An air conditioner using one of the supported protocols below**, with the
  blaster positioned so its IR signal can reach the unit.

## Supported protocols

| Protocol | Devices | Temp | Fan | Swing | Power off |
|----------|---------|------|-----|-------|-----------|
| `gree` | Tested device formerly labelled `midea_camera` | 16–30°C | auto/low/mid/high | vertical | ✓ |
| `electra` | Beko, AUX, Electrolux, Frigidaire | 16–32°C | auto/high/mid/low | vertical | ✓ |

Brand names identify protocol families, not a guarantee that every model from
that brand is compatible. The Gree protocol was first verified against the
lab's MQTT blaster, which checks the generated IR payload, and then confirmed
on the air conditioner itself through this integration: modes, temperatures,
fan speeds, swing and power off all behave as generated.
See [the Gree findings](docs/protocol_gree.md).

### Finding the right protocol

Setup asks how you would like to find it:

**Guided** — you do not choose at all. IRBridge sends a test command with the
first protocol, asks whether the air conditioner reacted, and moves to the
next one if it did not. Keep answering until something works.

**Expert** — you pick from the list, labelled with the brands each protocol
covers, and test that one.

Either way a real command is transmitted — cooling at 22 °C — and nothing is
saved until you confirm the unit reacted. This matters because a brand name
does not identify a protocol: the device this integration was first built
against is sold as Midea and turned out to speak Gree. Reconfiguring an
existing device runs the same check, so a wrong guess never replaces a setup
that already works.

### If you configured a device as "Midea"

Earlier versions offered a `midea` protocol. That name never described the
Midea protocol: it was the first, partly wrong reading of a Gree-compatible
unit, and the device it was built against is sold as Midea while speaking
Gree. It has been removed.

Existing entries are migrated automatically on upgrade — they become `gree`,
keeping their name and emitter, and gain the fan and swing controls the old
mapping lacked. Nothing to do by hand. If your unit is genuinely a Midea that
the Gree generator does not drive, please
[open an issue](https://github.com/Edsol/irbridge/issues) with a capture: real
Midea support would need a protocol reverse-engineered from samples, which is
what [ir-lab](https://github.com/Edsol/ir-lab) is for.

IRBridge sends through Home Assistant's native `infrared` platform. The setup
selector lists `infrared` entities; a blaster exposed only as a `remote` entity
cannot be selected directly.

## Installation

### Via HACS (recommended)

IRBridge is not yet in the default HACS store, so it must be added as a custom repository.

**One-click:** click the button below to open the custom-repository dialog in your Home Assistant directly:

[![Open your Home Assistant instance and add a HACS custom repository.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Edsol&repository=irbridge&category=integration)

**Manual:**

1. Open **HACS** in Home Assistant.
2. Click the **⋮** menu (top right) → **Custom repositories**.
3. Add the URL `https://github.com/Edsol/irbridge`, category **Integration**, then **Add**.
4. Search for **IRBridge** in HACS and click **Download**.
5. **Restart Home Assistant.**

### Manual installation (without HACS)

1. Copy the `custom_components/irbridge` folder from this repo into your HA `config/custom_components/` directory:
   ```
   config/custom_components/irbridge/
   ```
2. **Restart Home Assistant.**

### Add the integration

After installing (either method) and restarting:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **IRBridge**.
3. Enter a name, select your device protocol, and choose your `infrared` emitter.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=irbridge)

## Configuration

The config flow guides you through:

1. **Title** — name for the climate entity (e.g. "Living Room AC")
2. **Protocol** — select the protocol matching your device
3. **IR emitter** — an emitter entity from the `infrared` platform

You can reconfigure at any time via **Settings → Devices & Services → IRBridge → Configure**.

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

For a script action, replace the entity ID below with your IRBridge remote:

```yaml
action: remote.send_command
target:
  entity_id: remote.living_room_ac_remote
data:
  command: cool_22
```

Use temperatures and fan modes supported by your selected protocol. A mode-only
command uses the remote entity's remembered temperature and the default fan
speed.

## How it works

IRBridge translates the requested climate state into raw IR timings using a
protocol-specific `ClimateGenerator`. Its sender wraps those timings in a
`RawTimingsCommand` and passes the command to Home Assistant's native
`infrared.async_send_command` API, which handles transmission through the
configured emitter.

IR is one-way: the entity cannot read the unit back, so its state is what it
last transmitted. That state (mode, target temperature, fan, swing and the last
active mode used by `turn_on`) is restored after a Home Assistant restart
**without transmitting anything**. If the unit was operated with its original
remote in the meantime, the entity shows the old state until its next command.

## Troubleshooting

- **No emitter in the setup selector:** check that the blaster's integration
  provides an `infrared.*` entity and that you are running the required Home
  Assistant version.
- **The command is sent but the AC does not react:** check emitter placement
  and protocol compatibility. A shared brand name alone does not establish a
  protocol match.
- **A fan or swing option is missing:** available controls come from the
  selected generator's capabilities; see the protocol table above.

## Adding a new protocol

Paths below are relative to `custom_components/irbridge/`.

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
            frequency=38000,  # carrier in Hz; omit unless the protocol differs
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
        ├── remote.py                # Generated commands for scripts and cards
        ├── ir_command.py            # Raw timings -> infrared_protocols.Command
        ├── errors.py
        ├── generators/
        │   ├── __init__.py          # Registry: get_generator(), available_protocols()
        │   ├── base.py              # ClimateGenerator ABC + ClimateCapabilities
        │   ├── gree.py              # Gree raw IR generator
        │   ├── gree_climate.py      # Gree climate capabilities
        │   ├── electra.py           # Electra/AUX/Beko raw IR generator
        │   └── electra_climate.py   # Electra ClimateGenerator implementation
        └── senders/
            ├── __init__.py          # build_sender() factory
            ├── base.py              # IRSender ABC
            └── infrared_entity.py   # HA native infrared platform sender
```

## Relationship with ir-lab

IRBridge is developed alongside [ir-lab](https://github.com/Edsol/ir-lab), a research tool for capturing, analyzing and reverse-engineering IR protocols. Protocols are first reverse-engineered in ir-lab using a Zigbee2MQTT IR blaster, then the verified generators are ported to IRBridge.

## Roadmap

- [ ] More protocols (LG, Daikin, Samsung, Panasonic, ...)
- [ ] Tuya Cloud fallback for unknown brands
- [ ] IRremoteESP8266 wrapper for broad offline coverage
- [x] HA native `infrared` platform support
- [x] Gree fan and vertical swing generation, verified on the device
- [ ] Inclusion in the default HACS store

## License

GPL-3.0-or-later — see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

Releases up to 0.4.0 were MIT; from 0.5.0 IRBridge is GPL. You may still sell
a product built on it, but a derivative you distribute has to come with its
source under the same terms. See [NOTICE.md](NOTICE.md) for the reasoning and
for how protocol specifications are treated.

## Publishing a release

The `Release` workflow runs when a tag starting with `v` is pushed. It runs the
same generator tests, HACS and Hassfest checks as the validation workflow, then
requires the tag to match `custom_components/irbridge/manifest.json` exactly
(`v` plus `version`). It publishes a GitHub Release with generated release notes
and an `irbridge.zip` asset. No additional token secret is required.

To release, update and commit the manifest version, push that commit, then tag
it and push the tag. For example, **after setting the version to `0.3.0`**:

```bash
git tag -a v0.3.0 -m "IRBridge 0.3.0"
git push origin v0.3.0
```

Versions such as `0.3.0rc1` (tag `v0.3.0rc1`) are marked as prereleases.
The ZIP contains the integration files at its root: for manual installation,
extract it into `config/custom_components/irbridge/`, then restart Home Assistant.
HACS continues to install from the tagged repository using the existing layout.

# IRBridge — Agent Instructions

## License

GPL-3.0-or-later since 0.5.0 (MIT up to 0.4.0). Every source file carries the
GPL header; new files must too. The change was deliberate: a derivative must
not be closed and sold. Because GPL-3.0 is compatible with LGPL-2.1, protocol
code may be adapted from IRremoteESP8266 with attribution in the file — see
[NOTICE.md](NOTICE.md).

## What this is

A Home Assistant custom integration that generates IR codes on-the-fly for climate devices. No pre-recorded code databases — codes are computed from protocol specs.

Developed alongside `../ir-lab`, which is the research tool used to reverse-engineer IR protocols. Raw generators are verified in ir-lab first, then ported here.

## Architecture

### Adding a protocol

Three steps only:

1. `generators/<name>.py` — raw IR generation logic (ported from ir-lab)
2. `generators/<name>_climate.py` — implement `ClimateGenerator` ABC from `base.py`
3. `generators/__init__.py` — add one entry to `_REGISTRY`

Declare `brands` in the capabilities: it is what the setup picker shows, and
a protocol without it appears as a bare name nobody can match to their unit.

`climate.py` and `config_flow.py` require **no changes** — the new protocol appears automatically.

### Key files

| File | Role |
|------|------|
| `climate.py` | Protocol-agnostic `ClimateEntity` — reads capabilities from generator |
| `generators/base.py` | `ClimateGenerator` ABC and `ClimateCapabilities` dataclass |
| `generators/__init__.py` | Registry — single source of truth for available protocols |
| `senders/base.py` | `IRSender` ABC — implement to add new transmission backends |
| `config_flow.py` | Setup wizard + options flow (protocol, emitter, test step) |
| `strings.json` | Flow text HA actually reads; `translations/en.json` is its copy |

### Sender abstraction

`IRSender.async_send_raw(raw: list[int])` is the only method. There is a single
sender: `InfraredEntitySender`, which hands the command to HA's native
`infrared` platform. That platform already covers ESPHome, Broadlink, Tuya
Local, SMLIGHT and MQTT, so a new backend is HA's job rather than this
integration's.

### Flow text

Home Assistant resolves flow labels from `strings.json` in the component
root, and uses `translations/<lang>.json` only for translated locales. A step
missing from `strings.json` does not error — it renders its raw keys, so a
question shows up as `worked`. Keep `translations/en.json` an exact copy of
`strings.json`; `tests/test_strings.py` checks every step, field, error and
abort the flow references, and that the two files have not drifted.

### Entry migration

`async_migrate_entry` in `__init__.py` upgrades stored entries; `VERSION` in
`config_flow.py` is the current schema. Version 2 retired the `midea`
protocol name, renaming those entries to `gree`. Retiring or renaming a
protocol again means adding it to `_RENAMED_PROTOCOLS` and bumping `VERSION`,
or existing entries raise KeyError at setup and take the integration down.

### Setup wizard

Three steps, sharing the try-it-and-see machinery in `_TestMixin`:

1. **user** — name, blaster, and the choice between *guided* and *expert*.
   Explains what a protocol is and that a test signal will be transmitted.
2. **protocol** (expert only) — the picker, labelled with the brands from
   `ClimateCapabilities.brands`.
3. **test** — sends `cool` / 22 °C and asks whether the unit reacted.
   Guided mode walks the registry in order, skipping what was rejected;
   expert mode returns to the picker. Nothing is stored until a yes.

`TEST_HVAC_MODE` and `TEST_TEMP` must stay legal for every registered
protocol, and every protocol must declare `brands` or it shows up unlabelled.
`tests/test_config_flow.py` enforces both, plus the guided walk.

### Options flow

Changing protocol/emitter goes through the same test step, and the entry is
only rewritten once the user confirms — a wrong guess never replaces a working
setup. On confirmation `_async_update_listener` reloads the entry, so new
capabilities (fan modes, swing, temp range) take effect immediately.

## Development setup

The `custom_components/irbridge` folder is symlinked into the HA Docker dev instance:

```
~/Personale/Progetti/home assistant docker/custom_components/irbridge
  → /Users/edoardosoloperto/Downloads/ir-lab/irbridge/custom_components/irbridge
```

Changes here are live — restart the HA container to reload:
```bash
cd ~/Personale/Progetti/home\ assistant\ docker
docker compose restart homeassistant-dev
```

Or `docker compose up -d` if docker-compose.yaml was changed.

## Verified protocols

### Gree (`gree`)
- The device formerly stored as `midea_camera`: sold as Midea, speaks Gree
- Fan: auto/low/mid/high — Swing: vertical — 16-30 °C
- Verified on the unit through this integration: modes, temperatures, fan
  speeds, swing and power off

### Electra (`electra`)
- Devices: Beko (YKR-H/102E), AUX, Electrolux, Frigidaire
- Protocol: IRremoteESP8266 `ir_Electra.h` confirmed via sample analysis
- 13-byte frame, checksum = sum(logical bytes 0–11) & 0xFF
- Dry mode forces fan=low (protocol spec)
- Heat mode sets bit4 of B9 (Beko UseFahrenheit quirk)
- Swing vertical supported

## Current limitations

- Tuya Cloud fallback not yet integrated
- Requires HA 2026.7+, and Zigbee2MQTT 2.13.0+ for Tuya/Zosung blasters

## Remote entity

`remote.py` exposes an `IRBridgeRemote` entity alongside the climate entity. It accepts command strings and generates IR on-the-fly using the same generator.

Command parsing in `_parse_and_generate()`:
- `"off"` → power off
- `"cool_22"` → mode + temp
- `"cool_22_high"` → mode + temp + fan
- `"swing_on"` / `"swing_off"` → sets swing state for next command (stateful)

The `extra_state_attributes` exposes `supported_commands` — a full list of valid commands for the device, useful for card configuration.

## Do not

- Hardcode IR codes in `climate.py` — they belong in the generator
- Add protocol-specific logic to `climate.py` — it must stay protocol-agnostic
- Modify `climate.py` or `config_flow.py` when adding a new protocol — but do
  check the new protocol accepts the test state (`cool`, 22 °C)
- Insert user-provided Tuya base64 strings anywhere in the codebase

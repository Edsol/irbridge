# IRBridge — Agent Instructions

## What this is

A Home Assistant custom integration that generates IR codes on-the-fly for climate devices. No pre-recorded code databases — codes are computed from protocol specs.

Developed alongside `../ir-lab`, which is the research tool used to reverse-engineer IR protocols. Raw generators are verified in ir-lab first, then ported here.

## Architecture

### Adding a protocol

Three steps only:

1. `generators/<name>.py` — raw IR generation logic (ported from ir-lab)
2. `generators/<name>_climate.py` — implement `ClimateGenerator` ABC from `base.py`
3. `generators/__init__.py` — add one entry to `_REGISTRY`

`climate.py` and `config_flow.py` require **no changes** — the new protocol appears automatically.

### Key files

| File | Role |
|------|------|
| `climate.py` | Protocol-agnostic `ClimateEntity` — reads capabilities from generator |
| `generators/base.py` | `ClimateGenerator` ABC and `ClimateCapabilities` dataclass |
| `generators/__init__.py` | Registry — single source of truth for available protocols |
| `senders/base.py` | `IRSender` ABC — implement to add new transmission backends |
| `config_flow.py` | Setup wizard + options flow (protocol, sender, blaster entity) |

### Sender abstraction

`IRSender.async_send_raw(raw: list[int])` is the only method. Adding a new sender (Broadlink, ESPHome, etc.) requires only implementing this method and registering it in `config_flow.py`.

### Options flow

Changing protocol/sender in the options flow triggers `_async_update_listener` which reloads the config entry — new capabilities (fan modes, swing, temp range) take effect immediately.

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

### Midea (`midea`)
- Devices: Ferroli, Midea
- Reverse-engineered via sweep acquisition in ir-lab
- Power on/off: fixed byte sequences (verified against acquired samples)
- Fan speed: not yet mapped (requires tagged sweep)
- Swing: not yet acquired

### Electra (`electra`)
- Devices: Beko (YKR-H/102E), AUX, Electrolux, Frigidaire
- Protocol: IRremoteESP8266 `ir_Electra.h` confirmed via sample analysis
- 13-byte frame, checksum = sum(logical bytes 0–11) & 0xFF
- Dry mode forces fan=low (protocol spec)
- Heat mode sets bit4 of B9 (Beko UseFahrenheit quirk)
- Swing vertical supported

## Current limitations

- Midea fan speed not mapped (only "auto" exposed)
- Midea swing not acquired
- `infrared_entity` sender is a placeholder (HA InfraredEmitterEntity API not yet stable)
- Tuya Cloud fallback not yet integrated

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
- Modify `climate.py` or `config_flow.py` when adding a new protocol
- Insert user-provided Tuya base64 strings anywhere in the codebase

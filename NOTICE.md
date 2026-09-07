# License notes

IRBridge is distributed under **GPL-3.0-or-later** (see [LICENSE](LICENSE)).

Copyright (C) 2026 Edoardo Soloperto

## Why GPL, and the change from MIT

Releases up to and including **0.4.0 were published under the MIT license**.
Anyone who obtained those versions keeps the rights MIT granted them; that
cannot be revoked. From **0.5.0 onward IRBridge is GPL-3.0-or-later**.

The reason is deliberate: MIT allows a derivative work to be closed and sold
without giving anything back. GPL does not. Selling is still permitted — the
GPL has never forbidden commerce — but a derivative that is distributed must
come with its source, under the same terms.

It also aligns IRBridge with [ir-lab](https://github.com/Edsol/ir-lab), the
research tool its protocol generators come from, which is GPL-3.0-or-later
because it depends on irtuya.

## Protocol specifications

IR protocols are described publicly, and this project treats those
descriptions as what they are: facts about how a machine communicates. Where a
frame puts its temperature field, how wide its header pulses are, and how its
checksum is computed are measurements, not authorship — anyone with a receiver
and a remote arrives at the same numbers.

The generators here are written from those measurements plus samples captured
from physical remotes with ir-lab, and each is verified against real hardware
before it ships. [IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266)
(LGPL-2.1) is credited in the source where its protocol constants confirmed an
analysis; GPL-3.0 is compatible with LGPL-2.1, so code may also be adapted from
it directly, with attribution in the file that does so.

## References

- [IRremoteESP8266](https://github.com/crankyoldgit/IRremoteESP8266) — protocol
  reference for a large number of air conditioner families
- [ir-lab](https://github.com/Edsol/ir-lab) — the capture and analysis workbench
- [infrared-protocols](https://github.com/home-assistant-libs/infrared-protocols)
  — the `Command` contract Home Assistant's infrared platform expects

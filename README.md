# GaryPilot: Rivian R1T & R1S (`GaryPilot`)

A personal [sunnypilot](https://github.com/sunnypilot/sunnypilot)-based openpilot fork for the **Rivian R1T & R1S**. It combines:

* **xnor-tech [`rx-dev`](https://github.com/xnor-tech/openpilot/tree/rx-dev)**: angle-based lateral control through the angle harness, plus low-speed oscillation smoothing.
* **AdventurePilot [`stg-a`](https://github.com/AdventurePilotDev/openpilot/tree/stg-a)** gear-stalk MADS semantics: an upward stalk flick toggles or disengages lateral control, and lateral control disengages in Park and Reverse. Includes the matching panda safety support.

> [!WARNING]
> **This is alpha-quality research software, not a product.** It modifies lateral control and panda safety firmware.
> You are responsible for complying with local laws and for driving attentively at all times. No warranty, expressed or implied.

## Status

| Area | State |
|---|---|
| Base | `xnor-tech/openpilot` `rx-dev` prebuilt `8a627abb0` |
| Fork infrastructure (docs, commit conventions, CI) | ✅ |
| Gear-stalk MADS parity (panda safety + Python) | ✅ |
| Custom Outrun Screensaver (optimized for Comma 4) | ✅ |
| Releases | Released! See [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md) |

### Stalk & Vehicle Behavior

| Action / Event | Behavior |
|---|---|
| Stalk **up, first detent** (UP_1) with ACC off | Toggle MADS lateral (lateral-only "Mode B") |
| Stalk **up, first detent** (UP_1) with ACC on | Cancels stock ACC and cleanly disengages MADS lateral (B5b) |
| Stalk **up, past detent** (UP_2) | Fully disengages lateral and longitudinal. Engagement blocked while held |
| Press stalk **Park** button | Disengages controls and immediately transitions Comma 4 to **Offroad mode** (screensaver, fans idle) |
| Shift to **Drive** or **Reverse** | Immediately wakes Comma 4 into **Onroad mode** |
| Shift to **Reverse** while active | Disengages lateral control. No steering actuation outside Drive |
| **Brake pedal** in turns | Steers through braking by default (`Remain Active` mode); settings unlocked |
| **Fight wheel** past EPAS limit | Rivian EPAS override detection triggers immediate comma lateral disengage with audible chime |

## Installation

Supported hardware: **comma 3X** and **comma four**, in a Rivian R1T/R1S with the angle harness.

1. On the device: **Settings → Software → Uninstall**. The device reboots into setup.
2. Choose **Custom Software** and enter:
   ```
   caleb-collar/GaryPilot
   ```
   (equivalent to `https://installer.comma.ai/caleb-collar/GaryPilot`)
3. On first boot the panda is reflashed with this branch's firmware.

**Rollback:** repeat the steps with `xnor-tech/rx-dev`. The panda firmware is restored automatically.

> [!IMPORTANT]
> Installed devices auto-update from `GaryPilot`. Only verified changes are promoted to that branch.

## Repository Layout & Remotes

This branch is rooted on xnor's **prebuilt** `rx-dev` tree. Libraries are vendored rather than submodules
(`opendbc_repo/`, `panda/`, `msgq_repo/`, …), and compiled aarch64 binaries are committed so the device skips the build.

| Remote | Repository | Purpose |
|---|---|---|
| `origin` | `caleb-collar/openpilot` | This fork |
| `upstream` | `xnor-tech/openpilot` | Base (`rx-dev`). Push disabled |
| `adventure` | `AdventurePilotDev/openpilot` | Feature reference (`stg-a`). Push disabled |

Key Rivian code:
* `opendbc_repo/opendbc/car/rivian/`: car state, controller, xnor angle smoothing (`ext_controller.py`)
* `opendbc_repo/opendbc/sunnypilot/car/rivian/`: stalk parsing, MADS car controller
* `opendbc_repo/opendbc/safety/modes/rivian.h`: panda safety mode
* `openpilot/sunnypilot/selfdrive/car/car_specific.py`, `openpilot/sunnypilot/mads/`: MADS event handling

## Development

```bash
git config core.hooksPath .githooks   # Conventional Commits hook
```

* **Commits:** [Conventional Commits](https://www.conventionalcommits.org/), enforced locally and in CI. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
* **Checks:** [`fork/`](fork/README.md) holds the sudo-free safety gate (tests, 100% coverage, MISRA, mutation), a reproducible panda firmware build and verify step, and the prebuilt-branch invariant checks. CI runs the same scripts.
* **Changelog:** [Keep a Changelog](https://keepachangelog.com/) in [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md). The root `CHANGELOG.md` is upstream sunnypilot's. The device parses it for release notes, so leave it untouched.
* **Plan, constraints, verification matrix, upstream resync workflow:** [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md).

## Credits

* [comma.ai openpilot](https://github.com/commaai/openpilot): the foundation
* [sunnypilot](https://github.com/sunnypilot/sunnypilot): MADS and the fork this builds on
* [xnor-tech](https://github.com/xnor-tech/openpilot): Rivian angle harness support and steering smoothing
* [AdventurePilot](https://github.com/AdventurePilotDev/openpilot): Rivian gear-stalk MADS design
* [lukasloetkolben](https://github.com/lukasloetkolben): original Rivian R1S/R1T port

## User Data

By default, openpilot/sunnypilot uploads driving data to comma servers. You can access your data through [comma connect](https://connect.comma.ai/). You are free to disable data collection.

openpilot logs the road-facing camera, CAN, GPS, IMU, magnetometer, thermal sensors, crashes, and operating system logs.
The driver-facing camera and microphone are only logged if you explicitly opt in in settings.

By using this software, you understand that use of this software or its related services will generate certain types of user data, which may be logged and stored at the sole discretion of comma. By accepting this agreement, you grant an irrevocable, perpetual, worldwide right to comma for the use of this data.

## Licensing

This fork is released under the [MIT License](LICENSE), like sunnypilot and openpilot, from which it derives. The original openpilot license notice, including comma.ai's indemnification and alpha software disclaimer, is reproduced below as required:

> openpilot is released under the MIT license. Some parts of the software are released under other licenses as specified.
>
> Any user of this software shall indemnify and hold harmless Comma.ai, Inc. and its directors, officers, employees, agents, stockholders, affiliates, subcontractors and customers from and against all allegations, claims, actions, suits, demands, damages, liabilities, obligations, losses, settlements, judgments, costs and expenses (including without limitation attorneys' fees and costs) which arise out of, relate to or result from any use of this software by user.
>
> **THIS IS ALPHA QUALITY SOFTWARE FOR RESEARCH PURPOSES ONLY. THIS IS NOT A PRODUCT.
> YOU ARE RESPONSIBLE FOR COMPLYING WITH LOCAL LAWS AND REGULATIONS.
> NO WARRANTY EXPRESSED OR IMPLIED.**

For full license terms, see the [`LICENSE`](LICENSE) and [`LICENSE.md`](LICENSE.md) files.

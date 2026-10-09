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
| GaryPilot Longitudinal Control (hardware-gated on `0x131a`) | ✅ |
| Rivian Vehicle Tab (Diagnostics & Customization) | ✅ |
| Safety Gate (MISRA C:2012, 100% Coverage, Mutation Testing) | ✅ |
| Releases | Released! See [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md) |

## Integration, Behavior & Safety Matrix

The table below summarizes GaryPilot's integration with the Rivian R1 platform, detailing system behavior, driver interaction, safety thresholds, and direct source code references:

| Integration Area & Driver Question | System Behavior & Driver Experience | Safety Limits & Thresholds | Source Code Reference |
|---|---|---|---|
| **Regen vs. Friction Braking**<br>_Does the system use one-pedal regen or physical brake pads?_ | Emulates Rivian Autonomous Control Module (ACM). Sends unified acceleration request `0x160` (`ACM_longitudinalRequest`) to Rivian's **VDM** (Vehicle Dynamics Module). VDM commands 100% regenerative braking via drive units first; blends Bosch ESP friction brakes only during heavy braking, cold/full battery, or standstill hold. Brake lights automatically trigger over $\approx 0.13\text{g}$. | **Panda Safety Limits:**<br>Max accel: $+2.0\text{ m/s}^2$<br>Min accel: $-3.5\text{ m/s}^2$<br>Factory AEB (`ACM_AebRequest`) immediately overrides openpilot. | [`carcontroller.py`](opendbc_repo/opendbc/car/rivian/carcontroller.py#L55)<br>[`riviancan.py`](opendbc_repo/opendbc/car/rivian/riviancan.py#L92-L103)<br>[`rivian_primary_actuator.dbc`](opendbc_repo/opendbc/dbc/rivian_primary_actuator.dbc#L174-L180)<br>[`rivian.h`](opendbc_repo/opendbc/safety/modes/rivian.h#L151-L155) |
| **Follow Distance Control**<br>_Does follow distance adjust via the Rivian steering wheel?_ | Scrolling the right steering wheel thumbwheel (`RightButton_Scroll`) emits `gapAdjustCruise` to cycle openpilot's `LongitudinalPersonality` via decrement: **Standard (1)** $\rightarrow$ **Aggressive (0)** $\rightarrow$ **Relaxed (2)**. Accompanied by on-screen chevron update and confirmation chime. | Software debounced against rapid misfires. Default initial personality is Standard (1). | [`carstate_ext.py`](opendbc_repo/opendbc/sunnypilot/car/rivian/carstate_ext.py#L86-L93)<br>[`selfdrived.py`](openpilot/selfdrive/selfdrived/selfdrived.py#L518-L524) |
| **ACC Set Speed Adjustments**<br>_How are cruise speed steps commanded on the steering wheel?_ | Single click Left/Right on the right thumbpad steps set speed by $\pm 1\text{ mph}$ ($\pm 1\text{ km/h}$) by default, or configurable to $\pm 5\text{ mph}$ ($\pm 5\text{ km/h}$) via **Settings $\rightarrow$ Vehicle $\rightarrow$ Thumbpad Speed Click Step**. Long press/hold steps by $\pm 5\text{ mph}$ ($\pm 10\text{ km/h}$). Flicking the gear stalk down raises set speed to match current speed if driving faster than set speed (never decreases below current set speed). | Cruise speed strictly clamped to $[20\text{ mph}, 85\text{ mph}]$ ($[32\text{ km/h}, 137\text{ km/h}]$). | [`carstate_ext.py`](opendbc_repo/opendbc/sunnypilot/car/rivian/carstate_ext.py#L145-L175)<br>[`rivian.py`](openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py#L65-L75) |
| **Native Radar & Sensor Fusion**<br>_Does openpilot blend Rivian native radar readings for ACC?_ | Reads 32 object tracking channels (`RADAR_TRACK_500` through `51f`) from Rivian's front millimeter-wave radar on `Bus.radar`. Filters stationary road clutter (guardrails) and fuses radar distance/velocity with vision model leads in `radard.py` for all-weather lead tracking. | Lead Kalman filter tracks distance (`dRel`) and closing rate (`vRel`). Vision model vetoes false positives from overhead bridges. | [`interface.py`](opendbc_repo/opendbc/car/rivian/interface.py#L54-L58)<br>[`radar_interface.py`](opendbc_repo/opendbc/car/rivian/radar_interface.py#L49-L73)<br>[`radard.py`](openpilot/selfdrive/controls/radard.py#L157-L182) |
| **Blind Spot Detection (BSM)**<br>_Are native Rivian blind spot sensors used for lane changes?_ | Ingests corner radar status (`BSM_BlindSpotIndicator_Fwd` / `0x1350`). When `AutoLaneChangeBsmDelay` is active, automated lane changes pause and wait while adjacent vehicles are detected until clear. Screen borders glow amber/red to mirror side mirrors. | Prevents lane change initiation if `leftBlindspot` or `rightBlindspot` is true. Inhibits low-speed turn assist into occupied paths. | [`carstate_ext.py`](opendbc_repo/opendbc/sunnypilot/car/rivian/carstate_ext.py#L178-L182)<br>[`desire_helper.py`](openpilot/selfdrive/controls/lib/desire_helper.py#L67-L78)<br>[`blind_spot_indicators.py`](openpilot/selfdrive/ui/sunnypilot/onroad/blind_spot_indicators.py) |
| **Dynamic Experimental Control (DEC)**<br>_How does DEC stop at red lights and avoid jerky hesitation?_ | Dynamically switches between ACC (speed-holding) and Blended (stopping for lights/signs). Employs 4 internal `SmoothKalmanFilter` instances (Lead, Slow Down, Slowness, MPC FCW) to filter trajectory endpoint shortages and eliminate mode flapping. | Hysteresis thresholds require minimum mode duration (10 frames) unless emergency FCW triggers immediate override. | [`dec.py`](openpilot/sunnypilot/selfdrive/controls/lib/dec/dec.py#L25-L76) ([#L145-L172](openpilot/sunnypilot/selfdrive/controls/lib/dec/dec.py#L145-L172), [#L242-L304](openpilot/sunnypilot/selfdrive/controls/lib/dec/dec.py#L242-L304)) |
| **Stop Signs & Traffic Lights**<br>_Does GaryPilot brake automatically for stop signs and red lights?_ | When **Dynamic Experimental Control (DEC)** or Experimental Mode is active, the vision model predicts stopping trajectories for detected stop lines, signs, and traffic signals. Stopping behavior is probabilistic based on model confidence, lighting, and approach distance. Because there are no hard CAN failsafes for stop signs, the driver must always actively supervise intersections and be prepared to brake manually. | Factory Bosch ESP AEB remains active as an emergency safety net. Turning off **Disengage on Accelerator** allows the driver to override and accelerate through intersections without dropping cruise engagement. | [`dec.py`](openpilot/sunnypilot/selfdrive/controls/lib/dec/dec.py)<br>[`longitudinal_planner.py`](openpilot/selfdrive/controls/lib/longitudinal_planner.py)<br>[`modeld.py`](openpilot/sunnypilot/modeld_v2/modeld.py) |
| **Accelerator Override & Resumption**<br>_What happens when pressing the gas pedal while engaged?_ | Pressing the accelerator allows the driver to manually override openpilot speed commands. When **Disengage on Accelerator** is turned **OFF**, releasing the accelerator returns the vehicle smoothly to the set speed without cancelling cruise or dropping MADS lateral steering. When turned **ON**, pressing the accelerator disengages cruise control. | Acceleration is strictly controlled by driver foot; openpilot resumes command only once driver lifts off below or at target set speed. | [`carcontroller.py`](opendbc_repo/opendbc/car/rivian/carcontroller.py#L55)<br>[`selfdrived.py`](openpilot/selfdrive/selfdrived/selfdrived.py)<br>[`controls.yaml`](openpilot/sunnypilot/sunnylink/settings_ui_src/pages/controls.yaml) |
| **Driving Model (WMI V12)**<br>_Can WMI V12 run on Comma 4 with these features?_ | Fully supported under `tinygrad` runner. Runs at native 20Hz (`is20hz: true`) with Generation 12 world model dynamics. Emits standard 33-point trajectory consumed identically by DEC and Vision Turn Speed. | Hardware load on Comma 4 NPU remains under 60% with zero dropped frames. | [`split_model_constants.py`](openpilot/sunnypilot/models/split_model_constants.py#L8-L25)<br>[`modeld.py`](openpilot/sunnypilot/modeld_v2/modeld.py#L173-L179) |
| **Smart Cruise & Curve Slowdown**<br>_How do vision and map-based turn speeds operate?_ | Vision curve slowdown uses path predictions from the driving model; Map curve slowdown queries local OpenStreetMap geometry (`OsmLocal`) to preemptively brake before tight highway ramps or sharp turns. Slowdown sensitivity and target speed margins are adjustable in settings. | Blended smoothly through longitudinal planner acceleration limits. Speeds offset by configurable margin (+5 mph). | [`settings_ui.json`](openpilot/sunnypilot/sunnylink/settings_ui.json)<br>[`cruise.yaml`](openpilot/sunnypilot/sunnylink/settings_ui_src/pages/cruise.yaml#L213-L270) |
| **Stalk Gestures & MADS State**<br>_How do gear stalk controls manage lateral and longitudinal?_ | **UP_1**: Configurable via **Settings $\rightarrow$ Vehicle $\rightarrow$ Stalk UP_1 Tap Action**: *MADS Toggle* (Mode B, default), *Cancel ACC* (factory Rivian behavior), or *Disengage All* (simultaneous lateral & longitudinal).<br>**UP_2**: Full disengage of lateral and longitudinal.<br>**Park**: Disengages controls and triggers immediate Offroad mode.<br>**Reverse**: Disengages lateral control. | UP_2 MADS button press is inhibited in panda safety; full disengage latching and Park/Reverse transitions are enforced in car_specific.py. No steering actuation permitted outside Drive. | [`carstate_ext.py`](opendbc_repo/opendbc/sunnypilot/car/rivian/carstate_ext.py#L80-L125)<br>[`rivian.h`](opendbc_repo/opendbc/safety/modes/rivian.h#L78-L88)<br>[`car_specific.py`](openpilot/sunnypilot/selfdrive/car/car_specific.py#L61-L92)<br>[`rivian.py`](openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py#L55-L65) |
| **Steering Limits & Overrides**<br>_What are the physical and panda safety limits for steering?_ | Dual-channel control (angle commands + cooperative torque). Steering angle clamped to 500°. Torque limited to 350 counts ($\le 9\text{ m/s}$) stepping down to 250 counts ($\ge 17\text{ m/s}$). Driver override sensitivity is driver-tunable via **Settings $\rightarrow$ Vehicle $\rightarrow$ Driver Override Sensitivity** (*Light*: 75 allowance / 0.75 Nm threshold; *Standard*: 100 allowance / 1.00 Nm threshold; *Firm*: 100 allowance / 1.30 Nm threshold, respecting panda safety limit of 100). EPAS driver override detection instantly disengages with audio chime. | **Panda Safety Limits:**<br>Max rate up: 3 / frame<br>Max rate down: 5 / frame<br>Max real-time delta: 125 | [`rivian.h`](opendbc_repo/opendbc/safety/modes/rivian.h#L119-L149)<br>[`carstate.py`](opendbc_repo/opendbc/car/rivian/carstate.py#L48-L61)<br>[`ext_controller.py`](opendbc_repo/opendbc/car/rivian/ext_controller.py#L230-L245)<br>[`rivian.py`](openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py#L76-L86) |
| **Hardware & Harness Diagnostics**<br>_How do I verify the angle harness and longitudinal hardware?_ | Dedicated **Settings $\rightarrow$ Vehicle $\rightarrow$ Rivian** tab displays real-time diagnostic cards: Lateral Angle Harness (`0x1310`), Longitudinal Upgrade / XNOR XTREME (`0x131a`), Platform Generation (`0x321`), Front Radar (32 Tracks), and Corner Radar BSM (`0x1350`). Emits summary telemetry via `RivianHarnessStatus`. | Live updates run at 1Hz in UI; controls customization is disabled during active drives (`not_engaged` gate) for on-road safety. | [`rivian.py`](openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py)<br>[`carstate_ext.py`](opendbc_repo/opendbc/sunnypilot/car/rivian/carstate_ext.py#L40-L75)<br>[`vehicle.yaml`](openpilot/sunnypilot/sunnylink/settings_ui_src/pages/vehicle.yaml#L104-L145) |
| **Configuration Architecture**<br>_Where are settings managed, and are there conflicting toggles?_ | Streamlined control under **Toggles $\rightarrow$ GaryPilot Longitudinal Control** (disabled by default, strictly requiring hardware check `0x131a` on bus 1) with safety confirmation modal. Dedicated **Settings $\rightarrow$ Vehicle $\rightarrow$ Rivian** tab hosts live Hardware & Harness Diagnostics and controls customization (UP_1 stalk action, speed click step, driver override sensitivity). | Persistent parameters: `AlphaLongitudinalEnabled` (defaults to `"0"` / disabled; activates factory Rivian ACC). Hardware and control preferences stored via atomic `VIRTUAL_PARAMS` (`RivianHarnessStatus`, `RivianStalkUp1Action`, `RivianSpeedClickStep`, `RivianSteerOverrideSensitivity`). | [`toggles.py`](openpilot/selfdrive/ui/layouts/settings/toggles.py#L55-L66)<br>[`rivian.py`](openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py)<br>[`toggles.yaml`](openpilot/sunnypilot/sunnylink/settings_ui_src/pages/toggles.yaml#L22-L43)<br>[`vehicle.yaml`](openpilot/sunnypilot/sunnylink/settings_ui_src/pages/vehicle.yaml#L104-L145)<br>[`params.py`](openpilot/common/params.py#L37-L43) |
| **Automated Safety Gate & Invariants**<br>_How are safety, code quality, and branch invariants verified?_ | Every push and pull request runs automated CI: 100% Panda safety line coverage, 26 SunnyLink/Rivian unit tests, automotive static analysis with MISRA C:2012 (268 active checkers, 0 violations), and tree-sitter mutation testing (3,422 mutants evaluated, 99.91% killed). Prebuilt branch invariants strictly protect compiled binaries and param schemas. | Strict gate in `fork-ci.yml`. Conventional commit headers enforced up to 120 characters via `.githooks/commit-msg`. | [`fork-ci.yml`](.github/workflows/fork-ci.yml)<br>[`safety_tests.sh`](fork/scripts/safety_tests.sh)<br>[`check_invariants.sh`](fork/scripts/check_invariants.sh)<br>[`test_misra.sh`](opendbc_repo/opendbc/safety/tests/misra/test_misra.sh)<br>[`mutation.py`](opendbc_repo/opendbc/safety/tests/mutation.py) |
| **Updates & Remote Management**<br>_Does Comma 4 auto-update, and can it be rebooted remotely?_ | Devices automatically pull updates from branch `GaryPilot` when parked/offroad on Wi-Fi. Can be rebooted remotely via SSH (`sudo reboot`), web dashboard, or on-device UI. | SSH disabled by default for vehicle security (`SshEnabled: false`). Updates stage safely before prompting reboot. | [`updated.py`](openpilot/system/updated/updated.py)<br>[`hardwared.py`](openpilot/system/hardware/hardwared.py) |



## Installation

Supported hardware: **comma 3X** and **comma four**, in a Rivian R1T/R1S with the angle harness.

### New Install or Clean Reinstall
1. On the device: **Settings → Software → Uninstall** *(uninstalls driving software; does not factory-reset AGNOS or Wi-Fi)*.
2. The device reboots into the setup screen. Choose **Custom Software** and enter either:
   * **Full URL**:
     ```text
     https://installer.comma.ai/caleb-collar/GaryPilot
     ```
   * **Shorthand**:
     ```text
     caleb-collar/GaryPilot
     ```
   > [!IMPORTANT]
   > The branch name **`GaryPilot`** is case-sensitive in git. Ensure both `G` and `P` are capitalized.

3. On first boot the panda is reflashed with this branch's firmware automatically.

### Switching from an Existing Fork or Prior Branch
If your Comma was already running a previous branch or another fork pointing to `caleb-collar/openpilot`:
* **Via On-Device UI (Fastest):**
  1. Open **Settings → Software → Select a branch**.
  2. Select **`GaryPilot`**.
  3. Tap **Check for Updates** (or wait for the download to finish).
  4. Tap **Reboot** when prompted.
* **Via SSH:**
  ```bash
  ssh comma@<device-ip>
  cd /data/openpilot
  git remote set-url origin https://github.com/caleb-collar/openpilot.git
  git fetch origin GaryPilot
  git checkout -B GaryPilot origin/GaryPilot
  git submodule sync
  git submodule update --init --recursive
  touch prebuilt
  sudo rm -rf /data/safe_staging/*
  sudo reboot
  ```

**Rollback:** repeat the steps with `xnor-tech/rx-dev` (`https://installer.comma.ai/xnor-tech/rx-dev`). The panda firmware is restored automatically.

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

## Trademark & Legal Disclaimers

* **Rivian®**, **R1T®**, and **R1S®** are registered trademarks of their respective owners, **RIVIAN AUTOMOTIVE, LLC** and **RIVIAN AUTOMOTIVE, INC.**
* Rivian is a registered trademark of its respective owner. This project is independent and has no official affiliation with the manufacturer.
* **No Endorsement or Affiliation:** This project is an independent, community-driven open-source research fork. It is not affiliated with, endorsed by, sponsored by, or certified by Rivian Automotive, LLC, Rivian Automotive, Inc., or any of their affiliates.
* **No License or Credit Taken:** We do not claim any ownership, rights, or license to Rivian's trademarks, trade dress, or logos, nor do we take credit for or license Rivian's logo or intellectual property. Any references to Rivian vehicle makes or models are used strictly for vehicle identification, technical compatibility, and nominative fair use.
* **Exclusion of Visual Assets:** As stated in the [`LICENSE`](LICENSE) and [`LICENSE.md`](LICENSE.md) files, the MIT license applies solely to source code files. Visual assets and UI themes are excluded from this license.


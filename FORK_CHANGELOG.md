# Changelog

All notable changes to the `caleb-collar/openpilot` **GaryPilot** fork are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Fork versions are tagged `r1-vX.Y.Z` and are independent of the upstream sunnypilot version
(`openpilot/sunnypilot/common/version.h`).

> The root `CHANGELOG.md` is upstream sunnypilot's changelog. The device parses it at runtime
> for release notes, so this fork leaves it unchanged.

## [Unreleased]

## [0.2.2] - 2026-10-08

### Added

- Dedicated **Rivian Settings** menu in sunnylink and on-device Raylib UI:
  - Added `- id: rivian` section in `pages/vehicle.yaml` and recompiled canonical `settings_ui.json`, providing a dedicated brand configuration card for Rivian R1 vehicles on the public sunnylink web portal.
  - Implemented `RivianSettings` layout in `openpilot/selfdrive/ui/sunnypilot/layouts/settings/vehicle/brands/rivian.py` for full on-device screen parity.
  - Added **Enforce Factory Longitudinal Control** (`RivianEnforceStockLongitudinal`, default: Off): enables drivers to seamlessly fallback to native Rivian ACC radar/speed control while preserving continuous sunnypilot MADS steering assist (architecturally aligned with Toyota's stock longitudinal enforcement).
  - Added `VIRTUAL_PARAMS` support in `openpilot/common/params.py` with thread-safe in-memory caching and atomic file writes (`NamedTemporaryFile` + `os.replace`), eliminating file-tearing and disk stalls in real-time loops while keeping `params_keys.h` byte-identical to maintain prebuilt-branch invariants (plan D4).

### Changed

- Updated sunnylink and on-device UI warnings for **Alpha Longitudinal Control**:
  - Replaced the inaccurate blanket warning ("will disable Automatic Emergency Braking (AEB)") in `developer.yaml`, `settings_ui.json`, and `developer.py`.
  - Clarified that on vehicles with isolated AEB architecture (such as Rivian R1 with XNOR XTREME hardware), factory Automatic Emergency Braking (AEB) remains fully active via direct Bosch ESP intervention.

### Fixed

- Hardened factory AEB collision avoidance and fail-safe disengagement:
  - Added `ET.IMMEDIATE_DISABLE: ImmediateDisableAlert("Stock AEB: Risk of Collision")` to `EventName.stockAeb` in `openpilot/selfdrive/selfdrived/events.py`: forces `controlsd` to immediately transition to `disabled` with an audible alert, resetting integrators and preventing dangerous post-AEB acceleration snapback.
  - Enforced `CC.cruiseControl.cancel = True` alongside `CC.enabled = False` in `opendbc_repo/opendbc/sunnypilot/car/rivian/mads.py` (`MadsCarController.update`): immediately halts openpilot acceleration requests while vehicle Bosch ESP executes emergency braking.
  - Preserved openpilot's native hold state machine without standstill spoofing or high-frequency param polling, preventing unexpected creep in intersection stop-and-go scenarios.
- Fixed virtual parameter erasure by C++ `Params::clearAll`:
  - Relocated virtual parameter persistence to a dedicated `.virtual/` subdirectory within the parameters directory. Because C++ `Params::clearAll` skips directory entries (`de->d_type == DT_DIR`), virtual parameters are protected from being unlinked during manager startup (`CLEAR_ON_MANAGER_START`) or onroad/offroad drive transitions.
  - Added seamless automatic migration from legacy root parameter paths into `.virtual/`.
  - Scoped cache keys to the canonical parameter path (`self.get_param_path()`) and implemented 100 ms polling for `block=True` virtual parameter reads.
- Fixed UI dialog crashes in on-device Rivian settings:
  - Replaced non-existent `gui_app.show_dialog` with `gui_app.push_widget(dlg)` and instantiated `ConfirmDialog` with `rich=True` and keyword `callback=` to avoid callback misinterpretation.
- Fixed bitwise filtering in `all_keys` to ensure virtual parameters with `ParamKeyFlag.BACKUP` are discovered by Sunnylink cloud backup RPCs.
- Hardened `_initialize_rivian` in `interfaces.py` against `None` values in car interface params dictionaries.
- Expanded Sunnylink device telemetry in `capabilities.py` to accurately report `stock_longitudinal` for Rivian vehicles.

## [0.2.1] - 2026-10-08

### Fixed

- Decoupled MADS steering mode enablement from cruise engagement in the sunnylink schema:
  - Added `mads_full_steering_platforms` macro in `_macros.yaml` allowing Rivian full access to all steering modes on brake (`Remain Active`, `Pause`, `Disengage`).
  - Updated `MadsSteeringMode` options in `steering.yaml` to reference `mads_full_steering_platforms`, eliminating the false lockout that previously disabled `Remain Active` and `Pause` in the sunnylink web portal.
  - Preserved `mads_full_platforms` for `MadsMainCruiseAllowed` (forced off) and `MadsUnifiedEngagementMode` (forced on) to match Rivian stalk hardware constraints.
  - Recompiled canonical `settings_ui.json` and added regression tests in `test_settings_changes.py`.

## [0.2.0] - 2026-10-08

- Replaced the screensaver version number with an authentic driving pixel art vehicle cruising forward on the Outrun perspective grid: features signature coast-to-coast red LED lightbar with stadium pill capsules, warm sunset rear glass reflections, yellow recovery hooks, cyan glowing license plate, road suspension micro-rumble (15 Hz), gentle lane cruise sway (seamless 4.0s cycle), cyan underbody neon glow, and red taillight ambient bloom across Comma 4 (536x240) and Comma 3X (2160x1080 integer scaling).

- Added subtle synthwave screensaver animations to the GaryPilot typography badge: weightless organic hover floating (seamless 4.0s sine cycle), breathing luminescence glow pulse (seamless 2.0s sine cycle), and authentic 4-pointed retro diamond star specular glints cycling across letter highlights ('G', 'P', '0') on Comma 4 and Comma 3X.
- Added animated GIF export (`--gif`) and timestamped screenshot capture (`--time`) to `preview_screensaver.py` for headless verification and seamless loop inspection.
- Updated GaryPilot screensaver badge with enlarged, clean anti-aliased chrome typography and an ethereal soft luminous glow: rendered at font size 46 with 2x supersampling for pristine vector letterforms with natural geometry, brilliant white and metallic silver fill, multi-tier soft white/silver halo (replacing the previous hard border), and a soft ambient drop shadow to smoothly dim perspective grid lines behind the text.
- Enhanced screensaver badge generation: programmatic Audiowide font and version rendering now runs dynamically at runtime in `screen_saver.py` when Pillow is available, with seamless fallback to pre-rendered embedded base64 assets (`generate_screensaver_badge.py`) for minimal and headless device environments.
- Restored authentic Rivian compass emblem bytes to the screensaver retro sun with clean PNG headers and exact 92x91 active bounding box within 128x128 canvas, eliminating sky blowout and preserving starry night views on Comma 4 and Comma 3X.
- Added legal IP & trademark protections: updated `LICENSE.md` with explicit exclusions for visual assets and UI themes, added trademark disclosures in `README.md`, and disassociated internal logo asset filenames and variable names (`r_logo`).
- Documented full installer URL (`https://installer.comma.ai/caleb-collar/GaryPilot`), shorthand slug (`caleb-collar/GaryPilot`), case-sensitivity requirements, and on-device/SSH branch switching instructions across `README.md` and `INTEGRATION_PLAN.md`.
- Added "GaryPilot" retro 1980s chromed gradient pixel art badge to the Outrun screensaver (`ScreenSaverSP`), supporting both Comma 4 and Comma 3X resolutions.
- Centered and enlarged "GaryPilot" badge on the screensaver: positioned precisely in the vertical midpoint of the lower half of the display (equidistant 30px margins to horizon and bottom on Comma 4, 150px margins on Comma 3X) with 1.5x scale multiplier (6.0x crisp integer multiplier on Comma 3X).
- Achieved 100% parity between the screensaver preview simulator (`preview_screensaver.py`) and real Comma 4 / 3X devices by sharing `draw_screensaver(...)` directly from `openpilot/system/ui/sunnypilot/widgets/screen_saver.py`, with 100% deterministic screenshot capture.
- Updated UI home screen, settings toggles, startup alerts, device info, and setup wizards to reflect "GaryPilot" branding across Comma 4 and Comma 3X layouts.
- Migrated primary production branch and installation target to `GaryPilot`.
- Added first-boot Rivian R1 vehicle verification screen to the onboarding setup flow on both Comma 4 (`mici`) and Comma 3X, requiring explicit confirmation that the device is installed in a supported Rivian R1 with XNOR angle harness before proceeding, with a one-tap "Not an R1 / Uninstall" option to revert the device.
- Bumped `terms_version_sp` to `2.0` in `openpilot/common/version.py`, ensuring `hardwared` and UI gate onroad startup until vehicle verification is completed.
- Added automated runtime vehicle safety lockout (`enforce_vehicle_safety_gate` in `openpilot/selfdrive/car/helpers.py` called by `card.py`): non-Rivian vehicle CAN fingerprints permanently lock GaryPilot into passive dashcam-only mode (`CP.passive = True`, `CP.dashcamOnly = True`) and configure panda hardware safety to `SafetyModel.noOutput`, preventing any CAN actuation packets from ever being transmitted to non-Rivian vehicles.

## [0.1.0] - 2026-10-07

### Added

- Added a custom Outrun/Synthwave retro screensaver (`ScreenSaverSP`) featuring a 3D perspective neon grid, starry night sky, wireframe mountains, and a glowing retro sun motif.

- Fork infrastructure on top of `xnor-tech/openpilot` `rx-dev` prebuilt `8a627abb0`:
  fork README, this changelog, `CONTRIBUTING.md`, and the integration plan (`INTEGRATION_PLAN.md`, revision 2).
- Conventional Commits enforcement: `.githooks/commit-msg` hook (enable with
  `git config core.hooksPath .githooks`) and a GitHub Actions commit-lint job.
- Ported AdventurePilot `stg-a` MADS disengage behavior: shifting out of Drive or pulling the stalk to UP_2 cancels lateral control without canceling longitudinal control (`feat/v0.1-python-disengage`).
- Ported AdventurePilot `stg-a` MADS engage behavior: pulling the stalk to UP_1 toggles lateral control (`feat/v0.2-panda-engage`), along with rigorous C firmware debounce logic for the stalk sweep.
- GitHub Actions `fork-ci` workflow: commit lint, and `py_compile` + `ruff` on fork-touched Python files.
- Sudo-free fork tooling in `fork/` (see `fork/README.md`). All tools come from hash-locked wheels in the upstream `uv.lock` files:
  - `safety_tests.sh`: panda safety gate (all safety-mode tests, 100% line coverage, MISRA C:2012, mutation testing).
  - `build_firmware.sh` + `fw_compare.py`: build panda firmware from any ref in an isolated worktree with the pinned
    Arm GNU Toolchain 13.2.rel1, and verify committed firmware matches committed sources (byte-identical modulo gitversion).
  - `check_invariants.sh`: enforces the prebuilt-branch rules (no param-key/capnp/native changes, upstream changelogs
    untouched, installer requirements, xnor angle-stack files unchanged).
- CI jobs `invariants`, `safety`, and `firmware` (strict on `r1-dev`, `GaryPilot`, sync branches, and PRs;
  uploads firmware images and `SHA256SUMS` as artifacts).
- B5b tests (UP_1 with ACC on, Remain Active / Pause) on both the Python and panda side, plus Rivian
  steer-through-braking tests.
- `py_tests.sh` + CI job `pytests`: runs the fork's openpilot-side Python tests (and upstream's MADS tests) on x86_64 by
  building host copies of `libparams_c.so` and msgq from the committed sources into a cache dir outside the tree.
- PRNDL-aware CAN ignition for Rivian R1: CAN ignition evaluates PRNDL gear status (`0x150 VDM_PropStatus`) alongside EPAS power mode. Pushing the Park button on the stalk immediately transitions CAN ignition to false, allowing the comma to enter offroad mode (showing the screensaver, spinning down fans, and closing the drive log) instead of staying awake indefinitely on auxiliary fuse power. Shifting into Drive or Reverse immediately restores CAN ignition and wakes openpilot back onroad.
- Driver fighting / override protection: verified and tested that Rivian EPAS error 12 (`EPAS_Hands_On_Detn_Err`) triggers `steerDisengage` (`ET.USER_DISABLE`), immediately disengaging comma lateral control with audible chime; regression test added in `test_rivian_b5b_sp.py` (`TestRivianDriverOverrideDisengage`).

### Fixed

- Rivian steering mode on brake defaults to **Remain Active** (steer through braking in turns); push the stalk to
  UP_2 to fully disengage. The car port never writes `MadsSteeringMode`, so your choice in settings always wins.
  This deviates from AdventurePilot, which seeds Disengage on a first install. The previous seeding code also called
  `Params.put_int()`, which does not exist, so `card` would have crashed at startup on a default-mode device.
- MADS settings no longer lock Rivian to Disengage: the port had missed AdventurePilot's UI change, so opening the
  settings page forced `MadsSteeringMode` back to Disengage. All three modes are selectable; UEM stays forced on and
  Toggle with Main Cruise stays forced off, as in AdventurePilot.
- `uv.lock` restored to upstream (it had been silently re-locked by a local `uv run`); `check_invariants.sh` now pins it.
- `ruff` lint in the screensaver (whitespace and long lines only; the AST is unchanged).

[Unreleased]: https://github.com/caleb-collar/openpilot/compare/r1-v0.2.2...GaryPilot
[0.2.2]: https://github.com/caleb-collar/openpilot/compare/r1-v0.2.1...r1-v0.2.2
[0.2.1]: https://github.com/caleb-collar/openpilot/compare/r1-v0.2.0...r1-v0.2.1
[0.2.0]: https://github.com/caleb-collar/openpilot/compare/r1-v0.1.0...r1-v0.2.0
[0.1.0]: https://github.com/caleb-collar/openpilot/tree/r1-v0.1.0

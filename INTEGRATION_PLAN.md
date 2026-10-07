# Specification & Execution Plan: Rivian R1T openpilot Integration

## xnor Angle Steering + AdventurePilot Gear-Stalk MADS Parity

| Field | Value |
|---|---|
| Plan revision | 2.2 (2026-10-07) |
| Target | `caleb-collar/openpilot` @ `r1t-xnor-adventure` |
| Upstream base | `xnor-tech/openpilot` @ `rx-dev` → `8a627abb0` ("openpilot rx-dev prebuilt") |
| Upstream source (reference) | `xnor-tech/openpilot` @ `rx-new-src` → `406a1bc09` ("Rivian: angle control"). Its Rivian, safety, and MADS code matches `rx-dev` except for one MISRA suppression comment in `mads.h` |
| Feature source (prebuilt) | `AdventurePilotDev/openpilot` @ `stg-a` → `f5e525279` |
| Feature source (**primary port reference**) | `AdventurePilotDev/openpilot` @ `stg-a-src` → `80886ced` (full history, focused commits; see §2.6) |
| Fork changelog | [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md) (Keep a Changelog + SemVer) |
| Conventions | [`CONTRIBUTING.md`](CONTRIBUTING.md) (Conventional Commits) |
| Fork tooling | [`fork/README.md`](fork/README.md) (safety gate, firmware build/verify, invariant checks) |

## Status & Next Step (for a fresh session)

* **Done:** Phase 0 (fork, remotes, docs, commit hook, CI). Phase 1 steps 1–4 and 6: sudo-free toolchain, baseline safety gate green, firmware reproduced from source, CI jobs for both (see [Phase 1 baseline](#phase-1-baseline-results-2026-10-07)). Work happens on `r1t-dev`. The device branch `r1t-xnor-adventure` is fast-forwarded from it only after review.
* **Blocked on the owner:** Phase 1 step 5. Supply **at least 3 rx-dev angle-harness routes** (comma connect route IDs, made public, or downloaded `rlog`s) that contain UP_1/UP_2 stalk presses, Park/Reverse shifts, and ACC on/off. A stock upstream route is not representative (§0 #18).
* **Next:** Phase 2 (v0.1 Python Port). Run `git fetch adventure stg-a-src` and read the source commits in §2.6 first. We will implement the fail-safe Python-only disengage logic first.
* **Setup for a fresh clone:** install `uv` (see `fork/README.md`), then `fork/scripts/safety_tests.sh --quick` and `fork/scripts/build_firmware.sh --verify`.

## Decision Log

| ID | Decision | Rationale |
|---|---|---|
| D1 | **Full stg-a stalk parity**, including panda safety and a firmware rebuild (owner decision) | `ButtonType.lkas` is a toggle. Python-only would desync from the panda. Safety is paramount, so the port is test-heavy |
| D2 | Fork log in `FORK_CHANGELOG.md`. Root `CHANGELOG.md` untouched (owner decision) | The root file is parsed on the device for release notes and is overwritten on every resync |
| D3 | Do not port stg-a's torque-limit increase or angle-stack changes | Invariants I1 and I4 |
| D4 | No new param keys or cereal enums. Features that need them are excluded | Prebuilt binaries can't be rebuilt (§2.2) |
| D5 | `r1t-xnor-adventure` is fast-forward-only from tested branches | Installed devices auto-update from it |
| D6 | Port by hand, reading `stg-a-src` commit history. Use the prebuilt diff only as a cross-check | No shared history. Source commits carry rationale, tests, and route IDs |

---

## 0. Revision 2: Gaps Corrected from Revision 1

| # | Revision 1 assumption | Reality (verified) | Correction |
|---|---|---|---|
| 1 | `opendbc_repo` is a git submodule; commit inside it and bump the pointer | No `.gitmodules`. `rx-dev` is a **vendored, single-commit, orphan prebuilt tree** and `opendbc_repo/` is plain tracked files | Removed submodule phase. Edit files in place |
| 2 | `r1t-xnor-adventure` can be merged and diffed against `stg-a` normally | `rx-dev` and `stg-a` are **orphan prebuilt commits with no merge base**. They diverge across 1,530 files (different sunnypilot snapshots) | **Never merge or cherry-pick `stg-a`.** Port by hand from an explicit [port manifest](#26-stg-a-port-manifest) |
| 3 | UP_1 → `ButtonType.lkas` gives "disengagement" | `ButtonType.lkas` is a **toggle** in MADS (`openpilot/sunnypilot/mads/mads.py:174`). It also *engages*. stg-a only makes this safe by patching **panda safety firmware** (`rivian.h`) | Scope now includes the panda safety port, a firmware rebuild, and panda↔Python MADS consistency invariants |
| 4 | Pure-Python change | The prebuilt ships aarch64 `.so`s and **debug-signed panda firmware** (`DEV-ff8d7d84-DEBUG`) | Added toolchain, firmware rebuild, and artifact-commit phases. Documented what can and cannot change on a prebuilt |
| 5 | stg-a's Rivian files can be taken wholesale | stg-a's `rivian.h` also **raises torque limits** (350→385). Its `carstate.py` **removes** rx-dev's long-rejection loopback and changes non-harness fault semantics. It also adds params and cereal enums that rx-dev lacks | Per-hunk Port / Adapt / Exclude decisions. Hard rule: no new param keys and no cereal schema changes |
| 6 | Installer check: `curl` returns "a shell script" | `installer.comma.ai` returns an HTML stub unless the User-Agent is `AGNOSSetup-*`. With that UA it returns an **aarch64 ELF** with the repo URL and branch embedded | Fixed the acceptance command (see Phase 6) |
| 7 | Git LFS assets must be validated | This tree has **no `.gitattributes` / LFS**. The largest tracked file is 58 MB (`driving_supercombo.onnx`), under GitHub's 100 MB limit | LFS step downgraded to a sanity check |
| 8 | Conventional commit format not specified (`rivian: ...` example) | — | Conventional Commits enforced by `.githooks/commit-msg` and CI |
| 9 | Changelog unspecified | Root `CHANGELOG.md` is **parsed at runtime** (`common/version.py`, `system/updated/updated.py`) for device release notes, and `test_markdown.py` checks it | Upstream `CHANGELOG.md` is left byte-for-byte untouched. The fork log lives in `FORK_CHANGELOG.md` |
| 10 | No upstream-sync strategy | xnor force-publishes new orphan prebuilts | Added the [resync workflow](#phase-8-upstream-resync-workflow) |
| 11 | Pushes go straight to the install branch | Devices **auto-update** from the branch they were installed from | Added branch promotion rules (see §5) |
| 12 | "Comma 4X" | The products are **comma 3X** (`tizi`) and **comma four** (`mici`) | Renamed |
| 13 | `origin` = xnor-tech | — | `origin` = caleb-collar, `upstream` = xnor-tech, `adventure` = AdventurePilotDev. Push is disabled on `upstream` and `adventure` |
| 14 | (rev 2) Only prebuilt trees are available | Both sources publish **history-bearing source branches**: `adventure/stg-a-src` and `upstream/rx-new-src` | Use the source commits as the primary port reference (D6, §2.6) |
| 15 | (rev 2) `libsafety` is built with scons | `libsafety_py.py` compiles `safety.c` with **gcc through cffi at import time**. scons is only needed for panda firmware | Corrected §2.2 and Phase 1 |
| 16 | (rev 2.1) Phase 1 needs sudo for `cppcheck`, `scons`, and `gcc-arm-none-eabi` | All three ship as **hash-locked wheels** (`opendbc_repo/uv.lock` for cppcheck, root `uv.lock` for `scons==4.10.1` and `comma-deps-gcc-arm-none-eabi==13.2.1.post98`). Only `uv` is needed, installed per-user | No sudo. `fork/scripts/fw_requirements.py` derives the toolchain pins from `uv.lock` |
| 17 | (rev 2.1) Firmware byte-identity is not expected (toolchain drift) | The committed ELFs were built with **Arm GNU Toolchain 13.2.rel1**, the same compiler the wheel ships. A rebuild is **byte-identical except for the 8-char SHA in `gitversion`**, and the debug signature is deterministic | CI now proves committed firmware matches committed sources (`build_firmware.sh --verify`). Phase 4 becomes verifiable |
| 18 | (rev 2.1) Any Rivian route works for replay | Public CI route `bc095dc92e101734/000000db--ee9fe46e57` (stock upstream, torque control) replays with 0 RX errors but **251 blocked `0x120`** TX against rx-dev safety. It was recorded with different software | Replay acceptance must use **rx-dev angle-harness routes** from the owner. The public route only proves the replay pipeline works on PC |

---

## 1. Goal & Invariants

### 1.1 Objective
Build one publicly installable branch that combines:
* **From xnor `rx-dev`**: angle-based lateral control via the angle harness (`RivianFlags.ANGLE_HARNESS`, `EPAS_AdasStatus` handling) and low-speed oscillation smoothing (`ext_controller.py`).
* **From AdventurePilot `stg-a`**: gear-stalk MADS semantics. UP_1 toggles MADS lateral. UP_2 fully disengages lateral. Shifting to Park or Reverse disengages lateral. Lateral actuation is gated to Drive. This includes the matching **panda safety** support.

### 1.2 Non-Negotiable Invariants
1. **I1 – Angle stack preserved.** These stay functionally identical to `rx-dev`: `ext_controller.py`, angle-harness EAC fault semantics in `carstate.py` (`steerFaultPermanent` / `steerFaultTemporary` / `steeringDisengage`), the `Bus.loopback` long-rejection counter, and `carcontroller.py` / `riviancan.py` angle paths.
2. **I2 – Stalk parity with stg-a** (behavior table in Phase 5).
3. **I3 – Panda/Python MADS consistency.** The panda never grants lateral that Python would not command. Python never commands lateral the panda would reject. Rejected `0x110` frames create counter gaps, which fault the EPAS (`AngleControlCntr` → EAC fault + `ToiFlt` latch; stg-a route `c17ea97dc5472650/00000006` seg 3).
4. **I4 – Safety is never loosened.** Steering and longitudinal limits in `rivian.h` stay at `rx-dev` values. All safety tests, MISRA C:2012 checks, and mutation tests pass. New safety lines have 100% test coverage.
5. **I5 – Installer compatible.** The branch installs from the comma setup wizard on comma 3X / comma four with no extra steps.
6. **I6 – Resync friendly.** Fork changes stay minimal and isolated. Upstream-owned files that change every release (`CHANGELOG.md`, `RELEASES.md`) are never edited.

---

## 2. Discovery Findings

### 2.1 Remotes & Refs

| Remote | URL | Push | Role |
|---|---|---|---|
| `origin` | `git@github.com:caleb-collar/openpilot.git` (public fork in the commaai network) | ✅ | Target |
| `upstream` | `git@github.com:xnor-tech/openpilot.git` | disabled | Base (`rx-dev`) |
| `adventure` | `git@github.com:AdventurePilotDev/openpilot.git` | disabled | Feature reference (`stg-a`) |

The branch root commit is always the upstream prebuilt it is based on:
`git rev-list --max-parents=0 HEAD`. CI and the resync workflow depend on this.

### 2.2 Prebuilt Branch Constraints

`rx-dev` contains a `prebuilt` marker, so the device skips `scons` at launch.

| Can change | How |
|---|---|
| Python (openpilot, sunnypilot, opendbc car code) | Edit in place. Interpreted at runtime |
| Panda safety C (`opendbc_repo/opendbc/safety/**`) | Edit, then **rebuild and debug-sign** `panda/board/obj/*` and commit the binaries. Prior art: rx-dev ships `DEV-ff8d7d84-DEBUG` and stg-a ships `DEV-unknown-DEBUG`. `pandad` reflashes automatically on signature mismatch |
| Docs / CI / tooling | Freely |

| Must NOT change | Why |
|---|---|
| Param keys (`openpilot/common/params_keys.h`) | Compiled into the aarch64 params library. Unknown keys raise `UnknownKeyName` at runtime |
| Cereal schema (`openpilot/cereal/*.capnp`) | C++ consumers are prebuilt against the shipped schema |
| openpilot C/C++ (`*.cc`, `*.so`, binaries) | Would need a full aarch64 build. Out of scope |
| `prebuilt` marker, `launch_openpilot.sh` (mode `100755`) | Required for installer/boot |

**Testing consequence:** the aarch64 `.so`s do not load on x86. openpilot-side tests that import `Params` / `messaging` must run **on the device** (SSH, `/data/openpilot`). opendbc **safety** tests run on the PC: `opendbc/safety/tests/libsafety/libsafety_py.py` compiles `safety.c` with host gcc through cffi at import time (debug build with `-DALLOW_DEBUG` and gcov coverage flags). No scons is needed for this.

### 2.3 Layout

* `opendbc_repo/opendbc/car/rivian/` (also importable as `opendbc/car/rivian/` via a symlink; the root symlinks are gitignored and created at launch)
  * `carstate.py`, `carcontroller.py`, `ext_controller.py` (xnor smoothing), `riviancan.py`, `values.py`, `interface.py`
* `opendbc_repo/opendbc/sunnypilot/car/rivian/`: `carstate_ext.py` (stalk + long-upgrade parsing), `mads.py` (`MadsCarController`)
* `opendbc_repo/opendbc/safety/modes/rivian.h`: panda safety mode. `opendbc_repo/opendbc/safety/sunnypilot/mads.h`: MADS safety state machine
* `openpilot/sunnypilot/selfdrive/car/car_specific.py`: `CarSpecificEventsSP` (brand event shaping)
* `openpilot/sunnypilot/mads/{mads.py,state.py,helpers.py}`: MADS controller, state machine, brand helpers
* `panda/board/obj/`: committed firmware (`panda_h7.bin.signed`, bootstubs, `gitversion.h`)

### 2.4 CAN Signals

| Message | ID | Bus | Signal | Notes |
|---|---|---|---|---|
| `VDM_AdasSts` | `0x162` (354) | 0 | `VDM_UserAdasRequest` (bit 58, 3 bits → `data[7] & 0x7`) | `0 IDLE, 1 UP_1, 2 UP_2, 3 DOWN_1, 4 DOWN_2`. Checksum `data[0]` (poly `0x1D`, init `0xD1`). Counter `data[1] & 0xF`. ~50 Hz. **Known to lag and burst two frames** (`carstate.py` comment) |
| `VDM_AdasSts` | `0x162` | 2 (TX) | — | openpilot already **transmits** `0x162` to bus 2 (to the ACM) in `rx-dev`. Stalk parsing must read the **bus 0 original** |
| `VDM_AdasStalk` | `0x165` (357) | 0 | `VDM_AdasStalkAccCancelRes` (0 none, 1 cancel, 2 resume) | Not used by stg-a. Reference only |
| `ACM_Status` | `0x100` | 2 | `feature_status` | Drives `pcm_cruise_check`. stg-a also calls `stock_ecu_check(false)` here to tick `mads_state_update()` |

### 2.5 MADS Mechanics (rx-dev)

* `ButtonType.lkas` pressed → `lkasEnable` if MADS is off. If MADS is on, it gives `lkasDisable`, or `manualSteeringRequired` when selfdrive is engaged (`mads.py:174-180`).
* `EventNameSP.lkasDisable` (`custom.capnp` `@1`) and `silentLkasDisable` (`@5`) exist. `belowMadsMinEngageSpeed` and the `rivian*` angle-toggle events **do not** exist.
* rx-dev lists Rivian in `get_mads_limited_brands()`, which forces `MadsSteeringMode = 2` (DISENGAGE). stg-a removes it to unlock the full steering-mode choice, a prerequisite for Mode B (lateral-only via UP_1).
* **Paused-vs-disabled race:** on Park/Reverse entry, `wrongGear` → `transition_paused_state()` → `silentLkasDisable` in the same frame as `lkasDisable`, so the state ends `paused`. stg-a works around this by firing `lkasDisable` on two consecutive frames. The cleaner fix (explicit `lkasDisable` beats `silentLkasDisable` in `state.py`) changes shared behavior and is **deferred** (see §6).
* Panda side: `mads_heartbeat_engaged_check()` exits lateral after 3 mismatches. stg-a resets `heartbeat_engaged_mads_mismatches` in `mads_exit_controls()` so a saturated counter cannot kill the next re-engage.
* `RxCheck.ignore_frequency_check` **is available** in rx-dev's `declarations.h`, which can mitigate the `0x162` burst/lag risk.

### 2.6 stg-a Port Manifest

Legend: **Port** = bring over as is (re-applied by hand). **Adapt** = port with changes. **Exclude** = do not bring over.

| # | File | stg-a change | Decision | Rationale |
|---|---|---|---|---|
| P1 | `sunnypilot/car/rivian/carstate_ext.py` | `update_stalk_controls()`: UP_1 rising edge (from IDLE/DOWN) → deferred `ButtonType.lkas` with 1-frame lookahead (dropped if the next frame is UP_2). Suppressed when steering mode is DISENGAGE and ACC is on. UP_2 edges → `altButton2` press/release | **Port** | Core stalk semantics |
| P2 | same | Aggregate `buttonEvents` across sub-parsers (stops `gapAdjustCruise` overwriting `ret.buttonEvents`) | **Port** | Needed so stalk events aren't clobbered |
| P3 | same | Read `MadsSteeringMode` via lazy `openpilot` import (keeps opendbc importable standalone) | **Port** | Key exists in rx-dev |
| P4 | same | First-drive seeding of `MadsSteeringMode = DISENGAGE` when `CarParamsPersistent` is unset | **Port** | Parity. Mutates a user param only on a never-driven device |
| P5 | same | DOWN_2 resume-to-last-set-speed (`RivianResumeEnabled`) | **Exclude** | New param key (prebuilt constraint). Not stalk-up |
| P6 | `selfdrive/car/car_specific.py` | Rivian branch: `altButton2` → `lkasDisable`. Suppress `pcmEnable` while UP_2 is held or in Park. Park/Reverse entry → two-frame `lkasDisable` | **Port** | Core disengage semantics |
| P7 | same | `brakePressed` and mode PAUSE → `silentLkasDisable` every frame | **Port** | Required once P9 unlocks PAUSE for Rivian |
| P8 | same | `belowMadsMinEngageSpeed` / `MadsMinEngageSpeed`. Angle-toggle phases (`RivianAngleSteerPhase`, `rivianHold*`, `RivianAngleSaturated`) | **Exclude** | Missing cereal enums and param keys. Angle toggle conflicts with xnor's angle stack (I1) |
| P9 | `sunnypilot/mads/helpers.py` | Remove Rivian from `get_mads_limited_brands()`. Set `MadsMainCruiseAllowed = False` for Rivian (instead of removing it) | **Port** | Prerequisite for UP_1 toggle / Mode B |
| P10 | `sunnypilot/car/rivian/mads.py` | `lat_active` hard-gated to `GearShifter.drive` | **Port** | Safety improvement (no wheel motion in R/P/N) |
| S1 | `safety/modes/rivian.h` | `0x162` checksum (`0x1D`/`0xD1`) + RX check (bus 0, 50 Hz, `max_counter 14`) | **Adapt** | Port, but first validate against real routes. Use `ignore_frequency_check` if bursts/lag trip the check (§6 R1) |
| S2 | same | `mads_button_press = (UP_1 && !cruise_engaged_prev)` | **Port** | Panda half of the UP_1 toggle (I3) |
| S3 | same | `stock_ecu_check(false)` on `ACM_Status` (+ forward declaration) | **Port** | Ticks `mads_state_update()` at 100 Hz |
| S4 | same | Unused `rivian_prev_user_adas_request` state | **Adapt** | Drop it if unused (MISRA unused-variable). Keep the reset in `rivian_init` if retained |
| S5 | same | Torque limits `max_torque 350→385`, lookup `{9,17,17}/{350,250,250}` → `{9,25,27}/{385,295,275}` | **Exclude** | Loosens limits (I4). Unrelated to the stalk |
| S6 | same | `0x162` removed from `RIVIAN_LONG_TX_MSGS` | **Investigate** | Understand why before deciding. Default: keep rx-dev's TX list |
| S7 | `safety/sunnypilot/mads.h` | Reset `heartbeat_engaged_mads_mismatches` in `mads_exit_controls()` | **Port** | Prevents re-engage kills → EPAS faults (I3) |
| S8 | `safety/sunnypilot/mads.h` | Remove a `cppcheck-suppress misra-c2012-8.7` comment | **Exclude** | Unrelated. Would risk a MISRA regression |
| T1 | `safety/tests/test_rivian.py` | Stalk/MADS safety tests | **Port** (stalk-related only) | I4 coverage |
| T2 | `sunnypilot/selfdrive/car/tests/test_rivian_gear_disengage_sp.py`, Rivian parts of `test_car_specific_sp.py`, `mads/tests/*` deltas | **Port** | Run on the device (§2.2) |
| X1 | `car/rivian/carstate.py` | Removes `Bus.loopback` long-rejection counter. Changes non-harness `steerFaultTemporary` to `H_CAN_EPSS_ToiFlt`/`HandsOnLevel` | **Exclude** | I1 |
| X2 | `car/rivian/{carcontroller,ext_controller,interface,riviancan,values,angle_toggle}.py` | stg-a's own angle/torque tuning | **Exclude** | I1 |
| X3 | All non-Rivian drift (VW MEB, MG, Subaru, Ford, `lateral.h`, `longitudinal.h`, …) | Different upstream snapshot | **Exclude** | Out of scope |

#### Source commits on `adventure/stg-a-src` (read these first: `git show <sha>`)

Some commits appear twice (same change landed on two lineages). Paths before the repo flattening lack the `openpilot/` prefix.

| Manifest items | Commit(s) | Subject |
|---|---|---|
| P1, P2, P9, S2 (original port) | `cad9b1fa2` | rivian: port MADS lateral control from lat-mads-resume |
| S1–S4 (+ T1) | `02d27fcac` | Rivian safety: MADS lateral (Mode B), port dev's stalk wiring |
| S7, S2 `!cruise_engaged_prev` gate (+ T1) | `3cb72baa1` / `6b655f6b0` | panda MADS: fix engage-revoke race that faults the Rivian EPAS (route c17ea97d/6#3) |
| P10 symState/`lka_icon_states` | `e5f87cd24` | rivian: fix EPAS ToiFlt oscillation on MADS re-enable |
| P10 drive-gear gate | `670f76fe9` (rationale: `bf5e773c4` on `stg-a-revgate-src`) | gate MADS lateral to drive gear |
| P6 reverse entry | `5e7b49a5a` / `5c44026e4` (history: `dbbb6e066`, reverted in `0bd3bd3e9`; see R8) | rivian: disengage MADS fully on reverse gear entry |
| P4 (+ T2 test) | `483c4286a` / `1a7e4cce9` | rivian: default MadsSteeringMode to DISENGAGE on a first install only |
| S5 (excluded, for context) | `097d26503` | Rivian safety: torque envelope + blip handling |

Discovery command: `git log --oneline adventure/stg-a-src -- <path>`. Use `git log -S '<symbol>'` to trace a single hunk.

---

## 3. Comma Installer Compatibility

1. The repository must be `caleb-collar/openpilot` and **public**. ✅ (fork created)
2. The branch name equals the URL slug: `r1t-xnor-adventure`.
3. `launch_openpilot.sh` is at the root with mode `100755`. ✅ (verified in the index)
4. The `prebuilt` marker stays present, and all runtime binaries are committed.
5. No LFS pointers. No file is 100 MB or larger. ✅ (largest is 58 MB)
6. Panda firmware in `panda/board/obj/` matches the committed safety sources (Phase 4).

---

## 4. Phased Execution Plan

### Phase 0: Repository Bootstrap ✅ (this revision)
- [x] Fork `xnor-tech/openpilot` → `caleb-collar/openpilot` (public, default branch only).
- [x] Remotes: `origin`/`upstream`/`adventure`. Push disabled on `upstream` and `adventure`.
- [x] Working branch `r1t-xnor-adventure` rooted at `rx-dev` `8a627abb0`.
- [x] Conventional Commits: `.githooks/commit-msg`, enabled per clone with `git config core.hooksPath .githooks`.
- [x] Docs: `README.md` (fork), `FORK_CHANGELOG.md`, `CONTRIBUTING.md`, this plan.
- [x] CI: `.github/workflows/fork-ci.yml` (commit lint and Python checks on fork-touched files). Actions enabled on the fork. `r1t-xnor-adventure` set as the default branch.

### Phase 1: Toolchain & Baseline (no source changes)
1. [x] Install host tools. **No sudo** (§0 #16): host `gcc`/`gcov` plus a checksum-verified per-user `uv` (`fork/README.md`). `uv` provides Python 3.12, `cppcheck` (opendbc lock), and `scons` + Arm GNU Toolchain 13.2.rel1 (root lock, via `fork/scripts/fw_requirements.py`).
2. [x] Python 3.12 env for opendbc: `fork/scripts/safety_tests.sh` runs `uv sync --locked` into `opendbc_repo/.venv` (gitignored). `--locked` keeps `uv.lock` untouched.
3. [x] **Baseline safety gate** on the unmodified tree: `fork/scripts/safety_tests.sh` (all modes, coverage, MISRA, mutation).
4. [x] **Baseline firmware build** on the unmodified tree: `fork/scripts/build_firmware.sh --verify` (isolated sparse worktree, debug cert only). The result is reproducible (§0 #17).
5. [ ] **Collect replay data** (owner): rx-dev angle-harness routes with UP_1/UP_2 presses, Park/Reverse shifts, and ACC on/off. Run `safety_replay` on them with the baseline safety (command in `fork/README.md`). The PC replay pipeline is already validated on a public route (§0 #18).
6. [x] CI jobs: `invariants`, `safety`, `firmware` in `fork-ci.yml`, calling the same scripts.

Exit criteria: baseline tests green ✅, firmware builds reproducibly ✅, at least 3 replay routes available ⏳.

#### Phase 1 baseline results (2026-10-07)

Tree: `r1t-xnor-adventure` @ `8321693ab` (rx-dev `8a627abb0` + docs/CI only). Host: Ubuntu 26.04, gcc 15.2, 16 cores.

| Check | Result |
|---|---|
| Safety unit tests (all modes) | 8433 run, **OK** (915 skipped). `test_rivian` + `test_defaults`: 179 run, OK (20 skipped) |
| Line coverage | **100%** (2684/2684). `modes/rivian.h` 74/74, `sunnypilot/mads.h` 103/103 |
| MISRA C:2012 | **Pass** (268/386 active checkers) |
| Mutation | 3388 mutants, 3385 killed. **3 survivors, all upstream's `known_survivors`** in `lateral.h:190/220/221` (rt-window and angle-delta boundaries). Script exit 0 |
| Firmware toolchain | Committed ELFs and the rebuild both report `Arm GNU Toolchain 13.2.rel1 (Build arm-13.7) 13.2.1 20231009` |
| Firmware rebuild | `panda_h7` / `panda_jungle_h7` / `body_h7` `main.bin` + bootstubs **identical modulo gitversion** (committed `DEV-ff8d7d84-DEBUG`). `*.bin.signed` == debug-sign(committed `main.bin`). Section sizes identical. A negative test (`rivian.h` `max_torque` 350→349 in a dangling commit) is caught as `DIFFERS` |
| Signed image sizes | `panda_h7.bin.signed` 103216 B, `panda_jungle_h7.bin.signed` 96036 B, `body_h7.bin.signed` 102620 B |
| Safety replay (public stock route, seg 2) | Pipeline works on PC. 399014 RX / 0 invalid. 7199 TX / 251 blocked (`0x120`). Not representative (§0 #18) |
| Invariants (`check_invariants.sh`) | All pass. A negative test (edits to `CHANGELOG.md` / `ext_controller.py` / launcher mode) fails as expected |

> [!NOTE]
> `lateral.h` angle-limit survivors (#153/#156) sit on code the Rivian angle path may use. They are upstream's, not
> introduced here, and are out of scope (I4 only forbids loosening). Revisit if Phase 2 touches `lateral.h`.

### Phase 2: Python Port (v0.1 Staged Rollout)
This phase implements **only** the fail-safe disengage logic in Python. It does not touch the Panda firmware.
1. Create branch `feat/v0.1-python-disengage` from `r1t-dev`.
2. Apply P1–P4, P6, P7, P9, P10. Preserve I1 (diff `carstate.py`, `ext_controller.py`, `carcontroller.py` against `rx-dev`. The expected delta is empty. `check_invariants.sh` enforces this).
3. Hard guard (CI-checkable): no new `Params` keys and no cereal enums outside what `rx-dev` defines. File-level guards already exist in `check_invariants.sh`. Add a key-usage scan for fork-touched Python here.
4. Keep `opendbc` importable without `openpilot` (lazy imports only).
5. Port T2 tests. Add opendbc-level unit tests for the stalk edge detector (lookahead, UP_1→UP_2, DOWN→UP_1, ACC/DISENGAGE suppression).
6. **Exclude** the UP_1 lateral toggle logic from `mads.py`/`carstate_ext.py` for now, as it requires a Panda firmware update (which comes in v0.2) to prevent EPAS fault latches from counter gaps.
7. Commits, e.g.: `feat(rivian): map gear-stalk UP_2 and shifting to MADS disengage`, `feat(mads): unlock full steering modes for rivian`, `fix(rivian): gate lateral actuation to drive gear`.

### Phase 3: Safety Layer Port (C) (v0.2 Staged Rollout)
This phase implements the Panda firmware support for the UP_1 toggle, allowing Python and Panda to agree on lateral engagement.
1. Create branch `feat/v0.2-panda-engage` from `feat/v0.1-python-disengage`.
2. Apply S1–S4 and S7 to `rivian.h` / `mads.h`. Do not apply S5 or S8. Resolve S6.
3. Tests in `test_rivian.py` (T1):
   * `0x162` checksum/counter validation. A bad checksum or counter must not count as a press.
   * UP_1 sets `mads_button_press` only while `!cruise_engaged_prev`.
   * UP_2 never force-exits and never grants lateral.
   * `ACM_Status` ticks MADS state.
   * The heartbeat-mismatch counter resets on exit.
   * **Regression guard:** steering limits equal rx-dev values.
4. Run `fork/scripts/safety_tests.sh` (MISRA, mutation, and coverage). 100% of new lines must be covered, and mutation must add no survivors.
5. Replay (Phase 1.5 routes) with the new safety. Zero unexpected `controls_allowed` drops. If `0x162` bursts or lag trip the RX check, switch to `ignore_frequency_check` and document why.
6. Commit: `feat(safety): track rivian gear-stalk for MADS lateral`, `fix(safety): reset MADS heartbeat mismatch counter on exit`.
7. Introduce the UP_1 lateral toggle logic back into the Python files (`carstate_ext.py`).

> [!IMPORTANT]
> Push to `r1t-dev` only together with the final `build(panda)` commit. On `r1t-dev`, the device branch, and PRs, CI fails if committed firmware doesn't match the safety sources.

### Phase 4: Firmware Rebuild & Artifact Commit (v0.2)
1. With all source commits in place and a clean tree: `fork/scripts/build_firmware.sh --install`. This builds from `HEAD` (debug cert only, and it refuses `RELEASE`/`CERT`), then copies the artifacts into `panda/board/obj/`.
2. Commit the binaries as **one dedicated, final commit**: `build(panda): rebuild firmware with rivian stalk MADS safety`. Put the toolchain version, the source commit SHA (= gitversion), and `SHA256SUMS` in the commit body.
3. Confirm `fork/scripts/build_firmware.sh --verify` passes on the new `HEAD`. CI enforces this too.
4. This commit is always last on the branch. Resyncs drop and regenerate it (Phase 8).

### Phase 5: Verification Matrix

**PC (CI where possible):** commit lint · `py_compile` + `ruff` on touched files · invariants · safety tests · MISRA · mutation · coverage · firmware reproducibility (all in CI) · safety replay (local, owner routes).

**Device (SSH, `/data/openpilot`):** `pytest` T2 suites and `openpilot/sunnypilot/mads/tests`.

**Behavioral acceptance (on road; record route IDs in the PR / changelog):**

| # | Precondition | Action | Expected |
|---|---|---|---|
| B1 | Drive, ACC off, MADS off | UP_1 tap | MADS lateral engages (Mode B). Panda `controls_allowed_lateral` follows. No EPAS fault |
| B2 | Drive, ACC off, MADS on | UP_1 tap | MADS lateral disengages |
| B3 | Any | Fast push through UP_1 → UP_2 | **No** MADS toggle from the UP_1 transit. Lateral disengaged |
| B4 | Any engaged state | UP_2 | `lkasDisable`. `pcmEnable` suppressed while held. No re-engage on release |
| B5 | ACC on, steering mode DISENGAGE | UP_1 | ACC cancels natively. **No** MADS toggle (Python or panda) |
| B5b | ACC on, steering mode REMAIN_ACTIVE or PAUSE | UP_1 | Python still emits `lkas` (→ `manualSteeringRequired`), while the panda ignores the press (`cruise_engaged_prev`). Verify there is no heartbeat-mismatch exit or EPAS fault, and that the resulting MADS state is what we intend. **Asymmetric by design. Needs explicit test coverage** |
| B6 | Lateral active | Shift to Park / Reverse | MADS state is `disabled` (not `paused`). No wheel motion in R/P/N |
| B7 | Mode PAUSE, lateral active | Brake (moving and standstill) | Lateral paused for the whole press |
| B8 | 30+ engage/disengage cycles | Mixed B1–B7 | Zero heartbeat-mismatch exits, `steerTempUnavailable` loops, or `AngleControlCntr` faults |
| B9 | Angle harness | Low-speed maneuvers | Smoothing/feel matches `rx-dev` (no shudder or hunting) |

### Phase 6: Release & Installer Validation
1. Promote to `r1t-xnor-adventure` (see §5). Move `[Unreleased]` → `[0.1.0]` in `FORK_CHANGELOG.md`, tag `r1t-v0.1.0`, then push the branch and tag.
2. Validate the installer (the UA is required, and the payload is an aarch64 ELF):
   ```bash
   curl -sS -A "AGNOSSetup-16.0" -o /tmp/installer https://installer.comma.ai/caleb-collar/r1t-xnor-adventure
   file /tmp/installer                       # expect: ELF 64-bit ... ARM aarch64
   strings /tmp/installer | grep -E 'github.com/caleb-collar/openpilot|r1t-xnor-adventure'
   ```

### Phase 7: Device Onboarding (comma 3X / comma four)
1. Settings → Software → **Uninstall** (both UIs set `DoUninstall`). The device reboots into setup.
2. Choose **Custom Software** and enter `caleb-collar/r1t-xnor-adventure`.
3. First boot: `pandad` reflashes the panda with the fork firmware. Expect a brief panda reset.
4. Run B1–B9.
5. **Rollback:** reinstall `xnor-tech/rx-dev` the same way. `pandad` flashes rx-dev's firmware back automatically.

### Phase 8: Upstream Resync Workflow
When xnor publishes a new `rx-dev` prebuilt (a force-pushed orphan):
```bash
git fetch upstream rx-dev
old_base=$(git rev-list --max-parents=0 r1t-xnor-adventure)
git switch -c sync/rx-dev-$(date +%Y%m%d) r1t-xnor-adventure
git rebase -i --onto upstream/rx-dev "$old_base"   # mark the final build(panda) commit as "drop"; Phase 4 regenerates it
```
1. Resolve source conflicts. **Never resolve binary conflicts by picking a side.** Regenerate firmware (Phase 4: `build_firmware.sh --install`, then `--verify`). Before rebasing, run `build_firmware.sh --ref upstream/rx-dev --verify` to confirm the new upstream firmware is itself reproducible with the pinned toolchain.
2. Re-diff the I1 files against the new `rx-dev`. Re-run the full Phase 5 matrix.
3. Add a `Changed: rebased onto xnor-tech/rx-dev <sha>` entry to `FORK_CHANGELOG.md`.
4. Promote with `git push --force-with-lease origin sync/...:r1t-xnor-adventure`. On-device `updated` handles force-pushed branches (fetch + hard reset).

---

## 5. Branching & Commit Conventions

* **Conventional Commits** for every fork commit (enforced by hook and CI). Types: `feat fix docs style refactor perf test build ci chore revert`. Common scopes: `rivian`, `safety`, `mads`, `panda`, `sync`, `docs`, `ci`. Full guide: [`CONTRIBUTING.md`](CONTRIBUTING.md).
* `r1t-xnor-adventure` is the **device branch**: installed cars auto-update from it. Only verified work lands there.
* Develop on `feat/<topic>` / `fix/<topic>` branches, or on the integration branch `r1t-dev`. Promote to `r1t-xnor-adventure` by fast-forward only after the Phase 5 matrix passes.
* History stays linear (rebase, no merge commits). The firmware artifact commit is always last.
* Every user-visible change gets a `FORK_CHANGELOG.md` entry under `[Unreleased]`.

---

## 6. Risks & Open Items

| ID | Risk | Mitigation |
|---|---|---|
| R1 | The `0x162` RX check trips on known lag/burst, causing spurious `controls_allowed` drops | Replay validation (Phase 2.4). Fall back to `ignore_frequency_check` |
| R2 | Panda/Python MADS desync (stg-a hit this) | S2 `!cruise_engaged_prev` gate, S7 reset, B5/B8 acceptance |
| R3 | The firmware toolchain differs from xnor's | **Mitigated (Phase 1).** The pinned wheel is the same Arm GNU Toolchain 13.2.rel1 that xnor used, and the rebuild is byte-identical modulo gitversion. CI `firmware` re-proves this on every push. Re-check after resyncs that bump `uv.lock` |
| R4 | Two-frame `lkasDisable` hack depends on MADS state-machine ordering | Unit test B6 on device. Revisit the general `state.py` fix upstream with sunnypilot |
| R5 | P4 seeding changes a user setting | Only on a never-driven device. Documented in the changelog |
| R6 | An xnor resync changes the angle stack under us | Phase 8 step 2 (I1 re-diff) |
| R7 | Open question S6 (`0x162` in the long TX list) | Resolve during Phase 2 before porting |
| R8 | Reverse-entry `lkasDisable` (P6) has a history: first landed as `dbbb6e066`, **reverted** (`0bd3bd3e9`) for "a loggerd error on engagement", then re-landed (`5e7b49a5a`, Aug 2026) after a road test. The drive-gear gate (P10) independently stops actuation in Reverse | During B6, watch loggerd and `onroadEvents`. If the error recurs, P10 alone still meets "no steering in Reverse". Fall back to P10 only and record the change |

---

## 7. Verification Checklist

- [x] `git-lfs` available (3.5.1). Tree has no LFS objects
- [x] SSH + `gh` authenticated as `caleb-collar`
- [x] Public fork `caleb-collar/openpilot` exists. Remotes configured, upstream push disabled
- [x] Conventional Commits hook + CI, README, FORK_CHANGELOG, CONTRIBUTING committed
- [x] Phase 1 baseline: safety gate green (tests, 100% coverage, MISRA, mutation), firmware reproducible from source, CI jobs added
- [ ] Phase 1 replay routes collected (≥3 rx-dev angle-harness routes from the owner)
- [ ] Safety port S1–S4, S7 with tests, MISRA, mutation, 100% new-line coverage
- [ ] Python port P1–P4, P6, P7, P9, P10 with tests. I1 files unchanged vs `rx-dev`
- [ ] No new param keys / cereal enums
- [ ] Firmware rebuilt and committed as the final commit
- [ ] Device test suites pass on hardware
- [ ] Behavioral matrix B1–B9 passes on road (route IDs recorded)
- [ ] `r1t-v0.1.0` tagged. Installer returns an aarch64 ELF referencing the fork + branch

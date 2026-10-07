# Specification & Execution Plan: Rivian R1T openpilot Integration

## xnor Angle Steering + AdventurePilot Gear-Stalk MADS Parity

| Field | Value |
|---|---|
| Plan revision | 2.1 (2026-10-07) |
| Target | `caleb-collar/openpilot` @ `r1t-xnor-adventure` |
| Upstream base | `xnor-tech/openpilot` @ `rx-dev` → `8a627abb0` ("openpilot rx-dev prebuilt") |
| Upstream source (reference) | `xnor-tech/openpilot` @ `rx-new-src` → `406a1bc09` ("Rivian: angle control"). Its Rivian, safety, and MADS code matches `rx-dev` except for one MISRA suppression comment in `mads.h` |
| Feature source (prebuilt) | `AdventurePilotDev/openpilot` @ `stg-a` → `f5e525279` |
| Feature source (**primary port reference**) | `AdventurePilotDev/openpilot` @ `stg-a-src` → `80886ced` (full history, focused commits; see §2.6) |
| Fork changelog | [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md) (Keep a Changelog + SemVer) |
| Conventions | [`CONTRIBUTING.md`](CONTRIBUTING.md) (Conventional Commits) |

## Status & Next Step (for a fresh session)

* **Done:** Phase 0 (fork, remotes, docs, commit hook, CI). The branch is pushed and is the fork's default. CI is green. The installer endpoint already returns a valid aarch64 installer for the fork.
* **Next:** Phase 1 (toolchain + baseline, no source changes). It needs host packages installed with sudo (§Phase 1) and Rivian routes from the owner.
* **Before Phase 2:** `git fetch adventure stg-a-src` and read the source commits listed in §2.6.

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
1. Install host tools:
   * Safety tests: `uv`, `gcc` (cffi builds `libsafety`), `cppcheck` (MISRA, run by `safety/tests/misra`).
   * Firmware: `scons`, `gcc-arm-none-eabi` (match the version `panda/setup.sh` installs).
   * The host Python is 3.14, but the repo pins 3.12 (`.python-version`). Let `uv` provide 3.12.
2. Create the Python 3.12 env for opendbc: `cd opendbc_repo && ./setup.sh` (or `uv sync`).
3. **Baseline safety tests** on the unmodified tree: build `libsafety`, then run `test_rivian.py`, `test_defaults.py`, and the MADS common tests. Record the results.
4. **Baseline firmware build** on the unmodified tree (`CERT` unset → debug cert). Confirm the build succeeds and record its size and gitversion next to the committed binary. Byte-identity is not expected (toolchain drift).
5. **Collect replay data**: export Rivian routes from comma connect that contain UP_1/UP_2 presses, Park/Reverse shifts, and ACC on/off. Confirm `opendbc/safety/tests/safety_replay` runs on them with the baseline safety.
6. Add CI jobs for (3) and (4) once they run locally (`ci:` commit).

Exit criteria: baseline tests green, firmware builds reproducibly, at least 3 replay routes available.

### Phase 2: Safety Layer Port (C)
1. Apply S1–S4 and S7 to `rivian.h` / `mads.h`. Do not apply S5 or S8. Resolve S6.
2. Tests in `test_rivian.py` (T1):
   * `0x162` checksum/counter validation. A bad checksum or counter must not count as a press.
   * UP_1 sets `mads_button_press` only while `!cruise_engaged_prev`.
   * UP_2 never force-exits and never grants lateral.
   * `ACM_Status` ticks MADS state.
   * The heartbeat-mismatch counter resets on exit.
   * **Regression guard:** steering limits equal rx-dev values.
3. Run MISRA (`safety/tests/misra`), mutation tests (`safety/tests/mutation.py`), and coverage. 100% of new lines must be covered.
4. Replay (Phase 1.5 routes) with the new safety. Zero unexpected `controls_allowed` drops. If `0x162` bursts or lag trip the RX check, switch to `ignore_frequency_check` and document why.
5. Commit: `feat(safety): track rivian gear-stalk for MADS lateral`, `fix(safety): reset MADS heartbeat mismatch counter on exit`.

### Phase 3: Python Port
1. Apply P1–P4, P6, P7, P9, P10. Preserve I1 (diff `carstate.py`, `ext_controller.py`, `carcontroller.py` against `rx-dev`. The expected delta is empty).
2. Hard guard (CI-checkable): no new `Params` keys and no cereal enums outside what `rx-dev` defines.
3. Keep `opendbc` importable without `openpilot` (lazy imports only).
4. Port T2 tests. Add opendbc-level unit tests for the stalk edge detector (lookahead, UP_1→UP_2, DOWN→UP_1, ACC/DISENGAGE suppression).
5. Commits, e.g.: `feat(rivian): map gear-stalk UP_1/UP_2 to MADS toggle and disengage`, `feat(mads): unlock full steering modes for rivian`, `fix(rivian): gate lateral actuation to drive gear`.

### Phase 4: Firmware Rebuild & Artifact Commit
1. Rebuild `panda/board/obj/*` from the modified sources with the debug cert.
2. Commit the binaries as **one dedicated, final commit**: `build(panda): rebuild firmware with rivian stalk MADS safety`. Put the toolchain version, source tree hash, and gitversion in the commit body.
3. This commit is always last on the branch. Resyncs drop and regenerate it (Phase 8).

### Phase 5: Verification Matrix

**PC (CI where possible):** commit lint · `py_compile` + `ruff` on touched files · safety tests · MISRA · mutation · coverage · safety replay.

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
1. Resolve source conflicts. **Never resolve binary conflicts by picking a side.** Regenerate firmware (Phase 4).
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
| R3 | The firmware toolchain differs from xnor's | Pin the arm-gcc version from `panda/setup.sh`. Baseline build in Phase 1 |
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
- [ ] Phase 1 baseline: safety tests green, firmware builds, replay routes collected
- [ ] Safety port S1–S4, S7 with tests, MISRA, mutation, 100% new-line coverage
- [ ] Python port P1–P4, P6, P7, P9, P10 with tests. I1 files unchanged vs `rx-dev`
- [ ] No new param keys / cereal enums
- [ ] Firmware rebuilt and committed as the final commit
- [ ] Device test suites pass on hardware
- [ ] Behavioral matrix B1–B9 passes on road (route IDs recorded)
- [ ] `r1t-v0.1.0` tagged. Installer returns an aarch64 ELF referencing the fork + branch

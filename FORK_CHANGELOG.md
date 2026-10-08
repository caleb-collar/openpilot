# Changelog

All notable changes to the `caleb-collar/openpilot` **r1-xnor-adventure** fork are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Fork versions are tagged `r1-vX.Y.Z` and are independent of the upstream sunnypilot version
(`openpilot/sunnypilot/common/version.h`).

> The root `CHANGELOG.md` is upstream sunnypilot's changelog. The device parses it at runtime
> for release notes, so this fork leaves it unchanged.

## [0.1.0] - 2026-10-07

### Added

- Added a custom Outrun/Synthwave retro screensaver (`ScreenSaverSP`) featuring a 3D perspective neon grid, starry night sky, wireframe mountains, and a glowing Rivian logo sunset.

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
- CI jobs `invariants`, `safety`, and `firmware` (strict on `r1-dev`, `r1-xnor-adventure`, sync branches, and PRs;
  uploads firmware images and `SHA256SUMS` as artifacts).
- `py_tests.sh` + CI job `pytests`: runs the fork's openpilot-side Python tests (and upstream's MADS tests) on x86_64 by
  building host copies of `libparams_c.so` and msgq from the committed sources into a cache dir outside the tree.

### Fixed

- `MadsSteeringMode` seeding now matches AdventurePilot: DISENGAGE is seeded only on a never-driven device whose mode is
  still the stock default. The previous code called `Params.put_int()`, which does not exist, so `card` would have
  crashed at startup on any device still on the default mode.
- `uv.lock` restored to upstream (it had been silently re-locked by a local `uv run`); `check_invariants.sh` now pins it.
- `ruff` lint in the screensaver (whitespace and long lines only; the AST is unchanged).

[Unreleased]: https://github.com/caleb-collar/openpilot/compare/r1-v0.1.0...r1-xnor-adventure
[0.1.0]: https://github.com/caleb-collar/openpilot/tree/r1-v0.1.0

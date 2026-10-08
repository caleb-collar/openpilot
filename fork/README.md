# Fork tooling (`fork/`)

Scripts that gate changes to this fork. Everything here is fork-owned, so upstream resyncs never conflict with it.
CI (`.github/workflows/fork-ci.yml`) calls the same scripts, so a green local run predicts a green CI run.

## Prerequisites

* `git`, `gcc`/`gcov` (host compiler for `libsafety`), `python3` ≥ 3.11
* [`uv`](https://docs.astral.sh/uv/) on `PATH`. Install a pinned release and verify its checksum:
  ```bash
  V=0.12.23 A=uv-x86_64-unknown-linux-gnu.tar.gz
  curl -fsSLO "https://github.com/astral-sh/uv/releases/download/$V/$A"
  curl -fsSLO "https://github.com/astral-sh/uv/releases/download/$V/$A.sha256"
  sha256sum -c "$A.sha256" && tar xzf "$A" && install -m 0755 uv-x86_64-unknown-linux-gnu/uv* ~/.local/bin/
  ```

**No sudo is needed.** Python 3.12, `cppcheck`, `scons`, and the Arm GNU Toolchain all come from hash-locked wheels
(`opendbc_repo/uv.lock` and the root `uv.lock`).

## Scripts

| Script | What it does | Typical runtime |
|---|---|---|
| [`scripts/safety_tests.sh`](scripts/safety_tests.sh) | Panda safety gate: every safety-mode unit test, 100% line coverage, MISRA C:2012, and mutation testing. `--quick` skips MISRA and mutation. `--only test_rivian` runs single modules | ~1.5 min on 16 cores |
| [`scripts/build_firmware.sh`](scripts/build_firmware.sh) | Builds `panda_h7`, `panda_jungle_h7`, and `body_h7` from a git ref in a throwaway sparse worktree, then compares the result with the committed binaries. `--verify` fails on mismatch. `--install` copies the build into `panda/board/obj` (Phase 4) | ~30 s |
| [`scripts/fw_compare.py`](scripts/fw_compare.py) | The comparison used by `build_firmware.sh` (see below) | — |
| [`scripts/fw_requirements.py`](scripts/fw_requirements.py) | Writes hash-pinned `scons` + `comma-deps-gcc-arm-none-eabi` requirements from the root `uv.lock` | — |
| [`scripts/check_invariants.sh`](scripts/check_invariants.sh) | Prebuilt-branch hard rules from the plan: upstream `CHANGELOG.md`/`RELEASES.md`/`uv.lock` untouched, no param-key/capnp/native changes, `prebuilt` marker and `launch_openpilot.sh` mode, no LFS or ≥100 MB files, I1 angle-stack files unchanged | ~1 s |
| [`scripts/py_tests.sh`](scripts/py_tests.sh) | Runs the fork's openpilot-side Python tests plus upstream's MADS tests on x86_64. The prebuilt only ships aarch64 `libparams_c.so`/`ipc_pyx.so`, so it builds host copies from the committed sources into `~/.cache/r1-fork/host-native` (never into the tree) and uses a hash-pinned venv from `py_test_requirements.txt` | ~10 s first run |

## Firmware reproducibility

The committed panda firmware can be rebuilt exactly from source. With the pinned toolchain
(Arm GNU Toolchain 13.2.rel1, the same compiler xnor used), a rebuild matches the committed `main.bin` and
bootstub byte for byte, except for the 8-character git SHA embedded in the version string (`DEV-<sha8>-DEBUG`).
The debug signature is deterministic, so `fw_compare.py` checks:

1. `main.bin` and `bootstub.<project>.bin` equal the fresh build after swapping in the new gitversion
2. `<project>.bin.signed` equals the committed `main.bin` re-signed with the debug key

Together these show that the signed firmware a device flashes was built from the safety sources committed next to it.
A change to one constant in `rivian.h` turns check 1 into `DIFFERS` for all three images.

## Safety replay

`opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py` runs on a PC with a small ad-hoc environment
(it needs `openpilot.tools.lib.logreader`):

```bash
cd opendbc_repo/opendbc/safety/tests/safety_replay
PYTHONPATH="$(git rev-parse --show-toplevel):$(git rev-parse --show-toplevel)/opendbc_repo" \
  uv run --no-project --python 3.12 --with pyzmq --with pycapnp==2.1.0 --with zstandard \
  --with requests --with tqdm --with numpy --with pycryptodome --with cffi \
  python replay_drive.py "<dongle>/<route>/<segment>"   # or a local rlog path
```

Public routes download without auth. Private routes need `openpilot/tools/lib/auth.py` or downloaded `rlog` files.

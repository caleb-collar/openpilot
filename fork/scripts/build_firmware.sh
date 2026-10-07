#!/usr/bin/env bash
# Build panda firmware (panda_h7, panda_jungle_h7, body_h7) from a git ref in an isolated,
# sparse worktree, then compare the result with the binaries committed at that ref.
#
# The working tree is never modified unless --install is given. The toolchain (scons + Arm GNU
# Toolchain) is installed without sudo from hash-pinned wheels derived from the root uv.lock
# (see fork/scripts/fw_requirements.py).
#
# Usage: fork/scripts/build_firmware.sh [--ref <rev>] [--out <dir>] [--verify] [--install]
#   --ref      git revision to build (default: HEAD)
#   --out      where to copy built artifacts (default: $TMPDIR/r1t-fw-<sha>)
#   --verify   exit 1 unless the committed firmware at <rev> is reproduced from <rev>'s sources
#              (byte-identical modulo the embedded gitversion; see fork/scripts/fw_compare.py)
#   --install  copy built artifacts into ./panda/board/obj (plan Phase 4). Requires --ref HEAD
#              and no uncommitted changes outside panda/board/obj
#
# Env: FORK_FW_VENV  toolchain venv (default: ~/.cache/r1t-fork/fw-venv)
#      CERT/RELEASE  refused; builds are always debug-signed (plan §2.2)
set -euo pipefail

REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
REF="HEAD"
OUT=""
INSTALL=0
VERIFY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) REF="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --verify) VERIFY=1; shift ;;
    --install) INSTALL=1; shift ;;
    -h|--help) sed -n '2,19p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "${RELEASE:-}" || -n "${CERT:-}" ]]; then
  echo "error: RELEASE/CERT are set; this fork only produces debug-signed firmware" >&2
  exit 2
fi

SHA="$(git -C "$REPO" rev-parse --verify "$REF^{commit}")"
SHORT="$(git -C "$REPO" rev-parse --short=8 "$SHA")"
OUT="${OUT:-${TMPDIR:-/tmp}/r1t-fw-$SHORT}"
PROJECTS=(panda_h7 panda_jungle_h7 body_h7)
ARTIFACTS=()
for p in "${PROJECTS[@]}"; do
  ARTIFACTS+=("$p.bin.signed" "bootstub.$p.bin" "$p/main.elf" "$p/main.bin" "$p/bootstub.elf")
done
ARTIFACTS+=(gitversion.h version cert.h)

if [[ $INSTALL -eq 1 ]]; then
  if [[ "$SHA" != "$(git -C "$REPO" rev-parse HEAD)" ]]; then
    echo "error: --install requires --ref to resolve to HEAD" >&2; exit 2
  fi
  if [[ -n "$(git -C "$REPO" status --porcelain -- . ':!panda/board/obj')" ]]; then
    echo "error: --install requires a clean tree outside panda/board/obj" >&2; exit 2
  fi
fi

# *** toolchain ***
command -v uv >/dev/null || { echo "error: uv is required (see CONTRIBUTING.md)" >&2; exit 2; }
VENV="${FORK_FW_VENV:-$HOME/.cache/r1t-fork/fw-venv}"
REQ="$(mktemp)"
python3 "$REPO/fork/scripts/fw_requirements.py" > "$REQ"
if [[ ! -x "$VENV/bin/python" ]]; then
  uv venv -q --python 3.12 "$VENV"
fi
VIRTUAL_ENV="$VENV" uv pip install -q --require-hashes -r "$REQ"
rm -f "$REQ"
export PATH="$VENV/bin:$PATH"

# *** isolated sparse worktree ***
WT="$(mktemp -d "${TMPDIR:-/tmp}/r1t-fw-wt.XXXXXX")"
cleanup() { git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; }
trap cleanup EXIT
git -C "$REPO" worktree add -q --detach --no-checkout "$WT" "$SHA"
git -C "$WT" sparse-checkout set panda opendbc_repo
git -C "$WT" checkout -q "$SHA"

# Remove committed outputs so every artifact is rebuilt from source.
for a in "${ARTIFACTS[@]}"; do rm -f "$WT/panda/board/obj/$a"; done

TARGETS=()
for p in "${PROJECTS[@]}"; do TARGETS+=("board/obj/$p.bin.signed" "board/obj/bootstub.$p.bin"); done
mkdir -p "$OUT"
echo "building $SHORT in $WT (log: $OUT/build.log)"
if ! (cd "$WT/panda" && PYTHONPATH="$WT/opendbc_repo" scons -Q -j "$(nproc)" "${TARGETS[@]}") > "$OUT/build.log" 2>&1; then
  tail -n 40 "$OUT/build.log" >&2
  echo "error: firmware build failed" >&2
  exit 1
fi

# *** collect + report ***
for a in "${ARTIFACTS[@]}"; do
  mkdir -p "$OUT/$(dirname "$a")"
  cp "$WT/panda/board/obj/$a" "$OUT/$a"
done

echo
echo "== firmware build report =="
echo "ref:        $REF ($SHA)"
echo "gitversion: $(cat "$OUT/version")"
echo "committed:  $(git -C "$REPO" show "$SHA:panda/board/obj/version" 2>/dev/null || echo n/a)"
echo "toolchain:  $(arm-none-eabi-gcc --version | head -1)"
echo "scons:      $(scons --version | grep -m1 -o 'SCons: v[^ ]*' || true)"
echo "committed toolchain: $(git -C "$REPO" cat-file blob "$SHA:panda/board/obj/panda_h7/main.elf" | strings -a | grep -m1 'GCC: ' || true)"
echo "built toolchain:     $(strings -a "$OUT/panda_h7/main.elf" | grep -m1 'GCC: ' || true)"
echo
for p in "${PROJECTS[@]}"; do
  echo "-- $p main.elf sections (committed vs built) --"
  git -C "$REPO" cat-file blob "$SHA:panda/board/obj/$p/main.elf" > "$OUT/.committed-$p.elf"
  if diff <(arm-none-eabi-size -A "$OUT/.committed-$p.elf" | grep -E '^\.(isr_vector|text|rodata|data|bss) ') \
          <(arm-none-eabi-size -A "$OUT/$p/main.elf" | grep -E '^\.(isr_vector|text|rodata|data|bss) '); then
    echo "   sections identical in size"
  fi
  rm -f "$OUT/.committed-$p.elf"
done
(cd "$OUT" && sha256sum "${PROJECTS[@]/%/.bin.signed}" > SHA256SUMS)
echo
COMPARE_ARGS=(--repo "$REPO" --sha "$SHA" --built "$OUT" --panda "$WT/panda")
if [[ $VERIFY -eq 1 ]]; then COMPARE_ARGS+=(--strict); fi
VERIFY_STATUS=0
python3 "$REPO/fork/scripts/fw_compare.py" "${COMPARE_ARGS[@]}" || VERIFY_STATUS=$?
echo
echo "artifacts: $OUT"

if [[ $INSTALL -eq 1 ]]; then
  for a in "${ARTIFACTS[@]}"; do cp "$OUT/$a" "$REPO/panda/board/obj/$a"; done
  echo "installed into $REPO/panda/board/obj (review with: git status panda/board/obj)"
fi
exit "$VERIFY_STATUS"

#!/usr/bin/env bash
# Enforce the fork's prebuilt-branch invariants (INTEGRATION_PLAN.md §1.2, §2.2, §3) on everything
# changed since the branch root (the upstream xnor rx-dev prebuilt).
#
# Usage: fork/scripts/check_invariants.sh [<rev>]   (default: HEAD)
set -euo pipefail

REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$REPO"
REV="${1:-HEAD}"
ROOT="$(git rev-list --max-parents=0 "$REV" | tail -n1)"
CHANGED="$(git diff --name-only "$ROOT" "$REV")"
fail=0
err() { echo "::error::$*"; fail=1; }
ok() { echo "ok: $*"; }

echo "branch root (upstream prebuilt): $(git log -1 --format='%h %s' "$ROOT")"
echo "checking $REV ($(git rev-parse --short "$REV"))"

# I6 + D2: upstream-owned files that change every release stay byte-identical.
for f in CHANGELOG.md RELEASES.md; do
  if grep -qxF "$f" <<<"$CHANGED"; then err "$f is upstream-owned and must not be edited (plan I6/D2)"; else ok "$f untouched"; fi
done

# §2.2: param keys and cereal schema are compiled into the prebuilt aarch64 binaries.
if grep -qxF openpilot/common/params_keys.h <<<"$CHANGED"; then err "params_keys.h changed (no new param keys, plan D4)"; else ok "params_keys.h untouched"; fi
if grep -E '\.capnp$' <<<"$CHANGED" | grep -q .; then
  err "capnp schema changed (no cereal changes, plan D4): $(grep -E '\.capnp$' <<<"$CHANGED" | tr '\n' ' ')"
else
  ok "no capnp schema changes"
fi

# §2.2: no openpilot native sources or prebuilt binaries (would need a full aarch64 rebuild).
native="$(grep -E '\.(cc|cpp|hpp|so|a|o)$' <<<"$CHANGED" || true)"
if [[ -n "$native" ]]; then err "native sources/binaries changed: $(tr '\n' ' ' <<<"$native")"; else ok "no native sources or binaries changed"; fi

# §3: installer/boot requirements.
if git cat-file -e "$REV:prebuilt" 2>/dev/null; then ok "prebuilt marker present"; else err "prebuilt marker missing"; fi
mode="$(git ls-tree "$REV" launch_openpilot.sh | awk '{print $1}')"
if [[ "$mode" == "100755" ]]; then ok "launch_openpilot.sh is 100755"; else err "launch_openpilot.sh mode is '${mode:-missing}', expected 100755"; fi

# §3: no LFS pointers, nothing at or above GitHub's 100 MB limit.
big="$(git ls-tree -r -l "$REV" | awk '$4 >= 100*1024*1024 {print $5}')"
if [[ -n "$big" ]]; then err "files >= 100 MB: $big"; else ok "no files >= 100 MB"; fi
lfs=""
while IFS= read -r -d '' f; do
  if git cat-file blob "$REV:$f" | head -c 100 | grep -qa '^version https://git-lfs.github.com/spec/v1'; then lfs+="$f "; fi
done < <(git diff --name-only -z --diff-filter=ACMR "$ROOT" "$REV")
if [[ -n "$lfs" ]]; then err "LFS pointer files: $lfs"; else ok "no LFS pointers in changed files"; fi

# I1: xnor's angle stack stays identical to rx-dev.
I1_FILES=(
  opendbc_repo/opendbc/car/rivian/carstate.py
  opendbc_repo/opendbc/car/rivian/carcontroller.py
  opendbc_repo/opendbc/car/rivian/ext_controller.py
  opendbc_repo/opendbc/car/rivian/riviancan.py
)
for f in "${I1_FILES[@]}"; do
  if grep -qxF "$f" <<<"$CHANGED"; then err "I1 file changed vs rx-dev: $f"; else ok "I1 unchanged: ${f#opendbc_repo/opendbc/car/}"; fi
done

exit "$fail"

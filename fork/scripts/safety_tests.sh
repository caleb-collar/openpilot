#!/usr/bin/env bash
# Run the opendbc panda-safety checks that gate every safety change (plan Phase 1.3 / Phase 2.3).
#
#   1. unit tests: every safety mode, built from source with host gcc via cffi (libsafety)
#   2. line coverage: 100% of safety sources (gcovr, same gate as upstream's safety/tests/test.sh)
#   3. MISRA C:2012 (cppcheck from hash-locked wheels, via upstream's test_misra.sh)
#   4. mutation testing: every mutant must be killed (upstream known survivors excepted)
#
# Usage: fork/scripts/safety_tests.sh [--quick] [--only <test_module>...]
#   --quick   unit tests + coverage only (skip MISRA and mutation)
#   --only    run only the named unittest modules (e.g. test_rivian test_defaults); implies no
#             coverage gate, since coverage needs the full suite
set -euo pipefail

REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
ODBC="$REPO/opendbc_repo"
TESTS="$ODBC/opendbc/safety/tests"
QUICK=0
ONLY=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick) QUICK=1; shift ;;
    --only) shift; while [[ $# -gt 0 && "$1" != --* ]]; do ONLY+=("$1"); shift; done ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v uv >/dev/null || { echo "error: uv is required (see CONTRIBUTING.md)" >&2; exit 2; }
export UV_PROJECT_ENVIRONMENT="$ODBC/.venv"
(cd "$ODBC" && uv sync -q --locked --all-extras --all-groups)
# shellcheck disable=SC1091
source "$ODBC/.venv/bin/activate"
export PYTHONPATH="$ODBC"

step() { printf '\n\033[1;34m== %s ==\033[0m\n' "$*"; }

cd "$TESTS"
rm -f libsafety/*.gcda

if [[ ${#ONLY[@]} -gt 0 ]]; then
  step "unit tests (${ONLY[*]})"
  python -m unittest "${ONLY[@]}"
  exit 0
fi

step "unit tests (all safety modes)"
python -m unittest discover -s .

step "line coverage (100% required)"
gcovr -r "$TESTS/../" --gcov-executable gcov -d --fail-under-line=100 -e '^libsafety' | tail -n 4

if [[ $QUICK -eq 1 ]]; then
  echo -e "\nquick mode: skipped MISRA and mutation"
  exit 0
fi

step "MISRA C:2012"
"$TESTS/misra/test_misra.sh"

step "mutation"
(cd "$ODBC" && python opendbc/safety/tests/mutation.py -j "$(( $(nproc) > 1 ? $(nproc) - 1 : 1 ))" | tail -n 25)

echo -e "\n\033[1;32mall safety checks passed\033[0m"

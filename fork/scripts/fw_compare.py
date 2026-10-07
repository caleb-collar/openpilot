#!/usr/bin/env python3
"""Compare freshly built panda firmware with the binaries committed at a git ref.

The build is reproducible: with the pinned toolchain, a rebuild differs from the committed binary
only in the embedded gitversion string (``DEV-<sha8>-DEBUG``). This script checks, per project:

  * ``main.bin`` and ``bootstub.<project>.bin`` equal the build after swapping the gitversion
  * ``<project>.bin.signed`` equals the committed ``main.bin`` re-signed with the debug key

Together these prove the committed, signed firmware was built from the committed safety sources
(plan §3 item 6). Exit status is 1 on any mismatch when ``--strict`` is given.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECTS = ("panda_h7", "panda_jungle_h7", "body_h7")


def git_blob(repo: Path, sha: str, path: str) -> bytes | None:
  r = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", f"{sha}:{path}"], capture_output=True)
  return r.stdout if r.returncode == 0 else None


def resign(sign_py: Path, cert: Path, main_bin: bytes) -> bytes:
  with tempfile.TemporaryDirectory() as tmp:
    src, dst = Path(tmp, "main.bin"), Path(tmp, "signed")
    src.write_bytes(main_bin)
    subprocess.run([sys.executable, str(sign_py), str(src), str(dst), str(cert)], check=True,
                   capture_output=True, env={**os.environ, "SETLEN": "1"})
    return dst.read_bytes()


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--repo", type=Path, required=True)
  ap.add_argument("--sha", required=True, help="commit whose committed binaries are the reference")
  ap.add_argument("--built", type=Path, required=True, help="directory with freshly built board/obj artifacts")
  ap.add_argument("--panda", type=Path, required=True, help="panda source dir (for sign.py and the debug cert)")
  ap.add_argument("--strict", action="store_true", help="exit 1 on any mismatch")
  args = ap.parse_args()

  obj = "panda/board/obj"
  committed_ver = git_blob(args.repo, args.sha, f"{obj}/version")
  built_ver = (args.built / "version").read_bytes()
  if committed_ver is None:
    print("no committed firmware at this ref")
    return 1 if args.strict else 0
  if len(committed_ver) != len(built_ver):
    print(f"gitversion length differs: {committed_ver!r} vs {built_ver!r}")
    return 1

  ok = True
  print(f"gitversion committed={committed_ver.decode()} built={built_ver.decode()}")
  print(f"{'check':<44} result")
  for p in PROJECTS:
    for rel in (f"{p}/main.bin", f"bootstub.{p}.bin"):
      committed = git_blob(args.repo, args.sha, f"{obj}/{rel}")
      built = (args.built / rel).read_bytes()
      if committed is None:
        res = "MISSING (not committed)"
        ok = False
      elif committed == built:
        res = "identical"
      elif committed.replace(committed_ver, built_ver) == built:
        res = "identical modulo gitversion"
      else:
        res = "DIFFERS"
        ok = False
      print(f"{rel + ' == build':<44} {res}")

    committed_main = git_blob(args.repo, args.sha, f"{obj}/{p}/main.bin")
    committed_signed = git_blob(args.repo, args.sha, f"{obj}/{p}.bin.signed")
    if committed_main is None or committed_signed is None:
      res = "MISSING (not committed)"
      ok = False
    else:
      same = resign(args.panda / "board/crypto/sign.py", args.panda / "board/certs/debug", committed_main) == committed_signed
      res = "identical" if same else "DIFFERS"
      ok &= same
    print(f"{p + '.bin.signed == debug-sign(main.bin)':<44} {res}")

  print("RESULT:", "committed firmware matches committed sources" if ok else "MISMATCH between committed firmware and sources")
  return 0 if ok or not args.strict else 1


if __name__ == "__main__":
  raise SystemExit(main())

# Contributing to `caleb-collar/openpilot` (r1t-xnor-adventure)

This fork carries a small set of Rivian R1T changes on top of xnor-tech's `rx-dev` prebuilt.
Read [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) before changing anything that touches lateral control or panda safety.

## Setup

```bash
git clone git@github.com:caleb-collar/openpilot.git && cd openpilot
git switch r1t-xnor-adventure
git config core.hooksPath .githooks                     # enables the Conventional Commits hook
git remote add upstream git@github.com:xnor-tech/openpilot.git
git remote add adventure git@github.com:AdventurePilotDev/openpilot.git
git remote set-url --push upstream DISABLED             # never push to the sources
git remote set-url --push adventure DISABLED
```

## Commit messages: Conventional Commits 1.0.0

```
<type>(<scope>)!: <description>

[optional body: what changed and why, wrapped at ~72 chars]

[optional footers, e.g. BREAKING CHANGE: ..., Refs: #12, Route: <comma route id>]
```

| Type | Use for |
|---|---|
| `feat` | New user-visible behavior (e.g. a stalk gesture) |
| `fix` | Bug fix |
| `perf` | Performance improvement |
| `refactor` | Code change with no behavior change |
| `test` | Adding or fixing tests only |
| `build` | Firmware or binary rebuilds, build tooling (`build(panda): ...`) |
| `ci` | GitHub Actions / CI scripts |
| `docs` | Documentation only |
| `style` | Formatting only |
| `chore` | Maintenance, including upstream resyncs (`chore(sync): ...`) |
| `revert` | Reverting a previous commit |

**Scopes** (lowercase): `rivian`, `safety`, `mads`, `panda`, `sync`, `docs`, `ci`, `tests`, `deps`.

Rules (enforced by [`.githooks/commit-msg`](.githooks/commit-msg) and CI):
* The header matches `type(scope)!: description`, is 100 characters or fewer, and does not end with a period.
* Put a blank line between the header and the body.
* Mark breaking changes with `!` and/or a `BREAKING CHANGE:` footer.
* Safety-relevant commits should reference the on-road route(s) used for validation in a `Route:` footer.

Examples:
```
feat(rivian): map gear-stalk UP_2 to MADS lateral disengage
fix(safety): reset MADS heartbeat mismatch counter on exit
build(panda): rebuild firmware with rivian stalk MADS safety
chore(sync): rebase onto xnor-tech/rx-dev 8a627abb0
```

The upstream prebuilt root commit (`openpilot rx-dev prebuilt`) is exempt. CI only lints commits after the branch root.

## Changelog: Keep a Changelog 1.1.0

* Fork changes go in [`FORK_CHANGELOG.md`](FORK_CHANGELOG.md) under `## [Unreleased]`, grouped as
  `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`.
* **Do not edit the root `CHANGELOG.md`.** It belongs to upstream sunnypilot and is parsed on the device for
  release notes (`openpilot/common/version.py`, `openpilot/system/updated/updated.py`).
* Versions follow [SemVer](https://semver.org/) for the fork itself, tagged `r1t-vX.Y.Z`.

## Branches

* `r1t-xnor-adventure` is the **device branch**. Installed cars auto-update from it. Only promote verified work, by fast-forward.
* Develop on `feat/<topic>` / `fix/<topic>` (or the `r1t-dev` integration branch). Keep history linear (rebase, no merges).
* The panda firmware rebuild is always a single, final `build(panda): ...` commit (see the plan, Phase 4 / Phase 8).

## Hard rules for this prebuilt branch

* No new param keys (`params_keys.h` is compiled into prebuilt aarch64 libraries).
* No cereal schema changes.
* No loosening of panda safety limits. Every safety change needs tests, MISRA, mutation, and replay (plan Phase 2).
* Never merge or cherry-pick `adventure/stg-a` wholesale. It shares no history with `rx-dev`.

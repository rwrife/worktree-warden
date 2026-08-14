# worktree-warden

A local developer utility to discover Git worktrees under a folder and automatically purge stale worktrees after a configurable TTL.

## Overview

`worktree-warden` helps you keep disk usage and branch clutter under control when you use many Git worktrees.

Point it at a root folder (for example `~/repos`), and it will:

- discover repositories and linked worktrees,
- record worktree metadata (path, branch, HEAD, creation timestamp),
- show which worktrees are stale according to TTL,
- purge eligible worktrees safely (with dry-run and policy checks).

## Motivation

Worktrees are excellent for parallel development, but they often accumulate:

- forgotten feature branches,
- stale experiment directories,
- large build artifacts tied to old worktrees.

Manual cleanup is error-prone and easy to postpone. `worktree-warden` makes cleanup predictable and automatable.

## Use cases

- **Solo developers:** keep laptop SSD usage under control.
- **Teams using worktree-heavy workflows:** enforce cleanup windows (for example, remove worktrees older than 14 days).
- **Autonomous coding agents:** create and clean temporary worktrees consistently.
- **CI/devbox maintenance:** scheduled pruning with an audit trail.

## Features (MVP target)

- Recursive discovery from a root path.
- Worktree inventory export (table + JSON) via `scan` and `report`.
- TTL policy (`--ttl-days X`) based on first-seen UTC metadata with branch/path exclusions.
- Safe purge with:
  - `--dry-run`
  - skip protected branches (`main`, `master`, `release/*`)
  - skip dirty worktrees unless `--force`
  - path safety checks under allowed roots
- Optional scheduled cleanup mode.
- Optional trash/recycle-bin mode (platform-dependent) before hard delete.

## How to use

```bash
# discover worktrees
worktree-warden scan --root ~/repos

# discover with machine-readable output
worktree-warden scan --root ~/repos --json

# generate a versioned JSON inventory report
worktree-warden report --root ~/repos --json

# evaluate TTL eligibility while excluding protected branches and paths
worktree-warden scan --root ~/repos --ttl-days 21 \
  --exclude-branch main \
  --exclude-branch 'release/*' \
  --path-allowlist '~/repos/*' \
  --path-denylist '*archive*' \
  --json

# optional metadata file override (defaults to <root>/.worktree-warden/metadata.json)
worktree-warden scan --root ~/repos --state-file ~/.local/state/worktree-warden/metadata.json

# preview what would be deleted after 21 days
worktree-warden purge --root ~/repos --ttl-days 21 --dry-run

# perform cleanup
worktree-warden purge --root ~/repos --ttl-days 21

# force-remove dirty worktrees that pass other guardrails
worktree-warden purge --root ~/repos --ttl-days 21 --force

# append structured JSONL audit events for each purge decision
worktree-warden purge --root ~/repos --ttl-days 21 \
  --audit-log ~/.local/state/worktree-warden/purge-audit.jsonl \
  --json
```

## Scheduled cleanup (automation + audit trail)

Use your OS scheduler to run `purge` on a cadence and append structured audit events.

### Linux/macOS (`cron`) example

Run every day at 03:15 local time:

```cron
15 3 * * * /usr/bin/env bash -lc 'worktree-warden purge --root ~/repos --ttl-days 21 --audit-log ~/.local/state/worktree-warden/purge-audit.jsonl --json'
```

### Windows Task Scheduler example

Program/script:

```text
powershell.exe
```

Arguments:

```text
-NoProfile -Command "worktree-warden purge --root $HOME/repos --ttl-days 21 --audit-log $HOME/.worktree-warden/purge-audit.jsonl --json"
```

### Audit log shape

Each audit line is JSON (`.jsonl`) and includes run metadata plus the individual purge decision:

- `record.path`: worktree path
- `record.action`: `removed`, `would-remove`, `skipped`, or `error`
- `record.reason`: skip/failure reason (for example `protected-branch`, `dirty-worktree`)

This gives operations-friendly logs that explicitly show deleted paths and skip reasons for every run.

## Verification

### Local verification

```bash
# full suite
pytest

# focused suites used for TTL + safety guardrails
pytest tests/test_parser.py tests/test_ttl_policy.py tests/test_purge_pipeline.py
```

### CI baseline

GitHub Actions runs the same pytest suite on:

- `ubuntu-latest`
- `macos-latest`
- `windows-latest`

See `.github/workflows/ci.yml`.

## CLI contract

### Exit codes

- `0`: command completed successfully.
- `1`: runtime failure (for example git invocation errors or invalid runtime policy values).
- `2`: CLI usage/argument error (argparse semantics).
- `3`: purge completed but one or more eligible removals failed (`action=error` present in output).

### JSON schema

- `scan --json` emits a raw array of worktree records.
- `report --json` emits a versioned envelope with `schema_version`, `kind`, `root`, and `records`.
- Current schema docs: [`docs/json-schema.md`](docs/json-schema.md) (version `1`).

## Safety model

Before deleting a worktree, `worktree-warden` should verify configurable guardrails:

- branch is not protected,
- worktree has no uncommitted changes (unless forced),
- branch is merged (optional strict mode),
- path is inside allowed root(s).

## Platform support

- Windows 10/11
- macOS
- Linux (best effort)

## Status

Initial implementation now includes:

- `worktree-warden scan --root <path>` recursive discovery,
- porcelain parser support for branch, detached, and bare records,
- persistent metadata store for `first_seen_at`, `last_seen_at`, and `last_activity_at`,
- TTL evaluator with UTC day-boundary logic and branch/path exclusions,
- safe purge pipeline with dry-run, protected-branch rejection, dirty-worktree checks, and allowed-root enforcement,
- `report` command with a versioned JSON envelope,
- documented CLI exit code semantics for automation,
- unit/integration tests for parser, nested-repo discovery, metadata idempotency, and purge guardrails.

Remaining milestones are tracked in GitHub issues.

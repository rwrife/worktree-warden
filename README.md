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
- Worktree inventory export (table + JSON).
- TTL policy (`--ttl-days X`) based on creation time.
- Safe purge with:
  - `--dry-run`
  - skip protected branches (`main`, `master`, `release/*`)
  - optional skip when unmerged changes exist
- Optional scheduled cleanup mode.
- Optional trash/recycle-bin mode (platform-dependent) before hard delete.

## How to use (planned CLI)

```bash
# discover worktrees
worktree-warden scan --root ~/repos

# discover with machine-readable output
worktree-warden scan --root ~/repos --json

# preview what would be deleted after 21 days
worktree-warden purge --root ~/repos --ttl-days 21 --dry-run

# perform cleanup
worktree-warden purge --root ~/repos --ttl-days 21
```

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

Project scaffold created by auto tool-lab. Core implementation is tracked in issues.

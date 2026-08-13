# PLAN — worktree-warden

## Goal

Build a reliable utility that identifies Git worktrees under a target root and purges stale ones automatically after a configurable TTL.

## Non-goals (initial)

- Remote GitHub API management (repo settings/PR automation).
- Full GUI in v1 (CLI-first).
- Cross-machine sync of cleanup policy.

## Milestone 1 — Discovery + inventory

- Implement root scanner that finds Git repos and attached worktrees.
- Parse `git worktree list --porcelain` robustly.
- Normalize metadata:
  - absolute path
  - branch / detached HEAD state
  - commit SHA
  - creation timestamp (from local metadata store)
  - last activity timestamp (optional)
- Output: table and JSON.

## Milestone 2 — TTL policy engine

- Add policy evaluator:
  - stale when `age_days >= ttl_days`
  - exclusions for branch patterns
  - path allowlist/denylist
- Add policy config file support.

## Milestone 3 — Safe purge

- Implement dry-run first.
- Purge stale worktrees using `git worktree remove` when possible.
- Fallback removal strategy with explicit warnings.
- Add safety checks:
  - uncommitted changes detection
  - optional merged-branch requirement
  - protected branch rejection

## Milestone 4 — Automation

- Scheduled local cleanup mode (cron/task scheduler examples).
- Structured logs and cleanup report output.
- Exit codes suitable for automation.

## Milestone 5 — Packaging & DX

- Cross-platform install instructions.
- Binary/packaged release workflow.
- Shell completions and docs examples.

## Quality gates

- Unit tests for scanner, parser, and policy evaluator (`pytest tests/test_parser.py tests/test_ttl_policy.py`).
- Integration tests against temporary repos/worktrees, including dirty worktree and protected branch safety fixtures (`pytest tests/test_purge_pipeline.py`).
- Deterministic fixture-based tests for TTL boundaries.
- CI matrix runs the full pytest suite on Linux, macOS, and Windows.

## Open questions

1. Best default source for creation time:
   - first-seen timestamp in local DB,
   - file system creation time,
   - fallback heuristics.
2. Whether to require merged-branch checks by default.
3. Trash/recycle-bin support parity across platforms.

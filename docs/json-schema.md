# worktree-warden JSON schema

## Versioning policy

This document defines the JSON contract for CLI output consumed by automation.

- Current schema version: **`1`**
- Backward-incompatible JSON changes must increment the schema version.

## `report --json` payload (version `1`)

`report --json` emits an envelope object:

```json
{
  "schema_version": "1",
  "kind": "worktree-warden.report",
  "root": "/absolute/path/to/root",
  "records": [
    {
      "repo_path": "/absolute/path/to/repo",
      "path": "/absolute/path/to/worktree",
      "head": "<sha-or-null>",
      "branch_ref": "refs/heads/main",
      "detached": false,
      "bare": false,
      "locked_reason": null,
      "prunable_reason": null,
      "first_seen_at": "2026-01-01T10:00:00Z",
      "last_seen_at": "2026-01-01T10:00:00Z",
      "last_activity_at": "2026-01-01T10:00:00Z",
      "age_days": 7,
      "purge_eligible": true,
      "purge_block_reason": null,
      "extra": {},
      "branch": "main"
    }
  ]
}
```

### Field notes

- `schema_version` — schema contract version for report output.
- `kind` — stable identifier for payload type (`worktree-warden.report`).
- `root` — resolved absolute root path used during discovery.
- `records` — array of worktree records.

## `scan --json` payload

`scan --json` emits the same worktree record objects directly as an array (no envelope).

## `purge --json` payload

`purge --json` emits an array of purge action entries:

- `repo_path`, `path`, `branch`, `age_days`, `purge_eligible`
- `action` (`skipped`, `would-remove`, `removed`, `error`)
- `reason` and optional `detail`

## `purge --audit-log` JSONL events

When `purge` is invoked with `--audit-log <file>`, one JSON event is appended per
purge record. Each line in the file is a standalone JSON object:

```json
{
  "schema_version": "1",
  "kind": "worktree-warden.purge.audit",
  "executed_at": "2026-01-01T10:00:00Z",
  "root": "/absolute/path/to/root",
  "ttl_days": 21,
  "dry_run": false,
  "force": false,
  "record": {
    "repo_path": "/absolute/path/to/repo",
    "path": "/absolute/path/to/worktree",
    "branch": "feature/demo",
    "age_days": 34,
    "purge_eligible": true,
    "action": "removed",
    "reason": null,
    "detail": null
  }
}
```

This format is scheduler-friendly for cron/Task Scheduler pipelines and keeps
deleted paths plus skip reasons in a machine-readable audit trail.

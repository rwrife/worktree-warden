from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(repo_path: Path) -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init"], cwd=repo_path)
    (repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=repo_path)
    _run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo_path,
    )


def _create_worktree(repo_path: Path, *, branch: str, path: Path) -> Path:
    _run(["git", "branch", branch], cwd=repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", str(path), branch], cwd=repo_path)
    return path.resolve()


def _purge_json(project_root: Path, *args: str) -> list[dict[str, object]]:
    result = subprocess.run(
        [sys.executable, "-m", "worktree_warden", "purge", *args, "--json"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _entry_for_path(payload: list[dict[str, object]], target: Path) -> dict[str, object]:
    resolved_target = target.resolve()
    return next(item for item in payload if Path(str(item["path"])).resolve() == resolved_target)


def _read_audit_events(audit_log_path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in audit_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _audit_event_for_path(events: list[dict[str, Any]], target: Path) -> dict[str, Any]:
    resolved_target = target.resolve()
    for event in events:
        record = cast(dict[str, Any], event["record"])
        if Path(str(record["path"])).resolve() == resolved_target:
            return event
    raise AssertionError(f"No audit event found for {resolved_target}")


def test_purge_dry_run_previews_actions_without_deleting(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    stale_worktree = _create_worktree(
        repo,
        branch="feature/remove-me",
        path=root / "worktrees" / "remove-me",
    )

    payload = _purge_json(project_root, "--root", str(root), "--ttl-days", "0", "--dry-run")
    stale_entry = _entry_for_path(payload, stale_worktree)

    assert stale_entry["action"] == "would-remove"
    assert stale_entry["reason"] is None
    assert stale_worktree.exists()


def test_purge_blocks_dirty_worktree_without_force(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    dirty_worktree = _create_worktree(
        repo,
        branch="feature/dirty",
        path=root / "worktrees" / "dirty",
    )
    (dirty_worktree / "README.md").write_text("dirty changes\n", encoding="utf-8")

    payload = _purge_json(project_root, "--root", str(root), "--ttl-days", "0")
    dirty_entry = _entry_for_path(payload, dirty_worktree)

    assert dirty_entry["action"] == "skipped"
    assert dirty_entry["reason"] == "dirty-worktree"
    assert dirty_worktree.exists()

    forced_payload = _purge_json(
        project_root,
        "--root",
        str(root),
        "--ttl-days",
        "0",
        "--force",
    )
    forced_entry = _entry_for_path(forced_payload, dirty_worktree)

    assert forced_entry["action"] == "removed"
    assert forced_entry["reason"] is None
    assert not dirty_worktree.exists()


def test_purge_respects_protected_branch_and_allowed_root_guardrails(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    inside_worktree = _create_worktree(
        repo,
        branch="feature/inside",
        path=root / "worktrees" / "inside",
    )
    protected_worktree = _create_worktree(
        repo,
        branch="release/1.0",
        path=root / "worktrees" / "release-1-0",
    )
    outside_worktree = _create_worktree(
        repo,
        branch="feature/outside",
        path=tmp_path / "outside" / "feature-outside",
    )

    payload = _purge_json(project_root, "--root", str(root), "--ttl-days", "0")

    inside_entry = _entry_for_path(payload, inside_worktree)
    assert inside_entry["action"] == "removed"
    assert inside_entry["reason"] is None
    assert not inside_worktree.exists()

    protected_entry = _entry_for_path(payload, protected_worktree)
    assert protected_entry["action"] == "skipped"
    assert protected_entry["reason"] == "protected-branch"
    assert protected_worktree.exists()

    outside_entry = _entry_for_path(payload, outside_worktree)
    assert outside_entry["action"] == "skipped"
    assert outside_entry["reason"] == "path-outside-allowed-root"
    assert outside_worktree.exists()


def test_purge_audit_log_captures_removed_paths_and_skip_reasons(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    removable_worktree = _create_worktree(
        repo,
        branch="feature/removable",
        path=root / "worktrees" / "removable",
    )
    protected_worktree = _create_worktree(
        repo,
        branch="release/1.0",
        path=root / "worktrees" / "release-1-0",
    )
    audit_log_path = tmp_path / "logs" / "purge-audit.jsonl"

    _purge_json(
        project_root,
        "--root",
        str(root),
        "--ttl-days",
        "0",
        "--audit-log",
        str(audit_log_path),
    )

    events = _read_audit_events(audit_log_path)
    removable_event = _audit_event_for_path(events, removable_worktree)
    protected_event = _audit_event_for_path(events, protected_worktree)
    removable_record = cast(dict[str, Any], removable_event["record"])
    protected_record = cast(dict[str, Any], protected_event["record"])

    assert removable_event["kind"] == "worktree-warden.purge.audit"
    assert removable_record["action"] == "removed"
    assert removable_record["reason"] is None
    assert removable_record["path"] == str(removable_worktree)

    assert protected_event["kind"] == "worktree-warden.purge.audit"
    assert protected_record["action"] == "skipped"
    assert protected_record["reason"] == "protected-branch"
    assert protected_record["path"] == str(protected_worktree)

    assert all("executed_at" in event for event in events)
    assert all(event["root"] == str(root.resolve()) for event in events)
    assert not removable_worktree.exists()
    assert protected_worktree.exists()

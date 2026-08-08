from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from worktree_warden.discovery import discover_worktrees


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _commit(repo_path: Path, message: str) -> None:
    _run(["git", "add", "-A"], cwd=repo_path)
    _run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            message,
        ],
        cwd=repo_path,
    )


def _init_repo(repo_path: Path) -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init"], cwd=repo_path)
    (repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    _commit(repo_path, "init")


def _record_for_repo(records, repo: Path):
    target = repo.resolve()
    return next(r for r in records if r.path == target)


def test_metadata_first_seen_and_idempotent_rescan(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "repo"
    state_file = tmp_path / "state.json"
    _init_repo(repo)

    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    first_scan = discover_worktrees(root, metadata_store_path=state_file, now=t1)
    first_record = _record_for_repo(first_scan, repo)

    assert first_record.first_seen_at == "2026-01-01T10:00:00Z"
    assert first_record.last_seen_at == "2026-01-01T10:00:00Z"
    assert first_record.last_activity_at == "2026-01-01T10:00:00Z"

    t2 = datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    second_scan = discover_worktrees(root, metadata_store_path=state_file, now=t2)
    second_record = _record_for_repo(second_scan, repo)

    assert second_record.first_seen_at == "2026-01-01T10:00:00Z"
    assert second_record.last_seen_at == "2026-01-02T10:00:00Z"
    assert second_record.last_activity_at == "2026-01-01T10:00:00Z"

    (repo / "README.md").write_text("hello again\n", encoding="utf-8")
    _commit(repo, "update head")

    t3 = datetime(2026, 1, 3, 10, 0, 0, tzinfo=timezone.utc)
    third_scan = discover_worktrees(root, metadata_store_path=state_file, now=t3)
    third_record = _record_for_repo(third_scan, repo)

    assert third_record.first_seen_at == "2026-01-01T10:00:00Z"
    assert third_record.last_seen_at == "2026-01-03T10:00:00Z"
    assert third_record.last_activity_at == "2026-01-03T10:00:00Z"

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    entry = payload["worktrees"][str(repo.resolve())]
    assert entry["first_seen_at"] == "2026-01-01T10:00:00Z"
    assert entry["last_seen_at"] == "2026-01-03T10:00:00Z"
    assert entry["last_activity_at"] == "2026-01-03T10:00:00Z"

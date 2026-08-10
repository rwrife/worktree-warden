from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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

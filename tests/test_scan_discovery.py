from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from worktree_warden.discovery import discover_worktrees


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


def test_recursive_discovery_finds_nested_repo_worktrees(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "nested" / "sample-repo"
    _init_repo(repo)

    _run(["git", "branch", "feature/a"], cwd=repo)

    linked_worktree = root / "worktrees" / "sample-feature-a"
    linked_worktree.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", str(linked_worktree), "feature/a"], cwd=repo)

    records = discover_worktrees(root)
    paths = {r.path for r in records}

    assert repo.resolve() in paths
    assert linked_worktree.resolve() in paths


def test_scan_cli_json_output(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worktree_warden",
            "scan",
            "--root",
            str(root),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    payload = json.loads(result.stdout)
    paths = {Path(item["path"]).resolve() for item in payload}
    assert repo.resolve() in paths

    repo_row = next(item for item in payload if Path(item["path"]).resolve() == repo.resolve())
    assert repo_row["first_seen_at"].endswith("Z")
    assert repo_row["last_seen_at"].endswith("Z")
    assert repo_row["last_activity_at"].endswith("Z")

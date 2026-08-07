from __future__ import annotations

import subprocess
from pathlib import Path

from .models import WorktreeRecord
from .parser import parse_worktree_porcelain


class GitCommandError(RuntimeError):
    pass


def _run_git(path: Path, *args: str) -> str:
    cmd = ["git", "-C", str(path), *args]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise GitCommandError(
            f"git command failed ({' '.join(cmd)}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def discover_git_candidates(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    candidates: list[Path] = []

    for dirpath, dirnames, _ in __import__("os").walk(root):
        path = Path(dirpath)

        if path.name == ".git":
            dirnames.clear()
            continue

        git_marker = path / ".git"
        if git_marker.exists():
            candidates.append(path)

        # do not recurse into git internals
        if ".git" in dirnames:
            dirnames.remove(".git")

    return candidates


def _common_dir_for_repo(path: Path) -> Path:
    out = _run_git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return Path(out).resolve()


def discover_worktrees(root: Path) -> list[WorktreeRecord]:
    """Discover repos recursively and return normalized worktree records."""
    candidates = discover_git_candidates(root)
    discovered: list[WorktreeRecord] = []
    processed_common_dirs: set[Path] = set()

    for candidate in candidates:
        try:
            common_dir = _common_dir_for_repo(candidate)
        except GitCommandError:
            continue

        if common_dir in processed_common_dirs:
            continue
        processed_common_dirs.add(common_dir)

        repo_path = common_dir.parent if common_dir.name == ".git" else candidate

        porcelain = _run_git(candidate, "worktree", "list", "--porcelain")
        discovered.extend(parse_worktree_porcelain(porcelain, repo_path=repo_path))

    discovered.sort(key=lambda r: (str(r.repo_path), str(r.path)))
    return discovered

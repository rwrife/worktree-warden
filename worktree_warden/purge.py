from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from subprocess import run
from typing import Sequence

from .discovery import GitCommandError, discover_worktrees
from .policy import TtlPolicy

DEFAULT_PROTECTED_BRANCHES: tuple[str, ...] = ("main", "master", "release/*")


@dataclass(slots=True)
class PurgeLogEntry:
    repo_path: Path
    path: Path
    branch: str | None
    age_days: int | None
    purge_eligible: bool
    action: str
    reason: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_path": str(self.repo_path),
            "path": str(self.path),
            "branch": self.branch,
            "age_days": self.age_days,
            "purge_eligible": self.purge_eligible,
            "action": self.action,
            "reason": self.reason,
            "detail": self.detail,
        }


def _run_git(path: Path, *args: str) -> str:
    cmd = ["git", "-C", str(path), *args]
    proc = run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise GitCommandError(
            f"git command failed ({' '.join(cmd)}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def _is_under_any_root(path: Path, roots: Sequence[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_dirty_worktree(path: Path) -> bool:
    output = _run_git(path, "status", "--porcelain")
    return bool(output.strip())


def _is_protected_branch(branch: str | None, protected_branches: Sequence[str]) -> bool:
    if branch is None:
        return False
    return any(fnmatch(branch, pattern) for pattern in protected_branches)


def purge_worktrees(
    root: Path,
    *,
    ttl_policy: TtlPolicy,
    metadata_store_path: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    protected_branches: Sequence[str] = DEFAULT_PROTECTED_BRANCHES,
    allowed_roots: Sequence[Path] | None = None,
) -> list[PurgeLogEntry]:
    resolved_root = root.expanduser().resolve()
    resolved_allowed_roots = (
        [candidate.expanduser().resolve() for candidate in allowed_roots]
        if allowed_roots
        else [resolved_root]
    )

    records = discover_worktrees(
        resolved_root,
        metadata_store_path=metadata_store_path,
        ttl_policy=ttl_policy,
    )

    actions: list[PurgeLogEntry] = []

    for rec in records:
        resolved_path = rec.path.resolve()
        repo_path = rec.repo_path.resolve()
        base = PurgeLogEntry(
            repo_path=repo_path,
            path=resolved_path,
            branch=rec.branch,
            age_days=rec.age_days,
            purge_eligible=rec.purge_eligible,
            action="skipped",
        )

        if not rec.purge_eligible:
            base.reason = rec.purge_block_reason or "not-eligible"
            actions.append(base)
            continue

        if resolved_path == repo_path:
            base.reason = "primary-worktree"
            actions.append(base)
            continue

        if not _is_under_any_root(resolved_path, resolved_allowed_roots):
            base.reason = "path-outside-allowed-root"
            actions.append(base)
            continue

        if _is_protected_branch(rec.branch, protected_branches):
            base.reason = "protected-branch"
            actions.append(base)
            continue

        if not force and _is_dirty_worktree(resolved_path):
            base.reason = "dirty-worktree"
            actions.append(base)
            continue

        if dry_run:
            base.action = "would-remove"
            actions.append(base)
            continue

        try:
            remove_args = ["worktree", "remove", str(resolved_path)]
            if force:
                remove_args.append("--force")
            _run_git(repo_path, *remove_args)
            base.action = "removed"
            actions.append(base)
        except GitCommandError as exc:
            base.action = "error"
            base.reason = "git-remove-failed"
            base.detail = str(exc)
            actions.append(base)

    return actions

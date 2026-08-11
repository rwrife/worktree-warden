"""worktree-warden package."""

from .discovery import discover_worktrees
from .models import WorktreeRecord
from .parser import parse_worktree_porcelain
from .policy import TtlPolicy, apply_ttl_policy
from .purge import DEFAULT_PROTECTED_BRANCHES, PurgeLogEntry, purge_worktrees

__all__ = [
    "WorktreeRecord",
    "TtlPolicy",
    "apply_ttl_policy",
    "discover_worktrees",
    "parse_worktree_porcelain",
    "PurgeLogEntry",
    "DEFAULT_PROTECTED_BRANCHES",
    "purge_worktrees",
]

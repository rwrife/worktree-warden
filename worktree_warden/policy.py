from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

from .models import WorktreeRecord


@dataclass(slots=True)
class TtlPolicy:
    ttl_days: int
    exclude_branches: list[str] = field(default_factory=list)
    path_allowlist: list[str] = field(default_factory=list)
    path_denylist: list[str] = field(default_factory=list)


def _parse_utc_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    moment = datetime.fromisoformat(normalized)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _path_matches(patterns: list[str], path: Path) -> bool:
    path_str = str(path)
    posix = path.as_posix()

    for pattern in patterns:
        expanded = str(Path(pattern).expanduser()) if pattern.startswith("~") else pattern
        if fnmatch(path_str, pattern) or fnmatch(posix, pattern):
            return True
        if expanded != pattern and (fnmatch(path_str, expanded) or fnmatch(posix, expanded)):
            return True

    return False


def apply_ttl_policy(
    records: list[WorktreeRecord],
    *,
    policy: TtlPolicy,
    now: datetime,
) -> None:
    if policy.ttl_days < 0:
        raise ValueError("ttl_days must be >= 0")

    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)

    for rec in records:
        rec.purge_eligible = False
        rec.purge_block_reason = None
        rec.age_days = None

        if rec.branch and any(fnmatch(rec.branch, pattern) for pattern in policy.exclude_branches):
            rec.purge_block_reason = "excluded-branch"
            continue

        resolved_path = rec.path.resolve()
        if policy.path_allowlist and not _path_matches(policy.path_allowlist, resolved_path):
            rec.purge_block_reason = "path-not-allowlisted"
            continue

        if policy.path_denylist and _path_matches(policy.path_denylist, resolved_path):
            rec.purge_block_reason = "path-denylisted"
            continue

        if not rec.first_seen_at:
            rec.purge_block_reason = "missing-first-seen"
            continue

        first_seen = _parse_utc_timestamp(rec.first_seen_at)
        if first_seen > now_utc:
            rec.purge_block_reason = "first-seen-in-future"
            continue

        age_days = (now_utc - first_seen).days
        rec.age_days = age_days

        if age_days >= policy.ttl_days:
            rec.purge_eligible = True
        else:
            rec.purge_block_reason = "below-ttl"

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from worktree_warden.models import WorktreeRecord
from worktree_warden.policy import TtlPolicy, apply_ttl_policy


def _record(path: str, *, branch: str | None, first_seen_at: str) -> WorktreeRecord:
    return WorktreeRecord(
        repo_path=Path("/tmp/repo"),
        path=Path(path),
        branch_ref=f"refs/heads/{branch}" if branch else None,
        first_seen_at=first_seen_at,
    )


def test_ttl_boundary_n_minus_1_n_n_plus_1_days() -> None:
    now = datetime(2026, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _record("/tmp/wt/n-1", branch="feature/a", first_seen_at="2026-01-03T00:00:01Z"),
        _record("/tmp/wt/n", branch="feature/b", first_seen_at="2026-01-03T00:00:00Z"),
        _record("/tmp/wt/n+1", branch="feature/c", first_seen_at="2026-01-02T23:59:59Z"),
    ]

    apply_ttl_policy(records, policy=TtlPolicy(ttl_days=7), now=now)

    assert records[0].age_days == 6
    assert records[0].purge_eligible is False
    assert records[0].purge_block_reason == "below-ttl"

    assert records[1].age_days == 7
    assert records[1].purge_eligible is True
    assert records[1].purge_block_reason is None

    assert records[2].age_days == 7
    assert records[2].purge_eligible is True
    assert records[2].purge_block_reason is None


def test_excluded_branch_and_path_rules_block_purge_eligibility() -> None:
    now = datetime(2026, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        _record("/tmp/repos/main", branch="main", first_seen_at="2025-12-01T00:00:00Z"),
        _record(
            "/tmp/repos/release-allowed",
            branch="feature/allowed",
            first_seen_at="2025-12-01T00:00:00Z",
        ),
        _record(
            "/tmp/repos/release-secret",
            branch="feature/blocked",
            first_seen_at="2025-12-01T00:00:00Z",
        ),
    ]

    apply_ttl_policy(
        records,
        policy=TtlPolicy(
            ttl_days=7,
            exclude_branches=["main", "release/*"],
            path_allowlist=["*/repos/*"],
            path_denylist=["*secret*"],
        ),
        now=now,
    )

    assert records[0].purge_eligible is False
    assert records[0].purge_block_reason == "excluded-branch"

    assert records[1].purge_eligible is True
    assert records[1].purge_block_reason is None

    assert records[2].purge_eligible is False
    assert records[2].purge_block_reason == "path-denylisted"

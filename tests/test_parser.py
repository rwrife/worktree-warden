from pathlib import Path

import pytest

from worktree_warden.parser import parse_worktree_porcelain


def test_parse_normal_branch_record() -> None:
    raw = """
worktree /tmp/repo
HEAD abcdef1234567890
branch refs/heads/main
"""

    records = parse_worktree_porcelain(raw, repo_path=Path("/tmp/repo"))
    assert len(records) == 1
    rec = records[0]
    assert rec.path == Path("/tmp/repo").expanduser().resolve()
    assert rec.head == "abcdef1234567890"
    assert rec.branch_ref == "refs/heads/main"
    assert rec.branch == "main"
    assert rec.detached is False


def test_parse_detached_record() -> None:
    raw = """
worktree /tmp/repo-detached
HEAD fedcba9876543210
detached
"""

    rec = parse_worktree_porcelain(raw, repo_path=Path("/tmp/repo"))[0]
    assert rec.detached is True
    assert rec.branch is None
    assert rec.head == "fedcba9876543210"


def test_parse_bare_record() -> None:
    raw = """
worktree /tmp/bare-repo
bare
"""

    rec = parse_worktree_porcelain(raw, repo_path=Path("/tmp/bare-repo"))[0]
    assert rec.bare is True
    assert rec.branch is None
    assert rec.head is None


def test_parse_rejects_malformed_line() -> None:
    raw = """
worktree /tmp/repo
NOT_A_REAL_FIELD
"""

    with pytest.raises(ValueError, match="Malformed porcelain record"):
        parse_worktree_porcelain(raw, repo_path=Path("/tmp/repo"))

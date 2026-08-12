from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from worktree_warden import cli

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "worktree_warden", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_help_lists_scan_report_and_purge_commands() -> None:
    result = _cli("--help")
    assert result.returncode == 0
    assert "scan" in result.stdout
    assert "report" in result.stdout
    assert "purge" in result.stdout


def test_subcommand_help_documents_required_flags() -> None:
    scan_help = _cli("scan", "--help")
    assert scan_help.returncode == 0
    assert "--root" in scan_help.stdout

    report_help = _cli("report", "--help")
    assert report_help.returncode == 0
    assert "--root" in report_help.stdout
    assert "--json" in report_help.stdout

    purge_help = _cli("purge", "--help")
    assert purge_help.returncode == 0
    assert "--root" in purge_help.stdout
    assert "--ttl-days" in purge_help.stdout
    assert "--dry-run" in purge_help.stdout


def test_report_json_uses_versioned_envelope(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    result = _cli("report", "--root", str(root), "--json")
    assert result.returncode == 0

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1"
    assert payload["kind"] == "worktree-warden.report"
    assert Path(payload["root"]).resolve() == root.resolve()
    assert isinstance(payload["records"], list)
    paths = {Path(item["path"]).resolve() for item in payload["records"]}
    assert repo.resolve() in paths


def test_exit_code_semantics_for_success_usage_and_runtime_error(tmp_path: Path) -> None:
    root = tmp_path / "root"
    repo = root / "repo"
    _init_repo(repo)

    ok = _cli("scan", "--root", str(root), "--json")
    assert ok.returncode == cli.EXIT_SUCCESS

    usage = _cli("scan")
    assert usage.returncode == cli.EXIT_USAGE_ERROR

    runtime = _cli("report", "--root", str(root), "--ttl-days", "-1", "--json")
    assert runtime.returncode == cli.EXIT_RUNTIME_ERROR
    assert "ttl_days must be >= 0" in runtime.stderr


def test_purge_returns_partial_failure_exit_code(monkeypatch, tmp_path: Path) -> None:
    class _Entry:
        def to_dict(self) -> dict[str, object]:
            return {
                "repo_path": "/tmp/repo",
                "path": "/tmp/repo/wt",
                "branch": "feature/x",
                "age_days": 10,
                "purge_eligible": True,
                "action": "error",
                "reason": "git-remove-failed",
                "detail": "boom",
            }

    monkeypatch.setattr(cli, "purge_worktrees", lambda *args, **kwargs: [_Entry()])

    code = cli.run(["purge", "--root", str(tmp_path), "--ttl-days", "1"])
    assert code == cli.EXIT_PARTIAL_FAILURE

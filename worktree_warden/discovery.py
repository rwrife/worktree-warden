from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .models import WorktreeRecord
from .parser import parse_worktree_porcelain

_METADATA_DIRNAME = ".worktree-warden"
_METADATA_FILENAME = "metadata.json"


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

    for dirpath, dirnames, _ in os.walk(root):
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


def _default_metadata_store_path(root: Path) -> Path:
    return root / _METADATA_DIRNAME / _METADATA_FILENAME


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_timestamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_metadata_store(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    worktrees = payload.get("worktrees", {}) if isinstance(payload, dict) else {}
    if not isinstance(worktrees, dict):
        raise ValueError(f"Malformed metadata store at {path}: 'worktrees' must be an object")

    normalized: dict[str, dict[str, object]] = {}
    for key, value in worktrees.items():
        if isinstance(key, str) and isinstance(value, dict):
            normalized[key] = value
    return normalized


def _save_metadata_store(path: Path, entries: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "worktrees": entries}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _apply_persistent_metadata(
    records: list[WorktreeRecord],
    *,
    metadata_store_path: Path,
    now: datetime,
) -> None:
    store = _load_metadata_store(metadata_store_path)
    stamp = _to_utc_timestamp(now)
    mutated = not metadata_store_path.exists()

    for rec in records:
        key = str(rec.path.resolve())
        entry = store.get(key)

        if entry is None:
            entry = {
                "first_seen_at": stamp,
                "last_seen_at": stamp,
                "last_activity_at": stamp,
                "head": rec.head,
            }
            store[key] = entry
            mutated = True
        else:
            if not entry.get("first_seen_at"):
                entry["first_seen_at"] = stamp
                mutated = True

            previous_head = entry.get("head")
            if previous_head != rec.head:
                entry["last_activity_at"] = stamp
                mutated = True
            elif not entry.get("last_activity_at"):
                entry["last_activity_at"] = entry.get("last_seen_at") or stamp
                mutated = True

            if entry.get("last_seen_at") != stamp:
                entry["last_seen_at"] = stamp
                mutated = True

            if entry.get("head") != rec.head:
                entry["head"] = rec.head
                mutated = True

        first_seen = entry.get("first_seen_at")
        last_seen = entry.get("last_seen_at")
        last_activity = entry.get("last_activity_at")

        rec.first_seen_at = first_seen if isinstance(first_seen, str) else None
        rec.last_seen_at = last_seen if isinstance(last_seen, str) else None
        rec.last_activity_at = last_activity if isinstance(last_activity, str) else None

    if mutated:
        _save_metadata_store(metadata_store_path, store)


def discover_worktrees(
    root: Path,
    *,
    metadata_store_path: Path | None = None,
    now: datetime | None = None,
) -> list[WorktreeRecord]:
    """Discover repos recursively and return normalized worktree records."""
    resolved_root = root.expanduser().resolve()
    candidates = discover_git_candidates(resolved_root)
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

    effective_metadata_store = metadata_store_path or _default_metadata_store_path(resolved_root)
    _apply_persistent_metadata(
        discovered,
        metadata_store_path=effective_metadata_store,
        now=now or _utc_now(),
    )

    return discovered

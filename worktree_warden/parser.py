from __future__ import annotations

from pathlib import Path

from .models import WorktreeRecord


def _split_records(porcelain_text: str) -> list[list[str]]:
    records: list[list[str]] = []
    current: list[str] = []
    for raw in porcelain_text.splitlines():
        line = raw.strip()
        if not line:
            if current:
                records.append(current)
                current = []
            continue
        current.append(line)

    if current:
        records.append(current)

    return records


def parse_worktree_porcelain(porcelain_text: str, repo_path: Path) -> list[WorktreeRecord]:
    """Parse output of `git worktree list --porcelain` into normalized records."""
    parsed: list[WorktreeRecord] = []

    for i, record_lines in enumerate(_split_records(porcelain_text), start=1):
        first = record_lines[0]
        if not first.startswith("worktree "):
            raise ValueError(
                f"Malformed porcelain record {i}: expected 'worktree <path>', got '{first}'"
            )

        worktree_path = Path(first[len("worktree ") :]).expanduser().resolve()
        rec = WorktreeRecord(repo_path=repo_path.resolve(), path=worktree_path)

        for line in record_lines[1:]:
            if line.startswith("HEAD "):
                rec.head = line[len("HEAD ") :]
            elif line.startswith("branch "):
                rec.branch_ref = line[len("branch ") :]
            elif line == "detached":
                rec.detached = True
            elif line == "bare":
                rec.bare = True
            elif line == "locked":
                rec.locked_reason = ""
            elif line.startswith("locked "):
                rec.locked_reason = line[len("locked ") :]
            elif line == "prunable":
                rec.prunable_reason = ""
            elif line.startswith("prunable "):
                rec.prunable_reason = line[len("prunable ") :]
            else:
                if " " not in line:
                    raise ValueError(
                        f"Malformed porcelain record {i}: unrecognized token '{line}'"
                    )
                key, value = line.split(" ", 1)
                rec.extra[key] = value

        parsed.append(rec)

    return parsed

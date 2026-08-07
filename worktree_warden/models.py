from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class WorktreeRecord:
    repo_path: Path
    path: Path
    head: str | None = None
    branch_ref: str | None = None
    detached: bool = False
    bare: bool = False
    locked_reason: str | None = None
    prunable_reason: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def branch(self) -> str | None:
        if not self.branch_ref:
            return None
        prefix = "refs/heads/"
        if self.branch_ref.startswith(prefix):
            return self.branch_ref[len(prefix) :]
        return self.branch_ref

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["repo_path"] = str(self.repo_path)
        data["path"] = str(self.path)
        data["branch"] = self.branch
        return data

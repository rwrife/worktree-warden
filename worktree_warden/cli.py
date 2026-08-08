from __future__ import annotations

import argparse
import json
from pathlib import Path

from .discovery import discover_worktrees


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worktree-warden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover worktrees under a root path")
    scan.add_argument("--root", required=True, help="Root directory to scan")
    scan.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def _print_table(records: list[dict[str, object]]) -> None:
    headers = ["repo_path", "path", "branch", "detached", "bare", "head"]
    print("\t".join(headers))
    for rec in records:
        row = [str(rec.get(h, "")) for h in headers]
        print("\t".join(row))


def main() -> None:
    args = _build_parser().parse_args()

    if args.command == "scan":
        records = [r.to_dict() for r in discover_worktrees(Path(args.root))]
        if args.json:
            print(json.dumps(records, indent=2))
        else:
            _print_table(records)

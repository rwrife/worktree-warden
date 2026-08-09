from __future__ import annotations

import argparse
import json
from pathlib import Path

from .discovery import discover_worktrees
from .policy import TtlPolicy


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worktree-warden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover worktrees under a root path")
    scan.add_argument("--root", required=True, help="Root directory to scan")
    scan.add_argument("--state-file", help="Optional metadata store path")
    scan.add_argument("--ttl-days", type=int, help="TTL in days for purge eligibility")
    scan.add_argument(
        "--exclude-branch",
        action="append",
        default=[],
        help="Branch glob to exclude from purge eligibility (repeatable)",
    )
    scan.add_argument(
        "--path-allowlist",
        action="append",
        default=[],
        help="Path glob allowlist for purge eligibility (repeatable)",
    )
    scan.add_argument(
        "--path-denylist",
        action="append",
        default=[],
        help="Path glob denylist for purge eligibility (repeatable)",
    )
    scan.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def _print_table(records: list[dict[str, object]]) -> None:
    headers = [
        "repo_path",
        "path",
        "branch",
        "detached",
        "bare",
        "head",
        "age_days",
        "purge_eligible",
        "purge_block_reason",
    ]
    print("\t".join(headers))
    for rec in records:
        row = [str(rec.get(h, "")) for h in headers]
        print("\t".join(row))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        if args.ttl_days is None and (
            args.exclude_branch or args.path_allowlist or args.path_denylist
        ):
            parser.error(
                "--exclude-branch/--path-allowlist/--path-denylist require --ttl-days"
            )

        ttl_policy = None
        if args.ttl_days is not None:
            ttl_policy = TtlPolicy(
                ttl_days=args.ttl_days,
                exclude_branches=args.exclude_branch,
                path_allowlist=args.path_allowlist,
                path_denylist=args.path_denylist,
            )

        state_file = Path(args.state_file) if args.state_file else None
        records = [
            r.to_dict()
            for r in discover_worktrees(
                Path(args.root),
                metadata_store_path=state_file,
                ttl_policy=ttl_policy,
            )
        ]
        if args.json:
            print(json.dumps(records, indent=2))
        else:
            _print_table(records)

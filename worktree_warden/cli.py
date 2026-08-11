from __future__ import annotations

import argparse
import json
from pathlib import Path

from .discovery import discover_worktrees
from .policy import TtlPolicy
from .purge import DEFAULT_PROTECTED_BRANCHES, purge_worktrees


def _add_ttl_policy_arguments(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--ttl-days",
        type=int,
        required=required,
        help="TTL in days for purge eligibility",
    )
    parser.add_argument(
        "--exclude-branch",
        action="append",
        default=[],
        help="Branch glob to exclude from purge eligibility (repeatable)",
    )
    parser.add_argument(
        "--path-allowlist",
        action="append",
        default=[],
        help="Path glob allowlist for purge eligibility (repeatable)",
    )
    parser.add_argument(
        "--path-denylist",
        action="append",
        default=[],
        help="Path glob denylist for purge eligibility (repeatable)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worktree-warden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Discover worktrees under a root path")
    scan.add_argument("--root", required=True, help="Root directory to scan")
    scan.add_argument("--state-file", help="Optional metadata store path")
    _add_ttl_policy_arguments(scan, required=False)
    scan.add_argument("--json", action="store_true", help="Output JSON")

    purge = subparsers.add_parser("purge", help="Safely purge stale worktrees")
    purge.add_argument("--root", required=True, help="Root directory to scan")
    purge.add_argument("--state-file", help="Optional metadata store path")
    _add_ttl_policy_arguments(purge, required=True)
    purge.add_argument("--dry-run", action="store_true", help="Preview actions only")
    purge.add_argument(
        "--force",
        action="store_true",
        help="Allow purge even when worktrees contain uncommitted changes",
    )
    purge.add_argument(
        "--protected-branch",
        action="append",
        default=[],
        help=(
            "Branch glob protected from purge (repeatable, defaults to: "
            "main, master, release/*)"
        ),
    )
    purge.add_argument(
        "--allowed-root",
        action="append",
        default=[],
        help="Additional allowed root path for purge safety checks (repeatable)",
    )
    purge.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def _build_ttl_policy(args: argparse.Namespace) -> TtlPolicy:
    return TtlPolicy(
        ttl_days=args.ttl_days,
        exclude_branches=args.exclude_branch,
        path_allowlist=args.path_allowlist,
        path_denylist=args.path_denylist,
    )


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


def _print_purge_table(records: list[dict[str, object]]) -> None:
    headers = [
        "repo_path",
        "path",
        "branch",
        "age_days",
        "purge_eligible",
        "action",
        "reason",
        "detail",
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

        ttl_policy = _build_ttl_policy(args) if args.ttl_days is not None else None

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
        return

    if args.command == "purge":
        state_file = Path(args.state_file) if args.state_file else None
        protected_branches = args.protected_branch or list(DEFAULT_PROTECTED_BRANCHES)
        allowed_roots = [Path(args.root), *[Path(value) for value in args.allowed_root]]

        records = [
            row.to_dict()
            for row in purge_worktrees(
                Path(args.root),
                metadata_store_path=state_file,
                ttl_policy=_build_ttl_policy(args),
                dry_run=args.dry_run,
                force=args.force,
                protected_branches=protected_branches,
                allowed_roots=allowed_roots,
            )
        ]

        if args.json:
            print(json.dumps(records, indent=2))
        else:
            _print_purge_table(records)
        return

    parser.error(f"Unknown command: {args.command}")

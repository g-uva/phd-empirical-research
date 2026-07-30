#!/usr/bin/env python3
"""Check or explicitly update content hashes for catalogue experiments."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HASH_ALGORITHM = "sha256"
HASH_FORMAT = "experiment-content-v1"


def index_paths() -> list[Path]:
    return sorted((ROOT / "papers").glob("*/artifact/experiments/index.json"))


def paper_slug(index_path: Path) -> str:
    return index_path.relative_to(ROOT / "papers").parts[0]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_staged_json(path: Path) -> Any:
    relative = path.relative_to(ROOT).as_posix()
    completed = subprocess.run(
        ["git", "show", f":{relative}"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def canonical_content(metadata: dict[str, Any]) -> bytes:
    content = dict(metadata)
    content.pop("content_hash", None)
    envelope = {"format": HASH_FORMAT, "metadata": content}
    return json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def calculate_hash(metadata: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_content(metadata)).hexdigest()


def inspect_index(
    index_path: Path, *, staged: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reader = read_staged_json if staged else read_json
    index = reader(index_path)
    states: list[dict[str, Any]] = []
    for entry in index.get("experiments", []):
        metadata_path = index_path.parent / entry["path"]
        metadata = reader(metadata_path)
        expected = calculate_hash(metadata)
        states.append(
            {
                "slug": paper_slug(index_path),
                "index_path": index_path,
                "entry": entry,
                "metadata": metadata,
                "path": metadata_path,
                "expected": expected,
                "metadata_hash": metadata.get("content_hash"),
                "index_hash": entry.get("content_hash"),
            }
        )
    return index, states


def inspect_all(
    *, staged: bool = False
) -> tuple[dict[Path, dict[str, Any]], list[dict[str, Any]]]:
    indexes: dict[Path, dict[str, Any]] = {}
    states: list[dict[str, Any]] = []
    for path in index_paths():
        index, index_states = inspect_index(path, staged=staged)
        indexes[path] = index
        states.extend(index_states)
    return indexes, states


def invalid_states(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        state
        for state in states
        if state["metadata_hash"] != state["expected"]
        or state["index_hash"] != state["expected"]
    ]


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return completed.stdout.strip()


def changed_files(slug: str) -> list[dict[str, str]]:
    scope = f"papers/{slug}"
    records: dict[str, str] = {}
    output = git_output("diff", "--name-status", "HEAD", "--", scope)
    for line in output.splitlines():
        if not line:
            continue
        fields = line.split("\t")
        records[fields[-1]] = fields[0]
    untracked = git_output("ls-files", "--others", "--exclude-standard", "--", scope)
    for path in untracked.splitlines():
        if path:
            records.setdefault(path, "untracked")
    return [{"path": path, "status": records[path]} for path in sorted(records)]


def check(*, staged: bool = False) -> int:
    try:
        _, states = inspect_all(staged=staged)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        if staged:
            print(
                "ERROR: staged experiment catalogue is incomplete or invalid; "
                "stage every related index and metadata file.",
                file=sys.stderr,
            )
        print(str(exc), file=sys.stderr)
        return 1
    invalid = invalid_states(states)
    if invalid:
        for state in invalid:
            print(
                f"ERROR: stale or missing content hash for "
                f"{state['slug']}/{state['entry']['id']}; "
                f"expected {state['expected']}",
                file=sys.stderr,
            )
        print(
            "Run: python3 scripts/experiment_versions.py update --paper <slug> "
            '--reason "explain the scientific or metadata change"',
            file=sys.stderr,
        )
        return 1
    source = "staged" if staged else "working-tree"
    print(
        f"experiment content hashes valid "
        f"({len(states)} experiments across {len(index_paths())} papers, {source})"
    )
    return 0


def update(reason: str, requested_ids: list[str], requested_paper: str | None) -> int:
    indexes, states = inspect_all()
    if requested_paper:
        matching_indexes = [
            path for path in indexes if paper_slug(path) == requested_paper
        ]
        if not matching_indexes:
            print(f"ERROR: unknown paper slug: {requested_paper}", file=sys.stderr)
            return 2
        states = [state for state in states if state["slug"] == requested_paper]
    elif requested_ids:
        matching_slugs = {
            state["slug"]
            for state in states
            if state["entry"]["id"] in requested_ids
        }
        if len(matching_slugs) > 1:
            print(
                "ERROR: experiment IDs are only unique within a paper; "
                "supply --paper <slug>",
                file=sys.stderr,
            )
            return 2

    known_ids = {state["entry"]["id"] for state in states}
    unknown = sorted(set(requested_ids) - known_ids)
    if unknown:
        print(f"ERROR: unknown experiment IDs: {', '.join(unknown)}", file=sys.stderr)
        return 2

    candidates = invalid_states(states)
    selected = (
        [state for state in candidates if state["entry"]["id"] in requested_ids]
        if requested_ids
        else candidates
    )
    if not selected:
        print("experiment content hashes already current")
        return 0

    grouped: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    for state in selected:
        grouped[state["index_path"]].append(state)

    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    base_commit = git_output("rev-parse", "HEAD")
    total = 0
    for index_path, index_states in grouped.items():
        changes = []
        for state in index_states:
            previous = state["metadata_hash"]
            current = state["expected"]
            state["metadata"]["content_hash"] = current
            state["entry"]["content_hash"] = current
            write_json(state["path"], state["metadata"])
            changes.append(
                {
                    "experiment_id": state["entry"]["id"],
                    "uid": state["entry"]["uid"],
                    "previous_content_hash": previous,
                    "content_hash": current,
                    "metadata_path": str(state["path"].relative_to(ROOT)),
                }
            )
        write_json(index_path, indexes[index_path])
        slug = paper_slug(index_path)
        changes_path = index_path.parent / "changes"
        changes_path.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": "1.0.0",
            "created": timestamp.isoformat().replace("+00:00", "Z"),
            "reason": reason,
            "base_git_commit": base_commit,
            "hash_algorithm": HASH_ALGORITHM,
            "hash_format": HASH_FORMAT,
            "experiments": changes,
            "working_tree_changes": changed_files(slug),
        }
        stem = timestamp.strftime("%Y%m%dT%H%M%SZ")
        ids = "-".join(change["experiment_id"] for change in changes)
        record_path = changes_path / f"{stem}-{ids}.json"
        suffix = 1
        while record_path.exists():
            record_path = changes_path / f"{stem}-{ids}-{suffix}.json"
            suffix += 1
        write_json(record_path, record)
        print(f"wrote {record_path.relative_to(ROOT)}")
        total += len(changes)
    print(f"updated {total} experiment content hash(es)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate or explicitly update experiment content hashes."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument(
        "--staged",
        action="store_true",
        help="Validate the versions staged in the Git index.",
    )
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument(
        "--reason",
        required=True,
        help="Reason recorded in the generated experiment change record.",
    )
    update_parser.add_argument(
        "--paper",
        help="Paper slug under papers/; required when an explicit ID is ambiguous.",
    )
    update_parser.add_argument(
        "experiment_ids",
        nargs="*",
        metavar="exp-####",
        help="Only update these stale experiments (default: all stale experiments).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "check":
        return check(staged=args.staged)
    return update(args.reason, args.experiment_ids, args.paper)


if __name__ == "__main__":
    raise SystemExit(main())

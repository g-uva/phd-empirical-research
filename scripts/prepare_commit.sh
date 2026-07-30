#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
    echo "Usage: scripts/prepare_commit.sh \"Reason for the catalogue changes\"" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
cd "$repository_root"

reason=$1

# The Python updater changes only stale experiment hashes. If none are stale,
# it exits successfully without creating a change record.
python3 scripts/experiment_versions.py update --reason "$reason"

git add .
python3 scripts/experiment_versions.py check --staged
python3 scripts/validate_metadata.py
git diff --cached --check

echo
echo "Preparation complete. Review the staged changes before committing:"
git status --short

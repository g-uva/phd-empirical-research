#!/usr/bin/env bash
set -euo pipefail

artifact_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
snapshot="$artifact_root/../original/xprof-713b05f09e30.zip"
workdir=${XPROF_WORKDIR:-$(mktemp -d /tmp/xprof-demo.XXXXXX)}
port=${XPROF_PORT:-8791}

if [[ ! -f "$snapshot" ]]; then
  echo "Missing source snapshot: $snapshot" >&2
  exit 1
fi

mkdir -p "$workdir/extracted"
unzip -q "$snapshot" 'xprof/demo/*' -d "$workdir/extracted"

python3 -m venv "$workdir/venv"
"$workdir/venv/bin/python" -m pip install --upgrade pip
"$workdir/venv/bin/python" -m pip install 'setuptools<70' 'xprof==2.22.3'

echo "Demo data: $workdir/extracted/xprof/demo"
echo "XProf URL: http://127.0.0.1:$port/"
echo "The server runs until interrupted with Ctrl-C."
exec "$workdir/venv/bin/xprof" \
  --logdir="$workdir/extracted/xprof/demo" \
  --port="$port"

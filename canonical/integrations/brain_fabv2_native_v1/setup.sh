#!/bin/bash
set -euo pipefail

UPSTREAM_COMMIT="502aab6fdaa3fb9294905c7453f89882baa8d39b"
GET_AGENT_BLOB="22c012241a430975266fb7f8d2fe7af8e9f1b8d4"
TOOLS_BLOB="19b85ce4e110e39f410c52b2efa0e33f651fa6d1"

command -v uv >/dev/null
test -x /app/.venv/bin/python

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
archive="$tmp/finance-agent.tar.gz"
curl -fsSL "https://codeload.github.com/vals-ai/finance-agent-v2/tar.gz/$UPSTREAM_COMMIT" -o "$archive"
tar -xzf "$archive" -C "$tmp"
src="$tmp/finance-agent-v2-$UPSTREAM_COMMIT"

SRC="$src" GET_AGENT_BLOB="$GET_AGENT_BLOB" TOOLS_BLOB="$TOOLS_BLOB" /app/.venv/bin/python - <<'PY'
import hashlib
import os
from pathlib import Path

root = Path(os.environ["SRC"])
checks = {
    "finance_agent/get_agent.py": os.environ["GET_AGENT_BLOB"],
    "finance_agent/tools.py": os.environ["TOOLS_BLOB"],
}
for rel, expected in checks.items():
    data = (root / rel).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if actual != expected:
        raise SystemExit(f"UPSTREAM_BLOB_MISMATCH:{rel}:{actual}:{expected}")
PY

uv pip install --python /app/.venv/bin/python --no-deps --reinstall "$src"
mkdir -p /app/results/brain_fabv2_native
